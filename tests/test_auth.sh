#!/usr/bin/env bash
# Auth 场景可用性测试
# 前提：Chrome 已启动（openclaw 运行中）
# 用法：bash tests/test_auth.sh

set -euo pipefail

CLI="python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py"
PASS=0
FAIL=0
SKIP=0

run_test() {
    local name="$1"
    local cmd="$2"
    local expect_exit="${3:-0}"

    echo ""
    echo "--- [$name] ---"
    echo "CMD: $cmd"

    set +e
    output=$(eval "$cmd" 2>&1)
    actual_exit=$?
    set -e

    echo "EXIT: $actual_exit (expected: $expect_exit)"
    echo "OUTPUT: $output" | head -20

    # 验证输出是合法 JSON
    if echo "$output" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "JSON: valid"
    else
        echo "JSON: INVALID"
        ((FAIL++))
        return
    fi

    if [ "$actual_exit" -eq "$expect_exit" ]; then
        echo "RESULT: PASS"
        ((PASS++))
    else
        echo "RESULT: FAIL"
        ((FAIL++))
    fi
}

echo "========================================="
echo "  Auth Scene Usability Test"
echo "========================================="

# 1. check-login — 应返回 0（已登录）或 1（未登录+二维码）
run_test "check-login" "$CLI check-login" "0"
# 如果未登录 exit_code=1 也是正常的，手动判断

# 2. list-accounts — 应始终返回 0
run_test "list-accounts" "$CLI list-accounts" "0"

# 3. login --help — 验证 argparse 注册正确
echo ""
echo "--- [login --help] ---"
$CLI login --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 4. get-qrcode --help
echo ""
echo "--- [get-qrcode --help] ---"
$CLI get-qrcode --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 5. wait-login --help
echo ""
echo "--- [wait-login --help] ---"
$CLI wait-login --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 6. send-code --help
echo ""
echo "--- [send-code --help] ---"
$CLI send-code --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 7. verify-code --help
echo ""
echo "--- [verify-code --help] ---"
$CLI verify-code --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 8. phone-login --help
echo ""
echo "--- [phone-login --help] ---"
$CLI phone-login --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 9. delete-cookies --help
echo ""
echo "--- [delete-cookies --help] ---"
$CLI delete-cookies --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

# 10. add-account --help
echo ""
echo "--- [add-account --help] ---"
$CLI add-account --help >/dev/null 2>&1 && echo "RESULT: PASS" && ((PASS++)) || (echo "RESULT: FAIL" && ((FAIL++)))

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed, $SKIP skipped"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
