---
name: xhs-interact
description: 小红书互动场景 — 评论、回复、点赞、收藏、通知处理、互动去重
version: 2.0.0
---

# 互动场景

## 能力声明

本 Skill 处理小红书账号的全链路社交互动：
- 在笔记下发表评论（含搜索来源笔记）
- 回复他人评论
- 点赞/收藏笔记
- 查看并回复/点赞通知
- 互动去重（查询已互动记录、记录新互动、回复次数限制）

不能做：关注/取关用户、私信、举报、修改已发布评论。

## 命令清单

| 命令 | 用途 | 必需参数 | 可选参数 | 退出码 |
|------|------|---------|---------|--------|
| `post-comment` | 在笔记下发表评论 | `--feed-id`, `--xsec-token`, `--content` | `--xsec-source` | 0=成功, 1=未登录, 2=失败 |
| `reply-comment` | 回复某条评论 | `--feed-id`, `--xsec-token`, `--comment-id`, `--content` | `--xsec-source` | 0=成功, 1=未登录, 2=失败 |
| `like-feed` | 点赞笔记 | `--feed-id`, `--xsec-token` | `--xsec-source`, `--unlike` | 0=成功, 1=未登录, 2=失败 |
| `favorite-feed` | 收藏笔记 | `--feed-id`, `--xsec-token` | `--xsec-source`, `--unfavorite` | 0=成功, 1=未登录, 2=失败 |
| `list-notifications` | 获取通知列表 | 无 | `--tab` (comments/likes/connections) | 0=成功, 1=未登录, 2=失败 |
| `reply-notification` | 回复通知中的评论 | `--index`, `--content` | 无 | 0=成功, 1=未登录, 2=失败 |
| `like-notification` | 点赞通知中的内容 | `--index` | 无 | 0=成功, 1=未登录, 2=失败 |
| `check-interacted` | 批量查询是否已互动 | `--feed-ids` (space-separated) | `--authors` (JSON) | 0=成功, 2=失败 |
| `record-interact` | 记录新互动 | `--feed-id`, `--type`, `--author` | 无 | 0=成功, 2=失败 |
| `check-reply-limit` | 检查同帖同用户回复次数是否超限 | 无 | `--pairs` (JSON) | 0=未超限, 2=超限/失败 |
| `record-reply` | 记录回复（用于追踪同帖同用户次数） | `--feed-id`, `--user-id`, `--notification-id` | 无 | 0=成功, 2=失败 |
| `sync-notifications` | 首次同步：将已有通知标记为已读 | 无 | 无 | 0=成功, 2=失败 |
| `check-watermark` | 检查通知水位线 | 无 | 无 | 0=成功, 2=失败 |

CLI 前缀：`python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py`

## 关键规则

### CRITICAL: xsec-source 必须与 token 来源匹配

当笔记来源于搜索结果（`search-feeds`）时，**所有互动命令**（`post-comment`、`reply-comment`、`like-feed`、`favorite-feed`）都必须传入 `--xsec-source pc_search`。

来源于推荐页（`list-feeds`）时使用默认值 `pc_feed`，无需显式传入。

遗漏此参数会导致"当前笔记暂时无法浏览"报错（HTTP 404 或平台拦截）。

### CRITICAL: 评论前必查去重，评论后必记互动

每次执行 `post-comment` 或 `reply-comment` 之前：
1. 必须先调用 `check-interacted --feed-ids <id>` 确认未互动过
2. 互动成功后立即调用 `record-interact --feed-id <id> --type comment --author <昵称>`

不得跳过上述步骤，否则可能对同一笔记重复评论。

## 执行协议

### 场景 A：评论互动

目标：在一篇笔记下发表评论，含完整去重保护。

#### 前置条件
- 已通过 `check-login` 确认登录
- 持有目标笔记的 `feed-id` 和 `xsec-token`（从 `search-feeds` 或 `list-feeds` 返回）
- 已生成评论内容（见评论规范）

#### 执行步骤

1. 调用 `check-interacted --feed-ids <feed-id>`
   - 返回 `"interacted": true` → 跳过，记录日志，结束
   - 返回 `"interacted": false` → 继续

2. 调用 `post-comment`：
   ```bash
   # 推荐页笔记
   python .../cli.py post-comment \
     --feed-id <noteId> --xsec-token <token> --content "评论内容"

   # 搜索结果笔记（必须加 --xsec-source pc_search）
   python .../cli.py post-comment \
     --feed-id <noteId> --xsec-token <token> \
     --xsec-source pc_search --content "评论内容"
   ```

3. 调用 `record-interact --feed-id <noteId> --type comment --author <昵称>`

#### 后置校验
- 返回 JSON 包含 `"success": true`
- `record-interact` 返回 exit_code=0

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=2, "404" | 检查 feed-id 与 xsec-token 是否来自同一接口；搜索结果补 `--xsec-source pc_search` |
| exit_code=2, "sensitive" / 含敏感词 | 修改评论内容后重试 |
| exit_code=2, "duplicate" | 平台判定重复评论，跳过该笔记 |
| exit_code=1 | 未登录，先执行 xhs-auth 场景 A |

---

### 场景 B：回复评论

目标：回复笔记下的某条评论。

#### 前置条件
- 持有 `feed-id`、`xsec-token`、`comment-id`
- 已通过 `check-reply-limit` 确认同帖同用户未超限（默认上限 2 次）

