# 常见问题排查

## 登录问题

### Cookie 过期
**症状**: `python scripts/cli.py check-login` 返回码 1，或操作时跳转登录页
**处理**:
1. 通知用户扫码重新登录
2. `python scripts/cli.py login` → 生成二维码，等待扫码
3. 登录后 Cookie 自动保存到 Chrome Profile 目录
4. 如需切换账号：`python scripts/cli.py delete-cookies` 后重新登录

### 多端登录冲突
**症状**: 操作中突然被踢出
**原因**: 小红书同一账号不允许多个网页端同时登录
**处理**: 确保只在 OpenClaw 的 Chrome 实例中登录，不要在其他浏览器登录同一账号

### 无头模式登录
**症状**: 服务器无显示器，无法扫码
**处理**:
1. 首次用有头模式登录: `python scripts/chrome_launcher.py` (非 --headless)
2. 登录成功后切换为无头模式
3. 或通过截图 + 消息渠道发送二维码给用户

## 风控问题

### 验证码弹出
**处理**: 立即停止全部自动化操作，通知用户手动验证，等待 30 分钟后再恢复

### "操作频繁" 提示
**处理**: 停止所有操作 2-4 小时，检查是否超过了 strategy.json 中的频率限制

### 404 / 访问链接异常 / "当前笔记暂时无法浏览"
**原因**: xsec_token 过期，或 `--xsec-source` 与 token 来源不匹配
**处理**:
1. 搜索结果的帖子必须加 `--xsec-source pc_search`，推荐页用默认 `pc_feed`
2. 如仍失败，重新获取推荐流/搜索数据获取新 token

### 评论发送失败
**可能原因**: 含敏感词 / 频率过快 / 账号限制
**处理**: 更换评论内容，降低频率，检查账号状态

## Chrome 问题

### Chrome 进程异常退出
**处理**:
```bash
# 检查进程
ps aux | grep chrome
# 重启
python scripts/chrome_launcher.py --headless
```

### CDP 连接失败
**症状**: cli.py 报 "connection refused"
**处理**:
1. 确认 Chrome 以 `--remote-debugging-port=9222` 启动
2. 检查端口是否被占用: `lsof -i :9222`
3. 杀掉旧进程后重启

### 复用旧 tab 导致卡死 / session 响应超时
**症状**:
- `等待 session 响应超时 (id=...)`
- 旧的 target_id 还能读到，但 `Page.enable` / `Page.navigate` 卡住

**原因**:
- CLI 复用的 session tab 已失效，但 CDP attach 没彻底失败
- 旧 target 进入半失效状态，导致后续命令超时

**处理**:
1. 清理临时 tab 记录：`rm -f /tmp/xhs/session_tab_9222.txt`
2. 在 `xhs/cdp.py` 中让 `get_page_by_target_id()` 只要 attach 后初始化失败就直接回退返回 `None`
3. 重新走 `_connect()`，让浏览器创建新 tab

## 发布问题

### 长文发布找不到“新的创作”按钮
**症状**:
- `未找到'新的创作'按钮，页面结构可能已变化`

**原因**:
- 新版小红书长文页仍有“新的创作”文本，但真实可点击元素是 `button.new-btn`
- 旧逻辑遍历过宽，容易点到不可点击的容器/文本节点

**处理**:
1. 优先点击 `button.new-btn`
2. 再回退到通用文本匹配
3. 点击前校验元素可见性和尺寸

### 长文正文无法输入 / 输入极慢
**症状**:
- 标题能填，正文卡住
- 逐字输入很慢，甚至被页面吞掉

**原因**:
- 新版长文编辑器从旧的 `ql-editor` 切到 `div.tiptap.ProseMirror`
- 逐字输入在长文模式下不稳定

**处理**:
1. `CONTENT_EDITOR` 兼容 `div.tiptap.ProseMirror, div.ProseMirror`
2. 长文正文优先直接写入 ProseMirror DOM，再触发 input/change 事件
3. 只有找不到 ProseMirror 时才回退到旧的 contentEditable 逐字输入逻辑

### 长文正文注入报 SyntaxError
**症状**:
- `JS 执行异常: SyntaxError: Invalid or unexpected token`

**原因**:
- 直接把正文插进 JS 模板字符串，遇到引号、反斜杠、换行等字符时转义失败

**处理**:
1. 所有注入到 `page.evaluate()` 的正文/选择器都先 `json.dumps()`
2. 在 JS 内再读取安全字符串并处理换行

### 选择模板后找不到“下一步”按钮
**症状**:
- `未找到'下一步'按钮，页面结构可能已变化`

**原因**:
- 新版长文流程在选择模板后可能直接进入最终发布页，不再出现独立“下一步”按钮

**处理**:
1. 先检查是否已存在 `.publish-page-publish-btn button.bg-red`
2. 如果已在发布页，则直接跳过“下一步”
3. 直接补正文描述并执行发布

### 图文“文字配图”链路（2026-03-12 已验证）
**新版实际流程**:
1. `上传图文`
2. `文字配图`
3. 在 `div.tiptap.ProseMirror` 中输入文案
4. 点击 `.edit-text-button` 触发生成图片
5. 进入模板/卡片预览页（可换配色、选卡片）
6. 点击 `下一步`
7. 进入最终发布页
8. 点击 `发布`

**注意**:
- “生成图片”按钮不是原生 `button`，实际可点击容器是 `.edit-text-button`
- 文字配图页与长文页一样，也在使用 ProseMirror
- 长文链路：在 `next-step --tags ...` 阶段补 tag，最终只执行 `click-publish`
- 图文/通用最终发布页：仅当此前还没补 tag 时，才使用 `click-publish --tags ...`
- 现在已提供正式命令：`fill-text2image` / `publish-text2image`
## Cron 任务问题

### 任务未执行
**检查**:
```bash
openclaw cron list           # 确认 Enabled = true
openclaw cron status         # 确认 Cron 服务运行中
openclaw cron runs --id <id> # 查看执行历史
```

### 任务执行但结果异常
**处理**:
```bash
openclaw cron run <id> --force  # 手动触发测试
```
观察输出，通常是登录态过期或 strategy.json 配置问题。

### 修改任务时间
```bash
openclaw cron edit <job-id>
# 或直接告诉 agent："把发布时间改到晚上8点"
```

## 数据目录

所有数据存储在 `~/.openclaw/workspace/xhs-autopilot/`：

| 目录 | 内容 | 清理策略 |
|------|------|---------|
| content-calendar/ | 每日选题 | 保留 30 天 |
| drafts/ | 待发布草稿 | 发布后归档到 published/ |
| published/ | 已发布记录 | 永久保留 |
| analytics/ | 数据复盘 | 保留 90 天 |
| logs/ | 互动日志 | 保留 14 天 |
