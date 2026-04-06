---
name: xhs-interact
description: >
  Use when 用户要求在小红书上发评论、回复评论、点赞、收藏、
  查看通知、回复通知时触发。
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F4AC"
    os: [darwin, linux]
---

# 小红书社交互动

## 工具边界

所有操作只通过 `python scripts/cli.py <子命令>` 执行。禁止 MCP 工具、外部项目或任何非本项目实现。

## 账号选择（前置）

运行 `list-accounts`：0 个 → 不加 `--account`；1 个 → 自动使用；多个 → 询问用户。选定后全程固定。

---

## ⚠️ 互动前检查（每次必须确认）

1. [ ] 有 feed-id？（24 位十六进制，不是 comment-id）
2. [ ] 有 xsec-token？（与 feed-id 配对，从同一接口返回）
3. [ ] content 非空且非模板句？
4. [ ] 评论/回复内容已经用户确认？

---

## 发评论

⚠️ `--feed-id`、`--xsec-token`、`--content` 缺任何一个都会 404 或报错

⚠️ **`--xsec-source` 必须与 token 来源匹配**：搜索结果用 `pc_search`，推荐页用 `pc_feed`（默认）。

```bash
python scripts/cli.py post-comment \
  --feed-id <noteId> --xsec-token <xsecToken> --content "评论"
# 搜索结果帖子必须加 --xsec-source pc_search
python scripts/cli.py post-comment \
  --feed-id <noteId> --xsec-token <xsecToken> --xsec-source pc_search --content "评论"
```

❌ 常见错误：漏 `--xsec-token` → 404 · 用 comment-id 当 feed-id → 404 · 搜索结果帖子未加 `--xsec-source pc_search` → "当前笔记暂时无法浏览"

## 回复评论

⚠️ 还需 `--comment-id` 或 `--user-id` 至少一个

```bash
python scripts/cli.py reply-comment \
  --feed-id <帖子ID> --xsec-token <xsecToken> \
  --comment-id <评论ID> --content "回复"
# 搜索结果帖子加 --xsec-source pc_search
```

## 点赞 / 收藏

```bash
python scripts/cli.py like-feed --feed-id ID --xsec-token TOKEN [--xsec-source pc_search]
python scripts/cli.py favorite-feed --feed-id ID --xsec-token TOKEN [--xsec-source pc_search]
# 取消：加 --unlike 或 --unfavorite
```

## 通知

```bash
python scripts/cli.py list-notifications                    # 评论和@（默认）
python scripts/cli.py list-notifications --tab likes        # 赞和收藏
python scripts/cli.py list-notifications --tab connections   # 新增关注

python scripts/cli.py reply-notification --index N --content "回复"
python scripts/cli.py like-notification --index N
```

通知字段：`commentContent`（对方说的）、`targetCommentContent`（我们说的）、`noteTitle`、`hasReplyButton`、`domLiked`。

## 去重（互动前必查，互动后必记）

```bash
# 查：批量检查是否已互动（feed 或 notification）
python scripts/cli.py check-interacted --feed-ids id1 id2 --authors '{"id1":"作者1"}'
python scripts/cli.py check-interacted --notification-ids nid1 nid2

# 查：同帖同用户回复次数（默认上限 2 次，防止无限对话）
python scripts/cli.py check-reply-limit --pairs '[{"feed_id":"x","user_id":"y"}]'

# 记：互动后立即记录
python scripts/cli.py record-interact --feed-id ID --type comment --author "昵称"
python scripts/cli.py record-reply --feed-id ID --user-id UID --notification-id NID
```

⚠️ `reply-notification` 执行成功后会自动写入通知日志，后续 `check-interacted --notification-ids` 可查到。但 `record-reply` 仍需手动调用以追踪同帖同用户回复次数。

---

## 评论规则（强制）

❌ **禁止：** 万能废话（"写得很好感谢分享"）/ 零信息量（"学到了收藏了"）/ 敷衍赞美（"太棒了！"）/ AI 模板（"感谢博主分享受益匪浅"）/ 连续两条结构相同 / 不提帖子具体内容

✅ **要求：** 必须提及帖子**具体内容**；长度随机 5-50 字；语气随机（提问/共鸣/补充/感叹/吐槽/分享经验）；50-70% 概率加表情（见 `references/emoji-reference.md`）

**生成：** 读帖子 → 提取 1-2 个具体细节 → 随机选语气 → 口语化 → 随机加表情

---

## 失败处理

- **404**：检查 feed-id 和 xsec-token 是否正确配对
- **评论失败**：检查是否含敏感词
- **重复评论**：CLI 返回 `"duplicate": true`，跳过
- **未登录**：提示先登录（xhs-auth）