#### 执行步骤

1. 调用 `check-reply-limit --pairs '[{"feed_id":"<id>","user_id":"<uid>"}]'`
   - exit_code=2 → 超限，跳过
   - exit_code=0 → 继续

2. 调用 `reply-comment`：
   ```bash
   python .../cli.py reply-comment \
     --feed-id <noteId> --xsec-token <token> \
     --comment-id <commentId> --content "回复内容"
   # 搜索来源必须加 --xsec-source pc_search
   ```

3. 调用 `record-reply --feed-id <noteId> --user-id <uid> --notification-id <nid>`

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=2, "comment not found" | comment-id 失效（帖子已删），跳过 |
| exit_code=2, 其他 | 记录日志，等待 5 分钟后重试一次 |

---

### 场景 C：点赞/收藏

目标：点赞或收藏一篇笔记。

#### 执行步骤

```bash
# 点赞
python .../cli.py like-feed \
  --feed-id <noteId> --xsec-token <token> [--xsec-source pc_search]

# 收藏
python .../cli.py favorite-feed \
  --feed-id <noteId> --xsec-token <token> [--xsec-source pc_search]
```

- 返回 JSON 包含 `"success": true` → 完成
- 平台返回"已点赞"状态时视为成功，无需重试

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=2, "already liked" | 已点赞，直接跳过 |
| exit_code=2, "404" | xsec-token 来源与 xsec-source 不匹配，修正后重试 |

---

### 场景 D：通知处理

目标：读取未处理通知，对评论通知进行回复或点赞。

#### 执行步骤

1. 调用 `check-watermark` 确认是否有新通知
2. 调用 `list-notifications` 获取评论/回复列表
3. 遍历通知，对每条判断：
   - `hasReplyButton: true` 且未超回复限制 → 执行 `reply-notification`
   - 无需回复但值得互动 → 执行 `like-notification`
4. 处理后调用 `sync-notifications` 更新水位线（标记已处理）

```bash
python .../cli.py list-notifications
python .../cli.py reply-notification --index <N> --content "回复内容"
python .../cli.py like-notification --index <N>
python .../cli.py sync-notifications
```

#### 通知字段说明
- `commentContent` — 对方说的内容
- `targetCommentContent` — 我方原评论
- `noteTitle` — 所在笔记标题
- `hasReplyButton` — 是否可回复
- `domLiked` — 是否已点赞

#### 注意
- `reply-notification` 成功后会自动写入通知日志，`check-interacted --notification-ids` 可查到
- 仍需手动调用 `record-reply` 以追踪同帖同用户回复次数

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| list-notifications 返回空列表 | 无新通知，正常跳过 |
| reply-notification exit_code=2 | 通知索引失效（通知已更新），重新 list-notifications |

---

### 场景 E：去重管理

目标：查询已互动记录、记录新互动，防止重复操作。

#### 批量查询是否已互动

```bash
python .../cli.py check-interacted \
  --feed-ids id1 id2 id3 \
  --authors '{"id1":"作者昵称1","id2":"作者昵称2"}'
```

返回 JSON 中每个 feed-id 对应 `"interacted": true/false`。

#### 记录互动

```bash
# 发评论后
python .../cli.py record-interact \
  --feed-id <noteId> --type comment --author "作者昵称"

# 点赞后
python .../cli.py record-interact \
  --feed-id <noteId> --type like --author "作者昵称"
```

#### 回复次数检查

```bash
# 检查是否超限（默认上限 2 次/帖/用户）
python .../cli.py check-reply-limit \
  --pairs '[{"feed_id":"<id>","user_id":"<uid>"}]'
```

#### 首次初始化

首次运行前调用 `sync-notifications` 将已有通知标记为已读，避免对历史通知重复处理。

## 安全限制

| 操作 | 单次 Session 上限 | 每日上限 | 最小间隔 |
|------|-----------------|---------|---------|
| 评论（post-comment） | 8-10 条 | 20-25 条 | 2-5 分钟 |
| 回复通知（reply-notification） | 8-10 条 | 20-25 条 | 2-5 分钟 |
| 点赞（like-feed） | 15-20 次 | 40-50 次 | 随机 30-90 秒 |
| 收藏（favorite-feed） | 10-15 次 | 30-40 次 | 随机 30-90 秒 |

- 夜间 23:00-02:00 降频 50%；02:00-06:00 停止所有互动操作
- 遇到验证码弹窗 → 立即停止全部互动，记录日志，通知用户
- 遇到平台频控提示 → 停止当前操作，等待 30 分钟后重试

## 评论内容规范

评论必须自然、有实质内容，以下为强制要求：

**禁止：**
- 万能废话："写得很好感谢分享"
- 零信息量："学到了收藏了"
- 敷衍赞美："太棒了！"
- AI 模板句："感谢博主分享受益匪浅"
- 连续两条结构相同的评论
- 未提及帖子具体内容

**要求：**
- 必须提及帖子的 1-2 个具体细节
- 长度随机 5-50 字
- 语气随机轮换：提问 / 共鸣 / 补充信息 / 感叹 / 吐槽 / 分享经验
- 50-70% 概率加 XHS 表情（参见 `references/emoji-reference.md`）
- 口语化，避免书面语和完整长句

**生成流程：** 读取帖子正文 → 提取 1-2 个具体细节 → 随机选语气模板 → 口语化改写 → 按概率插入表情
