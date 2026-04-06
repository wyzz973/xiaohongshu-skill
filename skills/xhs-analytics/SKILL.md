---
name: xhs-analytics
description: >
  Use when 用户要查看数据、哪篇最火、涨粉情况、粉丝画像、审核状态，
  或需要自我进化优化（更新 evolution.json、调整策略参数、生成周报）时触发。
version: 2.0.0
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
    emoji: "\U0001F4CA"
    os: [darwin, linux]
---

# 数据分析 & 自我进化场景

## 能力声明

本 Skill 处理小红书账号的数据读取与自我进化优化：
- 读取所有已发笔记的深度指标（曝光、CTR、观看时长、涨粉）
- 获取账号 7 日总览仪表盘（环比、百分位排名）
- 读取粉丝画像（性别/兴趣/地域分布）
- 基于真实数据更新 `logs/evolution.json` 的 winning/losing patterns 权重
- 当数据支持时调整 `strategy.json` 可变参数，并记录变更日志
- 每周日自动生成进化报告

不能做：修改账号资料、操作笔记内容、执行发布或互动操作。

## 命令清单

CLI 前缀：`python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py`

| 命令 | 用途 | 必需参数 | 可选参数 | 退出码 |
|------|------|---------|---------|--------|
| `list-my-notes` | 所有已发笔记 + 深度分析（曝光/CTR/观看时长/涨粉） | 无 | 无 | 0=成功, 1=未登录, 2=错误 |
| `get-dashboard` | 账号 7 日总览（趋势/环比/同类百分位） | 无 | 无 | 0=成功, 1=未登录, 2=错误 |
| `get-fans-profile` | 粉丝画像（性别/兴趣/地域） | 无 | 无 | 0=成功, 1=未登录, 2=错误 |

### list-my-notes 输出字段说明

返回 JSON，包含 `notes` 数组，每条笔记关键字段：

| 字段 | 含义 |
|------|------|
| `impressions` | 曝光量 — 笔记被推送到用户 feed 的次数（≠ 真实阅读） |
| `views` | 点击量/阅读量 — 用户实际点进笔记的次数 |
| `ctr` | 点击率 — `views / impressions`，衡量封面+标题吸引力，正常范围 5-25% |
| `avg_watch_time` | 平均阅读时长（秒）— 衡量内容留存，>30s 算良好，>60s 算优秀 |
| `likes` | 点赞数 |
| `comments` | 评论数 |
| `collects` | 收藏数 — 收藏率高（>点赞率）说明内容实用价值强 |
| `shares` | 转发数 |
| `fans_gained` | 该笔记带来的涨粉数 |
| `audit_status` | 审核状态：`published`=正常，`under_review`=审核中，`rejected`=被拒，`limited`=限流 |
| `note_type` | 笔记类型：`image`=图文，`video`=视频，`article`=长文 |
| `publish_time` | 发布时间（ISO 8601） |

CTR 计算：平台内部计算，`list-my-notes` 直接返回百分比值，无需手动计算。

## 执行协议

### 场景 A：每日数据复盘

#### 触发条件
用户说"看数据 / 今天表现 / 哪篇最火 / 涨粉了吗 / 这周怎么样"。

#### 执行步骤

1. 运行 `list-my-notes`，获取所有笔记逐篇指标
2. 运行 `get-dashboard`，获取账号 7 日汇总 + 环比趋势
3. 分析每篇笔记的 CTR / 互动率 / 涨粉贡献：
   - 按 `fans_gained` 降序 → 找出最强涨粉笔记
   - 按 `ctr` 降序 → 找出封面/标题最强笔记
   - 按 `avg_watch_time` 降序 → 找出内容留存最好的笔记
4. 比较不同类型（image/video/article）的平均 CTR 和涨粉效率
5. 比较不同发布时段的表现差异
6. 识别 Top 3 表现最佳笔记 + Bottom 3 表现最差笔记
7. 找出漏斗瓶颈：曝光→点击（CTR 低？）or 点击→互动（内容不够？）
8. 向用户输出可视化表格 + 可执行改进建议

#### 输出格式

```
笔记表现排行（按涨粉）
标题                    | CTR  | 时长  | 涨粉 | 类型
"Cursor vs Claude Code" | 18.2%| 77s  | +8  | 长文
...

漏斗分析
曝光 → 点击：平均 CTR X%（行业参考 10-15%）
瓶颈在：[曝光不足 / 点击率低 / 内容留存低 / 互动转化低]

改进建议：
1. ...
2. ...
```

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=1 | 先执行 check-login，重新认证后重试 |
| notes 数组为空 | 账号尚无发布笔记，跳过分析 |
| 某字段缺失 | 该笔记可能审核中，跳过并标注 |

---

### 场景 B：粉丝分析

#### 触发条件
用户说"粉丝画像 / 粉丝是什么人 / 受众分析 / 谁在看我"。

#### 执行步骤

