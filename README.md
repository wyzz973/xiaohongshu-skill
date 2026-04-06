<p align="center">
  <img src="https://img.shields.io/badge/platform-OpenClaw-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/version-2.0.0-green?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License">
</p>

<h1 align="center">📕 XHS Autopilot</h1>

<p align="center">
  <strong>小红书 24/7 全自动运营系统</strong><br>
  选题 · 创作 · 发布 · 互动 · 复盘 — 一次配置，全链路自动驾驶
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-功能特性">功能特性</a> ·
  <a href="#%EF%B8%8F-架构设计">架构设计</a> ·
  <a href="#-命令参考">命令参考</a> ·
  <a href="CHANGELOG.md">更新日志</a>
</p>

---

## Why XHS Autopilot?

手动运营小红书是重复且低效的。每天需要研究选题、写文案、排版发布、评论互动、追踪数据——这些都是可以自动化的机械劳动。

**XHS Autopilot 让你把时间花在策略上，把执行交给 AI。**

- **不是简单的定时发帖**，而是完整的运营闭环
- **不是固定模板评论**，而是基于帖子内容动态生成的真人化互动
- **不是黑盒操作**，每一步都可审计、可干预、可定制

---

## ✨ 功能特性

### 全链路自动化

| 时段 | 任务 | 描述 |
|------|------|------|
| 07:00 | 选题研究 | 搜索赛道热点，自动生成 3-5 个选题 |
| 09:00 | 内容创作 | 结合人设风格，AI 生成标题+正文+标签 |
| 10:00 | 发布笔记 | 图文/视频/长文/文字配图，多格式支持 |
| 14:00 | 互动巡逻 | 推荐流+搜索+板块多源刷帖，智能评论引流 |
| 20:00 | 通知互动 | 批量处理回复通知，AI 决策是否回复 |
| 22:00 | 数据复盘 | 自动采集互动数据，生成日报 |
| 02:00 | 登录巡检 | 会话保活，异常自动通知 |

### 智能互动引擎

- **动态评论生成** — 阅读帖子内容 + 评论区语境，生成个性化评论
- **真人化行为** — 随机间隔、随机长度、随机语气、小红书表情
- **重复检测** — 自动识别已评论过的帖子，避免重复
- **风控熔断** — 验证码 / 频率限制触发时自动停止并通知

### 跨模型稳定性

专为多 LLM 环境设计，无论 Claude、GPT-4o 还是 Gemini 都能稳定执行：

- **Preflight Checklist** — 关键操作前强制自检，防止跳步
- **命令卡片格式** — 必填参数、参数来源、常见错误一目了然
- **反面示例约束** — 明确标注 ❌ 禁止的评论模式，防止 AI 味输出

### 发布能力

| 格式 | 命令 | 特色 |
|------|------|------|
| 图文 | `fill-publish` | 支持 URL 图片自动下载 |
| 视频 | `fill-publish-video` | 自动等待转码（最长 10 分钟） |
| 文字配图 | `fill-text2image` | 纯文本自动生成配图 |
| 长文 | `long-article` | 一键排版 + 模板选择 |

所有格式均支持：标签候选池（自动随机 3-6 个）、定时发布、地点、合集、原创声明、可见性控制。

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    用户（一次性配置）                       │
│                    strategy.json                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  OpenClaw Cron 调度                       │
│                                                          │
│   07:00 选题  09:00 创作  10:00 发布  14:00 互动          │
│   20:00 通知  22:00 复盘  02:00 巡检                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              SKILL.md (路由 + SOP)                        │
│         ┌──────┬──────┬──────┬──────┐                    │
│         │ auth │publish│explore│interact│                 │
│         └──┬───┴──┬───┴──┬───┴──┬───┘                    │
└────────────┼──────┼──────┼──────┼───────────────────────┘
             │      │      │      │
