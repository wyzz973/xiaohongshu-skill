<p align="center">
  <img src="https://img.shields.io/badge/platform-Claude_Code-blueviolet?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/version-2.0.0-green?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/react-18-blue?style=flat-square" alt="React">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License">
</p>

<h1 align="center">XHS Autopilot</h1>

<p align="center">
  <b>小红书 24/7 自动运营系统</b><br>
  基于 Claude Code Skill + CDP 浏览器自动化 + React Dashboard
</p>

---

## 它能做什么

- **自动发布** 图文 / 长文 / 文字配图 / 视频，支持 Markdown 排版和模板选择
- **智能互动** 浏览推荐页 + 搜索帖子 + 评论 + 点赞 + 收藏 + 回复通知
- **评论去 AI 味** 先读评论区真人语气，再模仿风格写评论（不是模板）
- **自动进化** 每日复盘 + winning/losing patterns + 策略自动调整
- **安全运营** Rate limiting + 互动去重 + 策略校验 fail-closed + Audit log
- **实时监控** React Dashboard 可视化全部操作 + CLI 日志流

## 架构

```
三层结构：

1. 调度层 — Daemon 守护进程（tmux + Claude Code 长驻会话，每 45 分钟一轮）
2. Skill 层 — SKILL.md（主路由）+ skills/*/SKILL.md（子技能 SOP）
3. 引擎层 — scripts/cli.py（43+ 子命令）→ scripts/xhs/（CDP 自动化库）

数据流：
strategy.json → Daemon → content-calendar/ → drafts/ → published/ → analytics/
```

## 项目结构

```
xiaohongshu-skill/
├── SKILL.md                   # 主技能路由（Agent 执行入口）
├── scripts/
│   ├── cli.py                 # 统一 CLI（43+ 子命令）
│   ├── common.py              # 共享基础设施（连接/输出/日志）
│   ├── rate_limiter.py        # 动态限额（从 strategy.json 读取）
│   ├── strategy_validator.py  # 策略校验（fail-closed）
│   ├── publish_checker.py     # 发布质检（标题/内容/敏感词）
│   ├── checkpoint.py          # 发布断点恢复
│   ├── commands/              # 分场景命令
│   │   ├── auth.py            # 认证（12 个命令）
│   │   ├── browse.py          # 浏览（4 个命令）
│   │   ├── interact.py        # 互动（13 个命令，内嵌去重）
│   │   ├── publish.py         # 发布（11 个命令）
│   │   └── analytics.py       # 数据（3 个命令）
│   └── xhs/                   # CDP 自动化引擎
│       ├── cdp.py             # WebSocket CDP 客户端
│       ├── comment.py         # 评论操作
│       ├── feed_detail.py     # 笔记详情 + 评论加载
│       ├── like_favorite.py   # 点赞/收藏
│       ├── notification.py    # 通知处理
│       ├── publish.py         # 图文/视频发布
│       ├── publish_long_article.py  # 长文发布（TipTap/Markdown）
│       └── stealth.py         # 反检测
├── skills/                    # 子技能 SOP
│   ├── xhs-auth/SKILL.md     # 认证协议
│   ├── xhs-explore/SKILL.md  # 浏览 + 竞品对标
│   ├── xhs-interact/SKILL.md # 互动 + 去 AI 味规则
│   ├── xhs-publish/SKILL.md  # 发布 + 笔记类型决策树
│   └── xhs-analytics/SKILL.md # 数据分析 + 自我进化
├── dashboard/                 # 监控面板
│   ├── server.py              # Flask API（20+ 端点）
│   └── frontend/              # React + Tailwind Dashboard
│       ├── src/
│       │   ├── components/    # StatCard, TrendChart, LogViewer, DataTable...
│       │   └── pages/         # Overview, Monitor, Content, Interact, Analytics, Settings
│       └── package.json
├── references/                # 参考资料
└── tests/                     # 测试脚本
```

