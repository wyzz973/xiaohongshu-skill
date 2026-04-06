#!/usr/bin/env bash
# Interact 场景可用性测试
# 前提：Chrome 已启动（openclaw 运行中），账号已登录
# 用法：bash tests/test_interact.sh

CLI="python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py"
PASS=0
FAIL=0

run_test() {
    local name="$1"
    local cmd="$2"
    local expect_exit="${3:-0}"

    echo ""
    echo "--- [$name] ---"
    echo "CMD: $cmd"

    output=$(eval "$cmd" 2>/dev/null) || true
    actual_exit=${PIPESTATUS[0]:-$?}

    echo "EXIT: $actual_exit (expected: $expect_exit)"
    echo "OUTPUT: $output" | head -20

    # 验证输出是合法 JSON
    if echo "$output" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "JSON: valid"
    else
        echo "JSON: INVALID"
        FAIL=$((FAIL + 1))
        return
    fi

    if [ "$actual_exit" -eq "$expect_exit" ]; then
        echo "RESULT: PASS"
        PASS=$((PASS + 1))
    else
        echo "RESULT: FAIL"
        FAIL=$((FAIL + 1))
    fi
}

run_help_test() {
    local name="$1"
    echo ""
    echo "--- [$name --help] ---"
    if $CLI "$name" --help >/dev/null 2>&1; then
        echo "RESULT: PASS"
        PASS=$((PASS + 1))
    else
        echo "RESULT: FAIL"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================="
echo "  Interact Scene Usability Test"
echo "========================================="

# 1. list-notifications — 实际执行，期望返回 0 + 合法 JSON
run_test "list-notifications" "$CLI list-notifications" "0"

# 2-8. --help 验证 argparse 注册正确（破坏性命令只测 help）
run_help_test "check-interacted"
run_help_test "record-interact"
run_help_test "post-comment"
run_help_test "reply-comment"
run_help_test "like-feed"
run_help_test "reply-notification"

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
