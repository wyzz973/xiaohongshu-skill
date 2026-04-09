#!/usr/bin/env bash
# Auth 场景可用性测试
# 前提：Chrome 已启动（openclaw 运行中）
# 用法：bash tests/test_auth.sh

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
echo "  Auth Scene Usability Test"
echo "========================================="

# 1. check-login — 应返回 0（已登录）或 1（未登录+二维码）
run_test "check-login" "$CLI check-login" "0"

# 2. list-accounts — 应始终返回 0
run_test "list-accounts" "$CLI list-accounts" "0"

# 3-10. --help 验证 argparse 注册正确
run_help_test "login"
run_help_test "get-qrcode"
run_help_test "wait-login"
run_help_test "send-code"
run_help_test "verify-code"
run_help_test "phone-login"
run_help_test "delete-cookies"
run_help_test "add-account"

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
