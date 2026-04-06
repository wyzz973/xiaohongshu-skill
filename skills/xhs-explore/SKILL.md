---
name: xhs-explore
description: 小红书浏览场景 — 首页推荐、关键词搜索、笔记详情、用户主页
version: 2.0.0
---

# 浏览场景

## 能力声明

本 Skill 处理小红书内容发现与信息采集：
- 浏览首页推荐（按频道分类）
- 关键词搜索笔记（多维筛选）
- 获取笔记详情与评论
- 查看用户主页与作品列表

不能做：发布内容、发表评论、点赞收藏、修改账号资料。

## 命令清单

| 命令 | 用途 | 必需参数 | 可选参数 | 退出码 |
|------|------|---------|---------|--------|
| `list-feeds` | 首页推荐列表 | 无 | `--channel` | 0=成功, 1=未登录, 2=错误 |
| `search-feeds` | 关键词搜索笔记 | `--keyword` | `--sort-by`, `--note-type`, `--publish-time`, `--search-scope`, `--location` | 0=成功, 1=未登录, 2=错误 |
| `get-feed-detail` | 笔记详情+评论 | `--feed-id`, `--xsec-token` | `--xsec-source`, `--load-all-comments`, `--click-more-replies`, `--max-replies-threshold`, `--max-comment-items`, `--scroll-speed` | 0=成功, 1=未登录, 2=错误 |
| `user-profile` | 用户主页信息 | `--user-id`, `--xsec-token` | 无 | 0=成功, 1=未登录, 2=错误 |

CLI 前缀：`python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py`

### 参数说明

**list-feeds `--channel`**：推荐 / 穿搭 / 美食 / 彩妆 / 影视 / 职场 / 情感 / 家居 / 游戏 / 旅行 / 健身（默认：推荐）

**search-feeds 可选参数**：

| 参数 | 可选值 |
|------|--------|
| `--sort-by` | 综合、最新、最多点赞、最多评论、最多收藏 |
| `--note-type` | 不限、视频、图文 |
| `--publish-time` | 不限、一天内、一周内、半年内 |
| `--search-scope` | 不限、已看过、未看过、已关注 |
| `--location` | 任意地名字符串 |

## xsec-source 规则（重要）

`xsec-source` 必须与 token 的来源页面匹配：

| token 来源 | 必须传的值 |
|-----------|-----------|
| `list-feeds`（推荐页） | `pc_feed`（默认，可不传） |
| `search-feeds`（搜索结果） | `pc_search`（**必须显式传**） |

**违反此规则会导致"当前笔记暂时无法浏览"错误**。

规则延伸：搜索结果中获取的 feed-id + xsec-token 用于后续任何命令（`post-comment`、`reply-comment`、`like-feed`、`favorite-feed`）时，同样必须携带 `--xsec-source pc_search`。

## 执行协议

### 场景 A：浏览推荐页

#### 前置条件
- `check-login` 返回 `logged_in: true`

#### 执行步骤

1. 运行 `list-feeds`（或 `list-feeds --channel <频道名>`）
2. 解析返回 JSON 中的 `feeds` 数组，每条包含：
   - `id`：笔记 ID
   - `xsec_token`：访问令牌
   - `note_card`：标题、封面、作者、互动数据
3. 选取感兴趣的笔记，记录 `id` 和 `xsec_token`
4. 运行 `get-feed-detail --feed-id <id> --xsec-token <token>`（推荐页**不传** `--xsec-source`）
5. 解析详情：正文、图片列表、评论数组

#### 后置校验
- 确认返回 JSON 包含 `feeds` 字段且为非空数组

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=1 | 先执行 xhs-auth 场景 A 登录 |
| feeds 为空数组 | 网络异常或频道无内容，切换频道重试 |
| get-feed-detail 返回"无法浏览" | 检查是否误传了 `--xsec-source pc_search`，推荐页 token 不传此参数 |

---

### 场景 B：搜索笔记

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 确定搜索关键词

#### 执行步骤

1. 运行 `search-feeds --keyword "<关键词>"`（可附加筛选参数）
2. 解析返回 JSON 中的结果列表
3. 选取目标笔记，记录 `id` 和 `xsec_token`
4. 运行 `get-feed-detail --feed-id <id> --xsec-token <token> --xsec-source pc_search`
   - **搜索结果 token 必须加 `--xsec-source pc_search`**
5. 如需加载更多评论，追加 `--load-all-comments --click-more-replies --max-replies-threshold 10`

#### 后置校验
- 确认返回 JSON 包含关键词相关笔记

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| 返回结果为空 | 换宽泛关键词，或去掉 `--note-type`/`--publish-time` 筛选 |
| get-feed-detail 返回"无法浏览" | 确认已加 `--xsec-source pc_search`，token 不可跨场景复用 |
| exit_code=2 | 关键词含特殊字符，检查转义 |

---

### 场景 C：竞品对标分析

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 确定竞品赛道关键词（如："AI工具"、"自动化运营"）

#### 执行步骤

1. 运行 `search-feeds --keyword "<竞品关键词>" --sort-by 最多点赞 --note-type 图文`
2. 取排名前 5-10 的笔记，批量执行 `get-feed-detail`（每次均加 `--xsec-source pc_search`）
3. 对每篇笔记提取：
   - 标题结构（数字/痛点/疑问句式）
   - 正文框架（列表/步骤/对比）
   - 互动数据（点赞/评论/收藏比）
   - 高频话题标签
4. 汇总 winning patterns：
   - 高互动标题共性
   - 内容长度与格式偏好
   - 评论区用户痛点
5. 将分析结果写入 `logs/evolution.json` 的 `winning_patterns` 字段

#### 注意
- 同一关键词连续抓取超过 10 篇时，每次请求间隔 3-5 秒
- 不要对竞品笔记执行点赞/评论，仅观察

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| 部分笔记详情失败 | 跳过该条，继续抓取其余笔记 |
| 搜索结果与关键词无关 | 使用更精确的长尾词重试 |

---

### 场景 D：查看用户主页

#### 前置条件
- `check-login` 返回 `logged_in: true`
- 已知目标用户 ID（`user-id`）和对应 `xsec-token`（通常来自笔记详情中的作者信息）

#### 执行步骤

1. 运行 `user-profile --user-id <uid> --xsec-token <token>`
2. 解析返回 JSON：
   - 基本信息：昵称、粉丝数、关注数、获赞数
   - 代表作列表：近期笔记标题 + 互动数据

#### 后置校验
- 确认返回 JSON 包含 `user_info` 字段

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=2 + "用户不存在" | user-id 有误，从笔记详情重新获取 |
| 返回空作品列表 | 用户可能已设为私密账号 |

---

## 安全限制

- 浏览操作无频率硬限制，但需遵守页面加载间隔（每次导航后等待 3-5 秒）
- 连续抓取超过 20 个详情页时，建议暂停 30 秒后继续
- 不缓存 xsec-token 跨 session 复用，token 有时效性
- 遇到验证码弹窗 → 停止自动操作，通知用户手动处理
