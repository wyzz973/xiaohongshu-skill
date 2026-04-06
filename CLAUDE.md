# xhs-autopilot

小红书 24/7 自动驾驶运营系统，基于 Python CDP 浏览器自动化引擎 + OpenClaw Cron 调度。

## 开发命令

```bash
uv sync                    # 安装依赖
uv run ruff check .        # Lint 检查
uv run ruff format .       # 代码格式化
uv run pytest              # 运行测试
```

## 架构

三层结构：

1. **调度层** — OpenClaw Cron 定时任务（7 个任务覆盖全链路）
2. **Skill 层** — `SKILL.md`（主路由）+ `skills/*/SKILL.md`（子技能 SOP）
3. **引擎层** — `scripts/cli.py`（43 个子命令）→ `scripts/xhs/`（CDP 自动化库）

### 调用方式

```bash
python scripts/chrome_launcher.py --headless          # 启动 Chrome
python scripts/cli.py check-login                     # 检查登录
python scripts/cli.py search-feeds --keyword "AI工具"  # 搜索
python scripts/cli.py fill-publish --title-file t.txt --content-file c.txt --images pic.jpg
python scripts/cli.py click-publish                   # 确认发布
python scripts/publish_pipeline.py --title-file t.txt --content-file c.txt --images URL
```

### 数据流

```
strategy.json → Cron 任务 → content-calendar/ → drafts/ → published/ → analytics/
```

所有运行时数据存储在 workspace 根目录（`XHS_WORKSPACE` 环境变量指定，默认回退 `~/.openclaw/workspace/xhs-autopilot/`）。

在此 workspace 中运行时，设置环境变量：
```bash
export XHS_WORKSPACE=~/xhs-workspace
```

## 代码规范

- 行长度上限 100 字符
- 完整 type hints，使用 `from __future__ import annotations`
- 异常继承 `XHSError`（`xhs/errors.py`）
- CLI exit code：0=成功，1=未登录，2=错误
- 用户可见错误信息使用中文
- JSON 输出 `ensure_ascii=False`

### 安全约束

- 发布类操作必须有用户确认机制
- 文件路径必须使用绝对路径
- 敏感内容通过文件传递，不内联到命令行参数
- Chrome Profile 目录隔离账号 cookies
- 频率限制硬编码，不可通过 strategy.json 突破

## CLI 子命令完整列表

| 子命令 | 分类 | 说明 |
|--------|------|------|
| `check-login` | 认证 | 检查登录状态（未登录自动返回二维码） |
| `login` | 认证 | 二维码登录（阻塞等待） |
| `get-qrcode` | 认证 | 获取二维码（非阻塞） |
| `wait-login` | 认证 | 等待扫码完成 |
| `phone-login` | 认证 | 手机号登录（交互式） |
| `send-code` | 认证 | 分步登录：发验证码 |
| `verify-code` | 认证 | 分步登录：提交验证码 |
| `delete-cookies` | 认证 | 清除 cookies |
| `list-feeds` | 浏览 | 首页推荐 |
| `search-feeds` | 浏览 | 关键词搜索 |
| `get-feed-detail` | 浏览 | 笔记详情+评论（搜索结果加 `--xsec-source pc_search`） |
| `user-profile` | 浏览 | 用户主页 |
| `post-comment` | 互动 | 发表评论（搜索结果加 `--xsec-source pc_search`） |
| `reply-comment` | 互动 | 回复评论（搜索结果加 `--xsec-source pc_search`） |
| `like-feed` | 互动 | 点赞（搜索结果加 `--xsec-source pc_search`） |
| `favorite-feed` | 互动 | 收藏（搜索结果加 `--xsec-source pc_search`） |
| `list-notifications` | 互动 | 通知列表 |
| `reply-notification` | 互动 | 回复通知 |
| `like-notification` | 互动 | 点赞通知 |
| `check-interacted` | 去重 | 批量查询是否已互动 |
| `record-interact` | 去重 | 记录新互动 |
| `check-reply-limit` | 去重 | 检查回复次数上限 |
| `record-reply` | 去重 | 记录回复 |
| `publish` | 发布 | 一步图文发布 |
| `publish-video` | 发布 | 一步视频发布 |
| `publish-text2image` | 发布 | 一步文字配图发布 |
| `fill-publish` | 分步 | 填写图文表单 |
| `fill-publish-video` | 分步 | 填写视频表单 |
| `fill-text2image` | 分步 | 填写文字配图表单 |
| `click-publish` | 分步 | 确认发布 |
| `save-draft` | 分步 | 保存草稿 |
| `long-article` | 发布 | 长文发布 |
| `select-template` | 发布 | 长文选模板 |
| `next-step` | 发布 | 长文下一步 |
| `add-account` | 账号 | 添加账号 |
| `list-accounts` | 账号 | 列出所有账号 |
| `remove-account` | 账号 | 删除账号 |
| `set-default-account` | 账号 | 设默认账号 |
| `list-my-notes` | 数据 | 我的笔记列表+深度分析(曝光/CTR/时长/涨粉) |
| `get-dashboard` | 数据 | 账号总览仪表盘(7日数据/环比/百分位) |
| `get-fans-profile` | 数据 | 粉丝画像(性别/兴趣/地域) |
| `sync-notifications` | 去重 | 首次同步标记已有通知 |
| `check-watermark` | 去重 | 检查通知水位线 |
