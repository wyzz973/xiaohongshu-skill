"""统一 CLI 入口，对应 Go MCP 工具的 13 个子命令。

全局选项: --host, --port, --account
输出: JSON（ensure_ascii=False）
退出码: 0=成功, 1=未登录, 2=错误
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# 共享基础设施（已拆分到 common.py）
# ---------------------------------------------------------------------------
from common import (
    VERSION,
    connect,
    connect_existing,
    output,
    logger,
    headless_fallback,
)

# 保留旧名称兼容（测试文件 test_headless_login.py 通过 cli._ 访问）
_connect = connect
_connect_existing = connect_existing
_output = output
_headless_fallback = headless_fallback

# ---------------------------------------------------------------------------
# 命令注册（各场景已拆分到 commands/ 子包）
# ---------------------------------------------------------------------------
from commands.auth import register_auth_commands
from commands.browse import register_browse_commands
from commands.interact import register_interact_commands
from commands.publish import register_publish_commands
from commands.analytics import register_analytics_commands


# ========== 参数解析 ==========


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="xhs-cli",
        description="小红书自动化 CLI",
    )

    # 全局选项
    parser.add_argument("--host", default="127.0.0.1", help="Chrome 调试主机 (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9222, help="Chrome 调试端口 (default: 9222)")
    parser.add_argument("--account", default="", help="账号名称")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # === 各场景命令注册 ===
    register_auth_commands(subparsers)
    register_browse_commands(subparsers)
    register_interact_commands(subparsers)
    register_publish_commands(subparsers)
    register_analytics_commands(subparsers)

    return parser


def _check_dependencies() -> None:
    """检查依赖，缺包时输出 JSON 错误而非 traceback。"""
    deps = {"requests": "requests", "websockets": "websockets"}
    missing = []
    for import_name in deps.values():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(import_name)
    if missing:
        print(json.dumps({
            "success": False,
            "error": "missing_dependencies",
            "packages": missing,
            "fix": "pip install " + " ".join(missing),
            "version": VERSION,
        }, ensure_ascii=False, indent=2))
        sys.exit(2)


def main() -> None:
    """CLI 入口。"""
    _check_dependencies()

    parser = build_parser()
    args = parser.parse_args()

    # Validate strategy.json on startup
    from strategy_validator import validate_strategy
    strategy_path = os.path.join(
        os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
        "strategy.json"
    )
    validate_strategy(strategy_path)

    try:
        args.func(args)
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        _output({"success": False, "error": str(e)}, exit_code=2)


if __name__ == "__main__":
    main()
