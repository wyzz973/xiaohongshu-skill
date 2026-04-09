#!/bin/bash
# XHS Night Operations - Cron Phase Runner
# Usage: ./run-phase.sh <task_id>
# Called by crontab to execute a scheduled task

# Set proxy (required for claude CLI to reach API)
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890

# Ensure PATH includes claude CLI and homebrew
export PATH="/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/bin:/opt/homebrew/bin:$PATH"

TASK_ID="${1:?Usage: run-phase.sh <task_id>}"
WORKSPACE="/Users/sd3/xhs-workspace"
TASKS_FILE="$WORKSPACE/dashboard/tasks.json"
LOG_DIR="$WORKSPACE/logs"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)
LOG_FILE="$LOG_DIR/task-${TASK_ID}-${DATE}.log"
MAX_SECONDS=1800

mkdir -p "$LOG_DIR"
echo "[$TIMESTAMP] Starting task: $TASK_ID" >> "$LOG_FILE"

# Extract task prompt from tasks.json
PROMPT=$(python3 -c "
import json, sys
with open('$TASKS_FILE') as f:
    tasks = json.load(f)
for t in tasks['tasks']:
    if t['id'] == '$TASK_ID':
        if not t.get('enabled', True):
            print('DISABLED', file=sys.stderr)
            sys.exit(1)
        print(t['prompt'])
        sys.exit(0)
print('NOT_FOUND', file=sys.stderr)
sys.exit(1)
" 2>/dev/null)

if [ -z "$PROMPT" ]; then
    echo "[$TIMESTAMP] Task $TASK_ID is disabled or not found, skipping" >> "$LOG_FILE"
    exit 0
fi

# Update task status to running (with file lock to prevent corruption)
python3 -c "
import json, os, fcntl
lock_file = open('${TASKS_FILE}.lock', 'w')
fcntl.flock(lock_file, fcntl.LOCK_EX)
try:
    with open('$TASKS_FILE') as f:
        data = json.load(f)
    for t in data['tasks']:
        if t['id'] == '$TASK_ID':
            t['status'] = 'running'
            t['last_run'] = '$TIMESTAMP'
            t['pid'] = os.getpid()
            break
    with open('$TASKS_FILE', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
finally:
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()
"

# Build full prompt with system context prefix
CONTEXT_PREFIX="[系统上下文 - 请在执行任务前先读取以下文件获取完整运营上下文]

必读文件（按顺序）：
1. 运营规范 SOP：读取 ~/xhs-workspace/xiaohongshu-skill/SKILL.md
2. 账号策略（人设/赛道/风格/禁用词/安全设置）：读取 ~/xhs-workspace/strategy.json
3. 历史互动记录（去重用）：读取 ~/xhs-workspace/logs/interacted-index.json
4. 通知水位线：读取 ~/xhs-workspace/logs/notification-watermark.json
5. 最近发布记录：ls ~/xhs-workspace/published/

CLI 工具统一入口：cd ~/xhs-workspace/xiaohongshu-skill && python scripts/cli.py <子命令>
所有操作必须通过此 CLI 执行，不得使用其他工具。

---
以下是本次任务：

"
FULL_PROMPT="${CONTEXT_PREFIX}${PROMPT}"

# Write prompt to file, then pipe to claude (avoids all shell quoting issues)
PROMPT_FILE="/tmp/xhs-prompt-${TASK_ID}.md"
printf '%s' "$FULL_PROMPT" > "$PROMPT_FILE"

START_SEC=$(date +%s)

cat "$PROMPT_FILE" | claude -p \
    --dangerously-skip-permissions \
    --output-format text \
    -d "$WORKSPACE" \
    >> "$LOG_FILE" 2>&1 &
CLAUDE_PID=$!

# Watchdog: kill after MAX_SECONDS
(
    sleep $MAX_SECONDS
    if kill -0 $CLAUDE_PID 2>/dev/null; then
        echo "[$(date +%Y-%m-%dT%H:%M:%S)] Timeout after ${MAX_SECONDS}s, killing" >> "$LOG_FILE"
        kill -TERM $CLAUDE_PID 2>/dev/null
        sleep 5
        kill -9 $CLAUDE_PID 2>/dev/null
    fi
) &
WATCHDOG_PID=$!

# Wait for claude to finish
wait $CLAUDE_PID 2>/dev/null
EXIT_CODE=$?

# Cleanup watchdog (ignore errors)
kill $WATCHDOG_PID 2>/dev/null || true
wait $WATCHDOG_PID 2>/dev/null || true

END_SEC=$(date +%s)
DURATION=$((END_SEC - START_SEC))
END_TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)

# Determine result
if [ $EXIT_CODE -eq 0 ]; then
    RESULT="completed"
    RESULT_MSG="成功完成，耗时 ${DURATION}s"
elif [ $DURATION -ge $MAX_SECONDS ]; then
    RESULT="failed"
    RESULT_MSG="超时终止（${MAX_SECONDS}s 限制）"
else
    RESULT="completed"
    RESULT_MSG="完成，耗时 ${DURATION}s (exit=$EXIT_CODE)"
fi

echo "[$END_TIMESTAMP] Task $TASK_ID finished: $RESULT_MSG" >> "$LOG_FILE"

# Update task status (with file lock)
python3 -c "
import json, fcntl
lock_file = open('${TASKS_FILE}.lock', 'w')
fcntl.flock(lock_file, fcntl.LOCK_EX)
try:
    with open('$TASKS_FILE') as f:
        data = json.load(f)
    for t in data['tasks']:
        if t['id'] == '$TASK_ID':
            t['status'] = '$RESULT'
            t['last_duration'] = $DURATION
            t['last_result'] = '$RESULT_MSG'
            t['pid'] = None
            break
    with open('$TASKS_FILE', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
finally:
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()
"

echo "[$END_TIMESTAMP] Status updated: $RESULT" >> "$LOG_FILE"
exit 0
