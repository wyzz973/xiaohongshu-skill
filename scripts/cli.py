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
    connect_fresh,
    connect_existing,
    connect_saved_tab,
    output,
    logger,
    normalize_tags,
    save_session_tab,
    load_session_tab,
    clear_session_tab,
    save_login_tab,
    load_login_tab,
    clear_login_tab,
    open_file_if_display,
    resolve_account,
    update_account_nickname,
    headless_fallback,
    qrcode_fallback,
    cleanup_extra_tabs,
)

# 保留旧名称兼容（带下划线前缀），等其他场景迁移时删除
_connect = connect
_connect_fresh = connect_fresh
_connect_existing = connect_existing
_connect_saved_tab = connect_saved_tab
_output = output
_normalize_tags = normalize_tags
_save_session_tab = save_session_tab
_load_session_tab = load_session_tab
_clear_session_tab = clear_session_tab
_save_login_tab = save_login_tab
_load_login_tab = load_login_tab
_clear_login_tab = clear_login_tab
_open_file_if_display = open_file_if_display
_resolve_account = resolve_account
_update_account_nickname = update_account_nickname
_headless_fallback = headless_fallback
_qrcode_fallback = qrcode_fallback
_cleanup_extra_tabs = cleanup_extra_tabs

# ---------------------------------------------------------------------------
# Auth 命令（已拆分到 commands/auth.py）
# ---------------------------------------------------------------------------
from commands.auth import register_auth_commands
from commands.browse import register_browse_commands
from commands.interact import register_interact_commands
from commands.publish import register_publish_commands


# ---------------------------------------------------------------------------
# 创作服务平台数据采集命令
# ---------------------------------------------------------------------------


def cmd_list_my_notes(args: argparse.Namespace) -> None:
    """获取我的全部笔记及深度分析数据。"""
    from xhs.creator import list_my_notes

    browser, page = _connect(args)
    try:
        data = list_my_notes(page)
        _output(data)
    finally:
        browser.close()


def cmd_get_dashboard(args: argparse.Namespace) -> None:
    """获取账号总览仪表盘数据。"""
    from xhs.creator import get_dashboard

    browser, page = _connect(args)
    try:
        data = get_dashboard(page)
        _output(data)
    finally:
        browser.close()


def cmd_get_fans_profile(args: argparse.Namespace) -> None:
    """获取粉丝画像数据。"""
    from xhs.creator import get_fans_profile

    browser, page = _connect(args)
    try:
        data = get_fans_profile(page)
        _output(data)
    finally:
        browser.close()

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

    # === Auth 场景（已拆分到 commands/auth.py）===
    register_auth_commands(subparsers)

    # === Browse 场景（已拆分到 commands/browse.py）===
    register_browse_commands(subparsers)

    # === Interact 场景（已拆分到 commands/interact.py）===
    register_interact_commands(subparsers)

    # === Publish 场景（已拆分到 commands/publish.py）===
    register_publish_commands(subparsers)

    # list-my-notes（获取我的全部笔记及深度分析数据）
    sub = subparsers.add_parser(
        "list-my-notes",
        help="获取我的全部笔记列表及深度分析数据（曝光/CTR/观看时长/涨粉）",
    )
    sub.set_defaults(func=cmd_list_my_notes)

    # get-dashboard（获取账号总览仪表盘）
    sub = subparsers.add_parser(
        "get-dashboard",
        help="获取账号总览（粉丝/曝光/涨粉趋势/账号诊断）",
    )
    sub.set_defaults(func=cmd_get_dashboard)

    # get-fans-profile（获取粉丝画像）
    sub = subparsers.add_parser(
        "get-fans-profile",
        help="获取粉丝画像（性别/年龄/兴趣/地域）",
    )
    sub.set_defaults(func=cmd_get_fans_profile)

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

    try:
        args.func(args)
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        _output({"success": False, "error": str(e)}, exit_code=2)


if __name__ == "__main__":
    main()
