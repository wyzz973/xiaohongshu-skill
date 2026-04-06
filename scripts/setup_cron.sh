#!/bin/bash
# xhs-autopilot Cron 任务一键注册脚本
# 用法: bash scripts/setup_cron.sh [strategy.json路径]
#
# 从 strategy.json 读取调度配置，注册全套 Cron 任务。
# 也可以直接告诉 OpenClaw："帮我注册小红书自动运营的定时任务"，它会自动执行。

set -e

STRATEGY_FILE="${1:-$HOME/.openclaw/workspace/xhs-autopilot/strategy.json}"

if [ ! -f "$STRATEGY_FILE" ]; then
    echo "❌ 策略文件不存在: $STRATEGY_FILE"
    echo "请先执行 /xhs-autopilot setup 完成初始化"
    exit 1
fi

# 读取时区（默认 Asia/Shanghai）
TZ=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('timezone','Asia/Shanghai'))" 2>/dev/null || echo "Asia/Shanghai")

echo "🕐 时区: $TZ"
echo "📋 开始注册 Cron 任务..."

# 1. 选题研究
TOPIC_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('topic_research_time','07:00'))" 2>/dev/null || echo "07:00")
TOPIC_H=$(echo $TOPIC_TIME | cut -d: -f1)
TOPIC_M=$(echo $TOPIC_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-topic-research" \
    --cron "$TOPIC_M $TOPIC_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "执行小红书选题研究。读取 ~/.openclaw/workspace/xhs-autopilot/strategy.json 的赛道和关键词，用 python scripts/cli.py search-feeds 搜索热点，分析 Top 笔记，生成选题建议保存到 content-calendar/ 目录。"
echo "  ✅ 选题研究: $TOPIC_TIME"

# 2. 内容创作
CREATE_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('content_creation_time','09:00'))" 2>/dev/null || echo "09:00")
CREATE_H=$(echo $CREATE_TIME | cut -d: -f1)
CREATE_M=$(echo $CREATE_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-content-create" \
    --cron "$CREATE_M $CREATE_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "执行小红书内容创作。从 content-calendar/ 取今日选题，按 strategy.json 人设风格和 references/copywriting.md 文案公式生成笔记草稿，保存到 drafts/ 目录。"
echo "  ✅ 内容创作: $CREATE_TIME"

# 3. 发布笔记（可能多个时间点）
PUBLISH_TIMES=$(python3 -c "
import json
d = json.load(open('$STRATEGY_FILE'))
times = d.get('schedule',{}).get('publish_times',['10:00'])
for t in times: print(t)
" 2>/dev/null || echo "10:00")

IDX=1
while IFS= read -r PUB_TIME; do
    PUB_H=$(echo $PUB_TIME | cut -d: -f1)
    PUB_M=$(echo $PUB_TIME | cut -d: -f2)
    openclaw cron add \
        --name "xhs-publish-$IDX" \
        --cron "$PUB_M $PUB_H * * *" \
        --tz "$TZ" \
        --session isolated \
        --message "执行小红书发布任务 #$IDX。检查登录态，从 drafts/ 取待发布笔记，通过 CLI 分步发布（fill → 预览 → confirm）。发布前如需确认则通知用户。发布后记录到 published/ 目录。" \
        --announce
    echo "  ✅ 发布 #$IDX: $PUB_TIME"
    IDX=$((IDX + 1))
done <<< "$PUBLISH_TIMES"

# 4. 互动巡逻
INTERACT_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('interact_time','14:00'))" 2>/dev/null || echo "14:00")
INTERACT_H=$(echo $INTERACT_TIME | cut -d: -f1)
INTERACT_M=$(echo $INTERACT_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-interact-patrol" \
    --cron "$INTERACT_M $INTERACT_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "执行小红书互动巡逻。读取 strategy.json 互动策略，搜索赛道笔记，按帖子内容 + 评论区语境动态生成真人感评论；评论长短要随机，禁止模板化。夜间降低浏览/评论概率，凌晨 2-6 点不刷帖不评论。严格遵守频率限制和安全规则。记录到 logs/ 目录。"
echo "  ✅ 互动巡逻: $INTERACT_TIME"

# 5. 评论回复
REPLY_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('reply_time','20:00'))" 2>/dev/null || echo "20:00")
REPLY_H=$(echo $REPLY_TIME | cut -d: -f1)
REPLY_M=$(echo $REPLY_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-reply-comments" \
    --cron "$REPLY_M $REPLY_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "检查小红书账号最新评论并按 strategy.json 人设风格回复。遵守频率限制。"
echo "  ✅ 评论回复: $REPLY_TIME"

# 6. 数据复盘
REPORT_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('report_time','22:00'))" 2>/dev/null || echo "22:00")
REPORT_H=$(echo $REPORT_TIME | cut -d: -f1)
REPORT_M=$(echo $REPORT_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-daily-report" \
    --cron "$REPORT_M $REPORT_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "生成小红书运营日报。获取已发布笔记数据（点赞/收藏/评论），汇总互动数据，分析内容表现，保存到 analytics/ 目录。" \
    --announce
echo "  ✅ 数据复盘: $REPORT_TIME"

# 7. 登录态巡检
AUTH_TIME=$(python3 -c "import json; d=json.load(open('$STRATEGY_FILE')); print(d.get('schedule',{}).get('auth_check_time','02:00'))" 2>/dev/null || echo "02:00")
AUTH_H=$(echo $AUTH_TIME | cut -d: -f1)
AUTH_M=$(echo $AUTH_TIME | cut -d: -f2)
openclaw cron add \
    --name "xhs-auth-check" \
    --cron "$AUTH_M $AUTH_H * * *" \
    --tz "$TZ" \
    --session isolated \
    --message "检查小红书登录状态。执行 python scripts/cli.py check-login。如果 Cookie 过期通知用户重新登录。如果 Chrome 进程异常尝试重启。"
echo "  ✅ 登录巡检: $AUTH_TIME"

echo ""
echo "🎉 全部 Cron 任务注册完成！"
echo ""
echo "查看任务列表: openclaw cron list"
echo "手动触发测试: openclaw cron run <job-id> --force"
echo "暂停某个任务: openclaw cron disable <job-id>"