## 快速开始

### 1. 环境准备

```bash
# Python 依赖
pip install requests websockets flask flask-cors

# 前端依赖
cd dashboard/frontend && npm install

# 设置 workspace 路径
export XHS_WORKSPACE=~/xhs-workspace
```

### 2. 启动 Chrome（带调试端口）

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$XHS_WORKSPACE/chrome-data"
```

### 3. 登录

```bash
python scripts/cli.py check-login    # 检查状态
python scripts/cli.py login          # 二维码登录
```

### 4. 启动 Dashboard

```bash
# 后端 API
cd dashboard && python server.py &

# 前端（开发模式）
cd dashboard/frontend && npm run dev
# 访问 http://localhost:5173
```

### 5. 自动运营（可选）

需要配置 `strategy.json`（运营策略）和 `loop-prompt.txt`（循环指令），然后：

```bash
python daemon.py start    # 启动守护进程
python daemon.py status   # 查看状态
python daemon.py stop     # 停止
```

## CLI 命令速查

| 命令 | 说明 |
|------|------|
| `check-login` | 检查登录状态 |
| `login` | 二维码登录 |
| `list-feeds` | 推荐页 |
| `search-feeds --keyword "AI"` | 搜索 |
| `get-feed-detail --feed-id ID --xsec-token T --load-all-comments` | 笔记详情 + 评论 |
| `post-comment --feed-id ID --xsec-token T --content "内容"` | 发评论（内嵌去重） |
| `like-feed --feed-id ID --xsec-token T` | 点赞（内嵌去重） |
| `list-notifications` | 通知列表 |
| `reply-notification --index N --content "回复"` | 回复通知 |
| `publish --title-file t.txt --content-file c.txt --images pic.jpg` | 图文发布 |
| `long-article --title-file t.txt --content-file c.txt --markdown` | 长文发布 |
| `list-my-notes` | 我的笔记 + 数据分析 |
| `get-dashboard` | 账号仪表盘 |

完整 43+ 命令见 `scripts/cli.py --help`。

## Dashboard 页面

| 页面 | 功能 |
|------|------|
| **运营总览** | 核心指标（粉丝/曝光/互动/CTR）+ 趋势图 + 守护进程状态 + 配额进度 |
| **实时监控** | CDP 日志流（2s 刷新）+ Daemon 面板 + 异常列表 |
| **内容管理** | 选题日历 + 草稿箱 + 已发布表格（可排序） |
| **互动中心** | 通知日志 + 互动日志 + 去重索引（可搜索） |
| **数据分析** | 粉丝画像 + 笔记排行 + 进化知识库（winning/losing patterns） |
| **设置** | 账号管理 + Daemon 启停 + 发布策略编辑 + 安全限额滑块 + 内容策略 |

## 安全机制

| 机制 | 说明 |
|------|------|
| Rate Limiting | 从 strategy.json 动态加载限额，post-success 扣 quota |
| 互动去重 | 内嵌到命令处理器，不依赖 agent 调用 |
| 策略校验 | 安全关键命令 fail-closed（strategy.json 无效则阻止执行） |
| Audit Log | 所有评论/点赞写入 audit.jsonl |
| CLI 文件日志 | 全部 CDP 操作写入 logs/cli.log（5MB 轮转） |
| 发布质检 | 标题长度/内容完整性/敏感词检查 |
| 断点恢复 | 发布流程中断后可从 checkpoint 恢复 |

## 技术栈

| 层 | 技术 |
|---|---|
| 浏览器自动化 | Chrome DevTools Protocol (CDP) via WebSocket |
| CLI | Python 3.11+ / argparse |
| Dashboard 后端 | Flask + flask-cors |
| Dashboard 前端 | React 18 + TypeScript + Tailwind CSS + Recharts + SWR + Zustand |
| Agent 调度 | Claude Code Skill + tmux + Daemon |

## License

MIT
