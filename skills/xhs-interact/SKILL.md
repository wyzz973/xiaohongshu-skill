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

### CRITICAL: 评论前必须先读评论区

**每次评论前必须执行：**
1. 调用 `get-feed-detail --load-all-comments` 获取帖子正文 + 已有评论（必须加 `--load-all-comments`，否则评论区为空）
2. 阅读评论区前 5-10 条真人评论，感受语气、长度、用词习惯
3. 模仿该评论区的真实风格生成评论（不是模仿某一条，是模仿整体氛围）
4. 如果评论区为空（0条），则根据帖子标题语气判断风格（吐槽型标题→吐槽/追问，教程型→追问细节，情绪型→共鸣短句）

这一步不可跳过。不同帖子的评论区风格差异很大：技术帖评论区偏理性追问，情绪帖评论区偏短句共鸣，吐槽帖评论区偏玩梗接话。你必须先读再写。

### 去 AI 味（最高优先级）

以下是被真人识破过的 AI 评论特征，**绝对禁止**：

| AI tell | 为什么暴露 | 正确做法 |
|---------|----------|---------|
| 每条都先肯定（"确实""说到点上了""这个思路很好"） | GPT 经典开头，连续 2 条就被认出 | 直接说事，不铺垫 |
| 肯定+经验+追问 三段式结构 | 每条结构一样=机器人 | 随机打破：只问、只吐槽、只补一句 |
| 书面化长句（"关键词密度之类的优化节点"） | 没人在评论区这么说话 | 短句口语："排名咋样？" |
| 一条评论覆盖多个点 | 真人评论只说一件事 | 一条只说一个点 |
| 每条都带追问 | 真人不会每条都问问题 | 有时只感叹/吐槽/分享，不问 |
| 过于完整（主谓宾齐全，标点正确） | 真人评论经常省略主语、没句号 | 允许不完整、省略、口语 |

### 评论风格库（随机轮换，不要连续用同一种）

**直接追问型：**
- "多agent互相调的时候稳吗？"
- "跑了多久了 中间挂过没"
- "这个能本地部署吗"

**吐槽/共鸣型：**
- "被context搞死过太多次了..."
- "我也是 折腾了一周才跑通"
- "哈哈哈这个坑我也踩过"

**补充信息型：**
- "试过xx 比这个快一点"
- "加个retry就好了 我之前也是这个问题"

**短句感叹型：**
- "牛"
- "这也太离谱了"
- "收了"

**反问/质疑型：**
- "但是成本呢？"
- "真有人用这个跑生产环境？"
- "速度能跟上吗"

### 基本要求

- 必须提及帖子的 1 个具体细节（不是泛泛而谈）
- 长度随机 3-40 字（真人评论大多很短）
- 50-70% 概率加 XHS 表情（参见 `references/emoji-reference.md`）
- 连续评论不能结构相同、语气相同
- 偶尔可以有错别字或不完整的句子（但不要刻意为之）

### 生成流程

```
get-feed-detail（读正文+评论区）
  → 感受评论区氛围（理性/情绪/玩梗/专业）
  → 提取 1 个具体细节
  → 从风格库随机选一种（不能跟上一条重复）
  → 用口语写出来
  → 检查：是否像上面表格里的 AI tell？是 → 重写
```