1. 运行 `get-fans-profile`
2. 解析返回 JSON：性别分布、年龄段、地域 Top5、兴趣标签 Top10
3. 输出粉丝画像表格
4. 基于画像给出内容策略建议，例如：
   - 女性 >60% → 增加情感共鸣类内容
   - 25-34岁主导 → 职场/效率/副业选题更易共鸣
   - 一线城市集中 → 可使用较高认知密度的内容
   - 某兴趣标签占比高 → 优先围绕该标签出内容

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| exit_code=1 | 先执行 check-login |
| 粉丝数量不足 | 平台可能不返回画像，提示用户账号粉丝量需达到一定门槛 |

---

### 场景 C：自我进化优化

#### 触发条件
- 每日复盘后自动执行（daemon 运营循环的 F 阶段）
- 用户说"更新进化知识库 / 优化策略 / 哪些模式有效"

#### 执行步骤

1. **读取现有进化知识库**
   ```bash
   cat /Users/sd3/xhs-workspace/logs/evolution.json
   ```

2. **计算每个 pattern 的实际表现得分**
   - 将 `list-my-notes` 数据中最近 14 天的笔记与 `winning_patterns` 匹配
   - 匹配维度：pattern 类型（title_pattern / content_structure / content_type 等）
   - 计算近期使用过该 pattern 的笔记的平均 CTR、平均涨粉、平均时长
   - 与 pattern 历史证据比较：新数据好于历史 → 升权；差于历史 → 降权

3. **升级已验证的高效 pattern（weight +0.1）**
   - 条件：最近 14 天至少 2 篇笔记使用，且平均 CTR > 12% 或 平均涨粉 > 3
   - 更新 `evolution.json`：`weight += 0.1`，`verified_at` 更新为今天，`status` 保持 `active`

4. **降权弱效 pattern（weight -0.2）**
   - 条件：最近 14 天有使用，但平均 CTR < 5% 且 平均涨粉 < 1
   - 更新：`weight -= 0.2`；weight < 0.3 时将 `status` 改为 `deprecated`，并写入 `losing_patterns`

5. **标记过期 pattern（30 天未使用）**
   - 条件：`verified_at` 距今 > 30 天且最近笔记中未见该 pattern
   - 更新：`status` 改为 `stale`（不删除，保留历史）

6. **更新 strategy.json 可变参数（仅 MUTABLE 参数）**
   - MUTABLE 参数范围：`post_times`（发布时段）、`post_frequency`（每日频次上限）、`content_mix`（类型比例）、`hashtag_strategy`（标签策略）
   - CORE 参数（禁止修改）：`rate_limits`（评论/点赞/发布上限）、`safety_rules`、`account_info`
   - 触发调整的条件：连续 7 天数据支持（不是单日波动）
   - 例如：若图文 CTR 持续 < 视频 50%，则将 `content_mix.article_ratio` 上调 10%
   - 所有调整记录到 `docs/changelog.md`，格式：`[日期] 参数名: 旧值 → 新值 | 数据依据`

7. **每周日生成进化报告**
   - 文件路径：`logs/weekly-evolution-report-{YYYY-MM-DD}.json`
   - 内容：本周 Top3 pattern、升降权汇总、策略调整记录、下周重点方向

#### 注意事项
- evolution.json 修改前先备份（`cp evolution.json evolution.json.bak`）
- 所有写操作用 Python 解析后写回，不用 sed/awk 直接修改 JSON
- 若同一天已运行过自我进化，检查 `_last_updated` 字段，避免重复执行

#### 错误恢复
| 现象 | 恢复动作 |
|------|---------|
| evolution.json 不存在 | 用默认模板创建空文件，继续执行 |
| strategy.json 解析失败 | 停止修改，只更新 evolution.json |
| 数据不足（<5篇笔记） | 跳过权重计算，只更新 `_last_updated` |

---

### 场景 D：资料消化（用户输入学习）

#### 触发条件
用户提供外部资料：竞品拆解、爆款截图分析、运营经验、平台规则更新等。

#### 执行步骤

1. 仔细阅读用户提供的资料，提取可操作的 pattern
2. 为每个新 pattern 构造 evolution.json 条目：
   ```json
   {
     "id": "wp-NNN",
     "type": "title_pattern | content_structure | content_type | timing | hook_pattern",
     "pattern": "简洁描述这个 pattern",
     "evidence": "从资料中摘录的具体证据",
     "source": "user_input",
     "source_detail": "用户提供：[资料简述]",
     "verified_at": "今天日期",
     "status": "active",
     "weight": 0.6
   }
   ```
3. 检查 `winning_patterns` / `losing_patterns` 中是否已有相似条目，避免重复
4. 将新 pattern 追加到 `evolution.json`
5. 向用户确认：提取了哪些 pattern，ID 是什么，下次写稿时会如何应用

#### 注意
- `source: "user_input"` 的 pattern 初始 weight 设为 0.6（中等可信度），需后续数据验证
- 若与现有 winning_pattern 冲突，保留旧的并添加注释字段 `"conflict_note"`

---

## 安全限制

- 数据读取命令（list-my-notes / get-dashboard / get-fans-profile）无频率限制，可随时执行
- 写操作（修改 evolution.json / strategy.json）必须先读取现有文件，不可盲写
- strategy.json 的 CORE 参数（rate_limits / safety_rules / account_info）**禁止通过进化流程修改**
- 所有 strategy.json 变更必须记录到 `docs/changelog.md`，可追溯
- 进化优化只基于真实数据，不基于预设假设
