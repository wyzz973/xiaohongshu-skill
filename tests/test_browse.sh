#!/usr/bin/env bash
# Browse 场景可用性测试
# 前提：Chrome 已启动（openclaw 运行中），且已登录小红书
# 用法：bash tests/test_browse.sh

CLI="python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py"
PASS=0
FAIL=0

run_test() {
    local name="$1"
    local cmd="$2"
    local expect_exit="${3:-0}"
    local required_field="${4:-}"

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

    # 验证必需字段（可选）
    if [ -n "$required_field" ]; then
        if echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$required_field' in d" 2>/dev/null; then
            echo "FIELD '$required_field': present"
        else
            echo "FIELD '$required_field': MISSING"
            FAIL=$((FAIL + 1))
            return
        fi
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
echo "  Browse Scene Usability Test"
echo "========================================="

# 1. list-feeds — 应返回 0，包含 feeds 字段
run_test "list-feeds" "$CLI list-feeds" "0" "feeds"

# 2. search-feeds — 搜索 AI工具，应返回 0，包含合法 JSON
run_test "search-feeds --keyword AI工具" "$CLI search-feeds --keyword 'AI工具'" "0"

# 3. get-feed-detail --help — argparse 注册校验
run_help_test "get-feed-detail"

# 4. user-profile --help — argparse 注册校验
run_help_test "user-profile"

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
