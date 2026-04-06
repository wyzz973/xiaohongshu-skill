#!/usr/bin/env bash
# Analytics 场景可用性测试
# 前提：Chrome 已启动（openclaw 运行中），账号已登录
# 用法：bash tests/test_analytics.sh

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
echo "  Analytics Scene Usability Test"
echo "========================================="

# 1. list-my-notes — 返回所有笔记深度分析，需已登录
run_test "list-my-notes" "$CLI list-my-notes" "0"

# 2. get-dashboard — 返回账号 7 日总览，需已登录
run_test "get-dashboard" "$CLI get-dashboard" "0"

# 3. get-fans-profile --help — argparse 注册检查（实际执行可能较慢）
run_help_test "get-fans-profile"

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