┌────────────▼──────▼──────▼──────▼───────────────────────┐
│           scripts/cli.py (40+ 子命令)                     │
│                       ↓                                   │
│              scripts/xhs/ (CDP 引擎)                      │
│                       ↓                                   │
│          Chrome (--remote-debugging-port=9222)             │
│                       ↓                                   │
│                    小红书                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- Chrome 浏览器
- [OpenClaw](https://openclaw.com) 平台

### 安装

```bash
# 克隆到 OpenClaw skills 目录
git clone https://github.com/wyzz973/xiaohongshu-skill.git \
  ~/.openclaw/workspace/skills/xhs-autopilot

cd ~/.openclaw/workspace/skills/xhs-autopilot

# 安装依赖
uv sync
```

### 初始化

```bash
# 1. 部署工作区模板
bash scripts/setup_workspace.sh

# 2. 启动 Chrome
python scripts/chrome_launcher.py

# 3. 对 OpenClaw 说：
#    "帮我设置小红书自动运营"
#    → 系统会引导你完成 strategy.json 配置

# 4. 注册定时任务
bash scripts/setup_cron.sh

# 5. 验证
openclaw cron list
```

### 手动测试

```bash
# 检查登录
python scripts/cli.py check-login

# 浏览推荐流
python scripts/cli.py list-feeds

# 搜索笔记
python scripts/cli.py search-feeds --keyword "美食探店" --sort-by "最多点赞"
```

---

## 📖 命令参考

### 认证

```bash
check-login                              # 检查登录状态
login                                     # 二维码登录
delete-cookies                            # 清除 cookies
```

### 搜索发现

```bash
list-feeds [--channel "美食"]              # 首页推荐 / 板块浏览
search-feeds --keyword "关键词"            # 搜索笔记
get-feed-detail --feed-id ID --xsec-token TOKEN  # 笔记详情
user-profile --user-id UID --xsec-token TOKEN    # 用户主页
```

### 社交互动

```bash
post-comment --feed-id ID --xsec-token TOKEN --content "..."   # 发评论
reply-comment --feed-id ID --xsec-token TOKEN --comment-id CID --content "..."  # 回复
like-feed --feed-id ID --xsec-token TOKEN          # 点赞
favorite-feed --feed-id ID --xsec-token TOKEN      # 收藏
list-notifications [--tab mentions|likes|connections]  # 通知列表
reply-notification --index N --content "..."        # 回复通知
like-notification --index N                         # 点赞通知
```

### 发布

```bash
fill-publish --title-file F --content-file F --images I [--tags T...]   # 图文（分步）
fill-publish-video --title-file F --content-file F --video V            # 视频（分步）
fill-text2image --content-file F [--tags T...]                          # 文字配图
long-article --title-file F --content-file F                            # 长文
click-publish                                                           # 确认发布
save-draft                                                              # 保存草稿
```

> 所有命令输出 JSON 格式，附带 `version` 字段。退出码：`0` 成功 · `1` 未登录 · `2` 错误

---

## 📂 项目结构

```
xhs-autopilot/
├── SKILL.md                     # 主入口：路由 + 24/7 SOP
├── CHANGELOG.md                 # 更新日志
├── pyproject.toml               # Python 依赖
├── scripts/
│   ├── cli.py                   # 统一 CLI（40+ 子命令）
│   ├── VERSION                  # 版本号
│   ├── chrome_launcher.py       # Chrome 进程管理
│   ├── publish_pipeline.py      # 发布编排器
│   └── xhs/                    # CDP 自动化引擎
├── skills/                      # 子技能 SOP
│   ├── xhs-auth/               # 认证
│   ├── xhs-publish/            # 发布
│   ├── xhs-explore/            # 搜索发现
│   ├── xhs-interact/           # 社交互动
│   └── xhs-content-ops/        # 复合运营
├── references/
│   ├── copywriting.md           # 文案公式 · 去 AI 味指南
│   ├── strategy-schema.md       # strategy.json 字段说明
│   └── troubleshooting.md       # 问题排查
├── workspace-templates/         # Agent 工作区模板
└── assets/
    └── strategy-template.json   # 策略配置模板
```

---

## 🔐 安全与限制

| 操作 | 每会话 | 每日上限 | 最小间隔 |
|------|--------|---------|---------|
| 评论 | 8-10 条 | 20-25 条 | 2-5 分钟 |
| 点赞 | 15-20 次 | 40-50 次 | 30s-2min |
| 发布 | 2-3 篇 | 3-5 篇 | 30 分钟 |

- 风控信号（验证码/频率限制）自动熔断
- 夜间 02:00-06:00 自动休眠
- 支持发布前人工确认模式
- **强烈建议用小号测试**

---

## 🔄 更新

```bash
cd ~/.openclaw/workspace/skills/xhs-autopilot
git pull
uv sync  # 如有新依赖
```

CLI 内置依赖检查——缺包时输出结构化错误而非 traceback：

```json
{
  "success": false,
  "error": "missing_dependencies",
  "packages": ["websockets"],
  "fix": "pip install websockets"
}
```

查看 [CHANGELOG.md](CHANGELOG.md) 了解每个版本的变更。

---

## 🗣️ 运行时指令

直接对 OpenClaw 说：

| 指令 | 效果 |
|------|------|
| "看看今天的选题" | 展示 content-calendar/ |
| "修改发布时间到晚上8点" | 更新 Cron |
| "暂停自动互动" | 禁用 Cron 任务 |
| "看这周数据" | 聚合 analytics/ 生成周报 |
| "换赛道做美食" | 更新 strategy.json |
| "手动发一篇" | 进入创作 → 发布流程 |
| "查看状态" | `openclaw cron list` |

---

## Credits

CDP 引擎基于 [autoclaw-cc/xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills) (MIT License)。

## License

[MIT](LICENSE)
