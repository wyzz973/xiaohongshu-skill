---
name: xhs-autopilot
description: >
  Use when 用户提到 小红书/XHS/笔记/种草/文案/测评/爆款/自动运营/自动发布/
  自动评论/小红书运营/账号运营/内容日历/定时发布/24小时运营/涨粉/引流/养号。
  Do NOT use: 与小红书无关的通用写作、非小红书平台操作。
user-invocable: true
metadata:
  openclaw:
    emoji: "📕"
    skillKey: "xhs-autopilot"
    version: "2.1.0"
    always: true
    requires:
      bins: ["python3"]
      config: ["browser.enabled"]
---

# 小红书 24/7 自动运营

## 强制规则

- **唯一工具**：所有操作只通过 `python scripts/cli.py <子命令>` 执行
- **禁止替代**：不得使用 MCP 工具、Go 工具、Playwright、xiaohongshu-mcp 或任何外部实现
- **文件路径**：必须绝对路径
- **输出格式**：CLI 输出 JSON，退出码 0=成功 1=未登录 2=错误

---

## 架构

```
strategy.json → Cron 调度 → content-calendar/ → drafts/ → published/ → analytics/
                   ↓
  scripts/cli.py (CLI) → scripts/xhs/ (CDP) → Chrome(:9222) → 小红书
```

## 安全限制

| 操作 | 每会话 | 每日上限 | 间隔 |
|------|--------|---------|------|
| 评论 | 8-10 | 20-25 | 2-5 分钟 |
| 点赞 | 15-20 | 40-50 | 30s-2min |
| 发布 | 2-3 | 3-5 | 30 分钟+ |

夜间：23:00-02:00 降频；02:00-06:00 仅巡检不互动。风控信号（验证码/频繁失败）→ 立即停止通知用户。

---

## CLI 命令速查

### 认证

| 命令 | 用途 |
|------|------|
| `check-login` | 检查登录（未登录自动返回二维码） |
| `login` | 二维码登录（阻塞等待） |
| `get-qrcode` | 获取二维码（非阻塞） |
| `wait-login` | 等待扫码完成（配合 get-qrcode） |
| `phone-login --phone P [--code C]` | 手机号登录（交互式） |
| `send-code --phone P` | 分步登录：发验证码 |
| `verify-code --code C` | 分步登录：提交验证码 |
| `delete-cookies` | 清除 cookies |
| `add-account --name N` | 添加命名账号 |
| `list-accounts` | 列出所有账号 |
| `remove-account --name N` | 删除账号 |
| `set-default-account --name N` | 设置默认账号 |

### 搜索发现

| 命令 | 用途 |
|------|------|
| `list-feeds [--channel C]` | 首页/板块推荐（穿搭/美食/彩妆/影视/职场/情感/家居/游戏/旅行/健身） |
| `search-feeds --keyword K [--sort-by S --note-type T]` | 搜索笔记 |
| `get-feed-detail --feed-id ID --xsec-token T [--xsec-source S]` | 笔记详情+评论（搜索结果用 `pc_search`） |
| `user-profile --user-id UID --xsec-token T` | 用户主页 |

### 发布

| 命令 | 用途 |
|------|------|
| `fill-publish --title-file F --content-file F --images I [--tags T...]` | 图文表单 |
| `fill-publish-video --title-file F --content-file F --video V` | 视频表单 |
| `fill-text2image --title-file F --content-file F` | 文字配图（分步） |
| `publish-text2image --content-file F [--title-file F]` | 文字配图（一步发布） |
| `long-article --title-file F --content-file F` | 长文 |
| `select-template --name N` | 长文选模板 |
| `next-step --content-file F [--tags T...]` | 长文下一步 |
| `click-publish` | 确认发布 |
| `save-draft` | 保存草稿 |
| `publish --title-file F --content-file F --images I` | 图文一步发布 |
| `publish-video --title-file F --content-file F --video V` | 视频一步发布 |

### 互动

