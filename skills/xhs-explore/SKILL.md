---
name: xhs-explore
description: >
  Use when 用户要求搜索小红书笔记、浏览首页推荐、查看笔记详情、
  查看用户主页、找博主、找帖子时触发。
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F50D"
    os: [darwin, linux]
---

# 小红书内容发现

## 工具边界

所有操作只通过 `python scripts/cli.py <子命令>` 执行。禁止 MCP 工具、外部项目或任何非本项目实现。

## 账号选择（前置）

运行 `list-accounts`：0 个 → 不加 `--account`；1 个 → 自动使用；多个 → 询问用户。选定后全程固定。

---

## 首页推荐

```bash
python scripts/cli.py list-feeds
python scripts/cli.py list-feeds --channel "美食"
# 可用板块：推荐/穿搭/美食/彩妆/影视/职场/情感/家居/游戏/旅行/健身
```

输出：`feeds` 数组（含 `id`、`xsec_token`、`note_card`）+ `count`。

## 搜索笔记

```bash
python scripts/cli.py search-feeds --keyword "关键词"
python scripts/cli.py search-feeds --keyword "关键词" \
  --sort-by 最多点赞 --note-type 图文 --publish-time 一周内
```

| 参数 | 可选值 |
|------|--------|
| `--sort-by` | 综合、最新、最多点赞、最多评论、最多收藏 |
| `--note-type` | 不限、视频、图文 |
| `--publish-time` | 不限、一天内、一周内、半年内 |
| `--search-scope` | 不限、已看过、未看过、已关注 |

## 笔记详情

`feed-id` 和 `xsec-token` 必须配对，从搜索/首页结果中获取。

⚠️ **`--xsec-source` 必须与 token 来源匹配**：搜索结果用 `pc_search`，推荐页用 `pc_feed`（默认）。来源不匹配会导致"当前笔记暂时无法浏览"。

```bash
# 推荐页帖子（默认 pc_feed）
python scripts/cli.py get-feed-detail --feed-id ID --xsec-token TOKEN
# 搜索结果帖子
python scripts/cli.py get-feed-detail --feed-id ID --xsec-token TOKEN --xsec-source pc_search
python scripts/cli.py get-feed-detail --feed-id ID --xsec-token TOKEN --xsec-source pc_search \
  --load-all-comments --click-more-replies --max-replies-threshold 10
```

## 用户主页

```bash
python scripts/cli.py user-profile --user-id UID --xsec-token TOKEN
```

## 结果呈现

- 笔记列表：标题、作者、互动数据
- 详情：完整正文、图片、评论
- 用户：基本信息 + 代表作
- 关键指标用 markdown 表格

## 失败处理

- **未登录**：提示先登录（参考 xhs-auth）
- **搜索无结果**：更换关键词或调整筛选
- **笔记/用户不可访问**：可能已删除或设为私密
