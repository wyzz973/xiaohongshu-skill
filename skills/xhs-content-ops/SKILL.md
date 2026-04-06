---
name: xhs-content-ops
description: >
  Use when 用户要求写笔记、创作发布、竞品分析、热点追踪、批量互动、
  查看数据、看涨粉情况、粉丝画像、哪篇最火、审核没过等复合运营任务时触发。
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F4CA"
    os: [darwin, linux]
---

# 小红书复合内容运营

## 工具边界

所有操作只通过 `python scripts/cli.py <子命令>` 执行。禁止 MCP 工具、外部项目或任何非本项目实现。

## 账号选择（前置）

运行 `list-accounts`：0 个 → 不加 `--account`；1 个 → 自动使用；多个 → 询问用户。选定后全程固定。

---

## 输入判断

1. "帮我写一篇 / 创作 / 发一篇关于XX的笔记" → **内容创作（完整流程）**
2. "竞品分析 / 分析竞品 / 对比笔记" → 竞品分析
3. "热点追踪 / 热门话题 / 最近什么火" → 热点追踪
4. "批量互动 / 评论策略" → 互动管理
5. "看数据 / 哪篇最火 / 涨粉情况" → **数据分析**
6. "粉丝画像 / 粉丝是什么人" → **粉丝分析**
7. "审核没过 / 为什么被限流" → **审核诊断**

---

## 内容创作（完整流程，手动版 Phase 1+2+2.5）

与自动模式相同的深度，但每步和用户确认。

### Step 1: 深度调研

1. 确认创作主题/方向
2. **站内搜索**：
   - `search-feeds --keyword "主题" --sort-by 最多点赞` → Top 热帖
   - `search-feeds --keyword "主题" --sort-by 最新` → 近期趋势
3. **爆款拆解**（选 3-5 篇高互动笔记）：
   - `get-feed-detail --xsec-source pc_search` 逐篇深度阅读（搜索结果必须用 `pc_search`）
   - 提取：标题模式、开头 hook、正文结构、互动引导、评论区热议、使用标签
   - 向用户报告拆解结论
4. **站外调研**：
   - WebSearch 搜最新资讯/热点事件
   - 向用户报告可结合的时效性素材
5. 向用户确认选题角度和切入点

### Step 2: 对标爆款创作

1. 读取自己最近笔记表现（`list-my-notes` 的 summary）→ 知道什么有效
2. 生成标题 5 个候选（标注模仿了哪个爆款模式）→ 用户选择
3. 生成正文（开头 hook + 干货主体 + 互动引导结尾）→ 用户确认
4. 生成 tags 候选池（大流量+精准+长尾三层）

### Step 3: 三层校验

发布前必须通过三层检查，向用户报告检查结果：

**第一层：内容质量** — hook？排版？互动引导？AI 味？
**第二层：爆款对标** — 标题匹配高 CTR 模式？tags 三层覆盖？结构合理？
**第三层：合规预检** — banned_patterns？绝对化用语？敏感内容？

全部通过 → 用户确认 → 发布（遵守 xhs-publish 流程）

---

## 数据分析

用户说"看数据 / 哪篇最火 / 涨粉了吗 / 这周表现怎么样"时触发。

```bash
list-my-notes     # 逐篇深度分析（曝光/CTR/观看时长/涨粉）
get-dashboard     # 账号 7 日总览 + 环比 + 同类百分位排名
```

呈现方式：
- 笔记排行表（按观看/涨粉/CTR 排序）
- 漏斗分析（曝光→点击→观看→互动，哪个环节瓶颈）
- 对比上期数据（环比变化趋势）
- 给出可执行的改进建议

## 粉丝分析

```bash
get-fans-profile  # 性别/兴趣/地域 + 活跃粉丝
```

呈现：粉丝画像表格 + 内容策略建议（如"65% 女性粉丝，可增加XX类内容"）

## 审核诊断

用户说"审核没过 / 为什么被限流 / 那篇怎么了"时：

1. `list-my-notes` → 找到 audit_status != published 的笔记
2. 向用户展示被拒笔记列表
3. 报告审核原因和平台建议（从 strategy.json 的 banned_patterns）
4. 建议修改方向

---

## 竞品分析

1. 确认关键词/竞品账号
2. `search-feeds --keyword "关键词" --sort-by 最多点赞`
3. 选 3-5 篇 → `get-feed-detail --xsec-source pc_search` 逐一拆解
4. 输出报告：标题风格 / 正文结构 / 标签使用 / 互动数据对比

## 热点追踪

1. 确认追踪领域
2. `search-feeds --keyword K --sort-by 最新 --publish-time 一周内` + `--sort-by 最多点赞`
3. WebSearch 搜站外热点
4. 输出：热度排名 / 爆款特征 / 选题建议

## 互动管理

1. 确认目标关键词
2. `search-feeds --keyword K --sort-by 最新` → 筛选适合互动的笔记
3. `get-feed-detail --xsec-source pc_search` → 生成评论建议 → 用户确认 → `post-comment --xsec-source pc_search`
4. 可选 `like-feed --xsec-source pc_search` / `favorite-feed --xsec-source pc_search`
5. 每次间隔 30-60 秒