| 命令 | 用途 |
|------|------|
| `post-comment --feed-id ID --xsec-token T [--xsec-source S] --content C` | 发评论 |
| `reply-comment --feed-id ID --xsec-token T [--xsec-source S] --comment-id CID --content C` | 回复评论 |
| `like-feed --feed-id ID --xsec-token T [--xsec-source S] [--unlike]` | 点赞/取消点赞 |
| `favorite-feed --feed-id ID --xsec-token T [--xsec-source S] [--unfavorite]` | 收藏/取消收藏 |
| `list-notifications [--tab mentions\|likes\|connections]` | 通知列表 |
| `reply-notification --index N --content C` | 回复通知 |
| `like-notification --index N` | 点赞通知 |

### 去重与限流（纯本地）

| 命令 | 用途 |
|------|------|
| `check-interacted --feed-ids ID... [--notification-ids NID...] [--authors JSON] [--check-author-days N]` | 批量去重查询 |
| `sync-notifications` | 首次同步：标记所有已有通知为已处理 |
| `check-watermark` | 检查通知水位线是否已初始化 |

### 数据分析（创作服务平台）

| 命令 | 用途 |
|------|------|
| `list-my-notes` | 我的笔记列表 + 深度分析（曝光/CTR/观看时长/涨粉） |
| `get-dashboard` | 账号总览（粉丝/7 日数据/环比/同类百分位排名） |
| `get-fans-profile` | 粉丝画像（性别/年龄/兴趣/地域） |
| `record-interact --feed-id ID --type T --author A` | 记录互动 |
| `check-reply-limit --pairs JSON` | 检查同帖同用户回复上限 |
| `record-reply --feed-id ID --user-id UID --notification-id NID` | 记录回复 |

---

## Phase 0：初始化（用户触发一次）

1. 启动 Chrome：`python scripts/chrome_launcher.py`
2. 登录：`python scripts/cli.py login` → 用户扫码
3. 对话引导采集策略（5 组）：账号定位 → 人设风格 → 运营策略 → 目标受众 → 安全设置
4. 按 `assets/strategy-template.json` 生成 strategy.json
5. 创建工作目录：`mkdir -p ~/.openclaw/workspace/xhs-autopilot/{content-calendar,drafts,published,analytics,logs}`
6. 注册 Cron：`bash scripts/setup_cron.sh` → `openclaw cron list` 验证

---

## Phase 1：深度选题调研（07:00）

### 1a. 站内搜索

1. 读取 strategy.json → 赛道/关键词/内容支柱
2. `search-feeds --keyword "{赛道词}" --sort-by "最多点赞" --note-type "图文"` → Top 20 热帖
3. `search-feeds --keyword "{赛道词}" --sort-by "最新"` → 近期趋势
4. `list-feeds --channel "{板块}"` → 推荐流补充

### 1b. 爆款拆解（核心步骤）

从 1a 中选 **3-5 篇高互动笔记** → `get-feed-detail` 逐篇深度阅读，对每篇提取：
- **标题模式**（数字型/对比型/提问型/痛点型/悬念型）
- **开头 hook 手法**（前 3 行用了什么技巧吸引继续看）
- **正文结构**（总分总/步骤型/清单型/故事型）
- **互动引导**（结尾怎么引导评论/收藏）
- **评论区 Top 5 热评**（用户真正关心什么 → 决定内容侧重点）
- **使用的标签**（爆款用了哪些 tag）

### 1c. 站外调研

- WebSearch "{赛道} 最新动态 {当前月份}"
- WebSearch "{选题关键词} 最新消息"
- 提取时效性素材（新产品/新政策/热门事件），判断蹭热点机会

### 1d. 输出选题卡片

保存到 `content-calendar/{date}.json`，每个选题包含：
```
topic, angle, reference_notes[爆款ID], title_patterns[高CTR模式],
hot_tags[], trending_material(时效性素材), comment_insights(评论区洞察), priority
```

保存爆款拆解报告到 `content-calendar/{date}-research.json`

---

## Phase 2：基于爆款的内容创作（09:00）

### 2a. 创作输入

读取全部上下文：
- `content-calendar/{today}.json` → 选题卡片 + 爆款拆解报告
- `strategy.json` → 人设/风格/禁用词
- `references/copywriting.md` → 文案公式
- `analytics/` 最近 5 篇笔记表现 → 知道哪种内容有效、哪种翻车

