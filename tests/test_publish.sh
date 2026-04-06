#!/usr/bin/env bash
# Publish 场景可用性测试
# 所有发布命令均为破坏性操作，只测试 --help（验证 argparse 注册正确）
# 用法：bash tests/test_publish.sh

CLI="python /Users/sd3/xhs-workspace/xiaohongshu-skill/scripts/cli.py"
PASS=0
FAIL=0

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
echo "  Publish Scene Usability Test"
echo "========================================="

# 图文发布
run_help_test "fill-publish"
run_help_test "click-publish"
run_help_test "publish"

# 长文发布
run_help_test "long-article"
run_help_test "select-template"
run_help_test "next-step"

# 文字配图发布
run_help_test "publish-text2image"

# 视频发布
run_help_test "publish-video"

# 草稿
run_help_test "save-draft"

echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