### 2b. 结构化生成（对标爆款，非自由发挥）

**标题**：生成 5 个候选，每个标注模仿了哪个爆款的模式
- 例："Cursor vs Claude Code，我用半年后说实话" → 模式：对比型+时间背书+悬念，参考爆款 #3

**正文**：按拆解出的最佳结构生成
- 开头 → 必须有 hook（参考爆款的开头手法：提问/痛点/数据/反常识）
- 中间 → 干货/步骤/对比（参考爆款的主体结构）
- 结尾 → 互动引导（"你们觉得呢？""评论区聊聊""收藏备用"）

**tags**：三层策略
- 大流量标签（从爆款提取的高频 tag）+ 精准标签（赛道细分）+ 长尾标签（选题特有）
- 候选池 10-15 个，脚本随机选 3-6 个
- ⚠️ **标签不能含空格**：如 "Claude Code" → "ClaudeCode"，"Vibe Coding" → "VibeCoding"

### 2c. 决定发布参数

根据内容类型决定 location/content_type/original/collection 等

---

## Phase 2.5：发布前三层校验

⚠️ **笔记写完后、fill-publish 之前，必须通过以下三层检查。任一层不过 → 修改后重检。**

### 第一层：内容质量检查

- [ ] **Hook 检查** — 开头 3 行是否包含：提问/痛点/数据/悬念/反常识？→ 没有 → 重写开头
- [ ] **排版检查** — 段落用空行分隔？有小标题或 emoji 分隔符？正文 800-1200 字？
- [ ] **互动引导** — 结尾是否有引导评论/收藏的话术？→ 没有 → 补一句
- [ ] **AI 味检测** — 是否包含："值得一提的是"/"总的来说"/"需要注意的是"/"综上所述"/"不可否认"/"毋庸置疑" → 有 → 替换为口语化表达

### 第二层：爆款对标检查

- [ ] **标题对标** — 标题是否匹配调研阶段发现的高 CTR 模式？自己历史 CTR > 15% 的标题是什么模式？→ 不匹配 → 重写
- [ ] **标签覆盖** — 候选池是否包含爆款高频 tag？是否三层覆盖（大流量+精准+长尾）？→ 缺失 → 补充
- [ ] **结构匹配** — 正文结构是否接近拆解出的最佳结构？开头/中间/结尾节奏合理？

### 第三层：合规预检

- [ ] **审核红线** — 检查 strategy.json 中 `banned_patterns`（从历史审核拒绝中学到的违规模式）
- [ ] **绝对化用语** — "第一"/"最好"/"唯一"/"100%" → 改为相对表述（"我用下来觉得…"）
- [ ] **敏感内容** — 竞品品牌直接点名对比？→ 模糊化；涉及价格/收入？→ 确认是否需要

三层全过 → 保存 `drafts/{date}-{seq}.json` → 进入 Phase 3

---

## Phase 3：发布（10:00/16:00）

⚠️ **机械检查（全部确认才执行）：**
1. 标题写入 /tmp/xhs-title.txt（不内联中文到命令行）
2. 正文**完整**写入 /tmp/xhs-content.txt（确认未截断）
3. 图片路径是绝对路径或 HTTP URL
4. 标题长度 ≤ 20（汉字=1，ASCII 每两个=1）
5. tags 通过 `--tags` 传入（不写进正文文件）

执行：`check-login` → 从 drafts/ 取笔记 → 根据类型选对应 fill 命令 → `click-publish` → 记录到 `published/`

详细发布流程见 `skills/xhs-publish/SKILL.md`。

---

## Phase 4：互动巡逻（14:00）

1. `check-login` → 未登录则跳过
2. 获取当前用户 ID（用于过滤自己的笔记）
3. 随机混合获取目标（避免行为模式单一）：
   - `list-feeds --channel "{板块}"` / `search-feeds --keyword "{赛道词}" --sort-by "最新"` / `list-feeds`
4. ⚠️ **过滤（必做）**：
   - 跳过自己的笔记（user.userId == 当前用户 ID）
   - `check-interacted --feed-ids ... --authors '{"id":"昵称",...}'` → interacted=true 或 author_warnings 有记录的跳过
5. 对每个未互动的笔记（遵守限额）：
   a. `get-feed-detail` → 读内容（⚠️ 搜索结果帖子必须加 `--xsec-source pc_search`，推荐页用默认 `pc_feed`）
   b. 按「评论规则」生成评论 → `post-comment`（⚠️ `--xsec-source` 同上）
   c. ⚠️ `record-interact --feed-id ID --type comment --author "昵称"`（每次互动后立即执行）
   d. 50-70% 概率 `like-feed`（也 record-interact，⚠️ `--xsec-source` 同上）
   e. 随机间隔 2-5 分钟，每 session_limit 次后休息

---

## Phase 5：通知互动（20:00）

⚠️ **首次运行前提**：先 `check-watermark` → 如果 `initialized=false`，必须先执行 `sync-notifications` 标记所有已有通知为已处理，否则会重复回复历史通知。

1. `list-notifications --tab mentions`
2. ⚠️ **三层去重过滤（必做，按顺序执行）**：
   - **第一层：通知级去重** — `check-interacted --notification-ids id1 id2 ...` → interacted=true 的跳过（已处理过的通知）
   - **第二层：对话深度限制** — `check-reply-limit --pairs '[{"feed_id":"noteId","user_id":"userId"},...]'` → can_reply=false 的跳过（同帖同用户已回复 ≥2 次）
   - **第三层：内容过滤** — 跳过：hasReplyButton=false / "原评论已删除" / 纯表情([赞R][笑哭R]) / 营销引流(私信/加微/咨询)
3. ⚠️ **防无限对话规则**：
   - 如果 `targetCommentContent`（我们说的话）存在 → 说明这是「对方回复了我们的回复」→ 属于来回对话
   - 来回对话场景：只在对方**提出新问题**或**补充有价值信息**时才回复，简单附和/感谢/表情不回
   - 同一用户同一帖子最多回复 **2 次**（默认上限），到达后不再回复该用户
4. 值得回复的场景（通过三层过滤后）：
   - 新评论（targetCommentContent 为空）→ 用户直接评论我的帖子，优先回复
   - 作者回复(isAuthor=true) → 帖子原作者，礼貌互动
   - 用户提出具体问题或求助 → 简短有用的回答
5. 执行回复：`reply-notification --index N --content "..."`（命令内部自动写入通知日志）
6. 回复后记录：⚠️ `record-reply --feed-id {noteId} --user-id {userId} --notification-id {通知id}`
7. domLiked=false 的可 `like-notification`
8. 间隔 1-3 分钟，每次 5-10 条，不必全部回复

---

## Phase 6：数据复盘与策略进化（22:00）

### 6a. 数据采集

1. `list-my-notes` → 获取全部笔记的深度分析数据（曝光/CTR/观看时长/涨粉/审核状态）
2. `get-dashboard` → 获取账号 7 日总览 + 环比 + 同类百分位排名
3. `get-fans-profile` → 获取粉丝画像（性别/兴趣/地域变化）
4. 读取 logs/ 互动统计 → 汇总今日互动效果

### 6b. 分析（agent 推理，基于以上数据）

对每篇笔记分析漏斗：
```
曝光(impressions) → CTR(click_through_rate) → 观看时长(avg_view_duration) → 互动(likes/favs/comments)
```
- **CTR < 10%** → 标题/封面问题（不够吸引点击）
- **CTR > 15% 但观看时长 < 15s** → 标题好但内容不留人
- **观看时长 > 30s 但互动少** → 内容好但缺互动钩子（提问/投票/引导评论）
- **fans_gained > 0** → 该内容有涨粉能力，分析其标题模式和选题方向
- **audit_status = rejected** → 学习审核红线，记录到 strategy.json 的禁用规则

对比同类型笔记，找出最有效的：选题方向、标题模式、发布时间、内容长度

### 6c. 策略自动调整

基于分析结果，**自主修改** strategy.json 中的以下字段：

| 可调字段 | 调整逻辑 |
|---------|---------|
| `content_strategy.pillars[].weight` | 表现好的内容支柱权重提高 |
| `content_strategy.keywords` | 加入高 CTR 笔记的选题关键词 |
| `content_strategy.tags_pool` | 更新标签候选池（保留高互动标签） |
| `schedule.publish_times` | 调整到数据表现最好的时段 |
| `schedule.publish_frequency` | 根据涨粉效率决定增减频率 |
| `interaction.daily_limits` | 根据风控信号调整互动限额 |
| `content_strategy.banned_patterns` | 从审核拒绝中学习，加入禁用模式 |

⚠️ **不动区域**（只能用户主动修改）：`account`（赛道）、`persona`（人设风格/语言风格/emoji 密度）、`safety`

### 6d. 输出

1. 保存日报到 `analytics/{date}.json`（含原始数据 + 分析结论 + 策略变更记录）
2. 如有策略变更 → 记录变更原因到日报（如："标题模式'XX vs YY'CTR 21%，权重从 0.2 提升到 0.4"）
3. 通知用户日报摘要（含关键指标变化和策略调整）

---

## Phase 7：登录巡检（02:00）

1. `check-login` → 首次未登录时通知用户扫码，从未登录恢复时通知"自动驾驶已恢复"
2. Chrome 异常 → `python scripts/chrome_launcher.py --headless` 重启

---

## 评论规则（所有评论/回复场景通用）

❌ **禁止：** 万能废话（"写得很好感谢分享"）/ 零信息量（"学到了收藏了"）/ 敷衍赞美（"太棒了！"）/ AI 模板（"感谢博主分享受益匪浅"）/ 连续两条结构相同 / 不提帖子具体内容

✅ **要求：** 必须提及帖子**具体内容**（某道菜/某步骤/某观点）；长度随机 5-50 字；语气随机（提问/共鸣/补充/感叹/吐槽/分享经验）；50-70% 概率加表情（见 `references/emoji-reference.md`）

**生成：** 读帖子 → 提取 1-2 个具体细节 → 随机选语气 → 口语化评论 → 随机加表情

---

## 意图路由（手动操作时）

| 意图 | 路由 |
|------|------|
| 登录/检查/切换账号 | `skills/xhs-auth/SKILL.md` |
| 搜索/查看笔记/浏览首页 | `skills/xhs-explore/SKILL.md` |
| 评论/回复/点赞/收藏 | `skills/xhs-interact/SKILL.md` |
| **帮我写一篇/创作笔记** | `skills/xhs-content-ops/SKILL.md` → 内容创作（完整流程） |
| **发布已有内容/上传图文视频** | `skills/xhs-publish/SKILL.md` |
| 竞品分析/热点追踪/批量互动 | `skills/xhs-content-ops/SKILL.md` |
| **看数据/哪篇最火/涨粉情况** | `skills/xhs-content-ops/SKILL.md` → 数据分析 |
| **粉丝画像/粉丝是什么人** | `skills/xhs-content-ops/SKILL.md` → 粉丝分析 |
| **审核没过/为什么被限流** | `skills/xhs-content-ops/SKILL.md` → 审核诊断 |
| 设置/修改运营策略 | Phase 0 setup 流程 |

⚠️ **"帮我写一篇" vs "发布这篇"的区别**：
- "帮我写一篇关于 XX 的笔记" → xhs-content-ops（完整创作流程：调研→创作→校验→发布）
- "帮我发布这篇（用户已提供标题+正文+图片）" → xhs-publish（只处理发布机械流程）

## 用户运行时指令

| 指令 | 效果 |
|------|------|
| "看今天选题" | 读 content-calendar/ |
| "修改发布时间" | openclaw cron edit |
| "暂停互动" | openclaw cron disable |
| "看数据/哪篇最火" | `list-my-notes` + `get-dashboard` |
| "粉丝画像" | `get-fans-profile` |
| "换赛道" | 更新 strategy.json（仅用户主动修改） |
| "手动写一篇" | → xhs-content-ops 完整创作流程 |
| "审核没过" | → xhs-content-ops 审核诊断 |

## 参考资料

| 文件 | 何时读 |
|------|-------|
| `references/copywriting.md` | 创作时 |
| `references/strategy-schema.md` | 配置时 |
| `references/troubleshooting.md` | 出错时 |
| `references/emoji-reference.md` | 评论/回复时 |
