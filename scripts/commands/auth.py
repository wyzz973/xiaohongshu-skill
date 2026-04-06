"""认证场景命令：登录、登出、账号管理。"""

from __future__ import annotations

import argparse
import json
import os
import sys

from common import (
    connect,
    connect_saved_tab,
    clear_login_tab,
    clear_session_tab,
    logger,
    open_file_if_display,
    output,
    qrcode_fallback,
    save_login_tab,
    save_session_tab,
    update_account_nickname,
)


# ---------------------------------------------------------------------------
# 登录状态检查
# ---------------------------------------------------------------------------
def cmd_check_login(args: argparse.Namespace) -> None:
    """检查登录状态。未登录时自动获取二维码。"""
    from xhs.login import fetch_qrcode, make_qrcode_url, save_qrcode_to_file

    browser, page = connect(args)
    try:
        png_bytes, _b64_orig, already = fetch_qrcode(page)
        if already:
            output({"logged_in": True}, exit_code=0)
            return

        qrcode_path = save_qrcode_to_file(png_bytes)
        image_url, login_url = make_qrcode_url(png_bytes)

        save_login_tab(page.target_id, args.port)
        clear_session_tab(args.port)
        open_file_if_display(qrcode_path)

        from chrome_launcher import has_display
        result: dict = {
            "logged_in": False,
            "qrcode_path": qrcode_path,
            "qrcode_image_url": image_url,
        }
        if login_url:
            result["qr_login_url"] = login_url
        if has_display():
            result["login_method"] = "qrcode"
            result["hint"] = "未登录，二维码已自动生成。扫码后运行 wait-login 等待登录结果"
        else:
            result["login_method"] = "both"
            result["hint"] = (
                "未登录，二维码已自动生成。"
                "方式A: 直接扫码 + wait-login；"
                "方式B: send-code --phone <手机号> + verify-code（手机验证码）"
            )
        output(result, exit_code=1)
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 二维码登录（阻塞）
# ---------------------------------------------------------------------------
def cmd_login(args: argparse.Namespace) -> None:
    """获取登录二维码并阻塞等待扫码（最多 120 秒）。"""
    from xhs.login import fetch_qrcode, save_qrcode_to_file, wait_for_login

    browser, page = connect(args)
    try:
        png_bytes, _b64, already = fetch_qrcode(page)
        if already:
            output({"logged_in": True, "message": "已登录"})
            return

        qrcode_path = save_qrcode_to_file(png_bytes)
        open_file_if_display(qrcode_path)
        print(json.dumps({"qrcode_path": qrcode_path, "message": "请扫码登录"}, ensure_ascii=False))
        success = wait_for_login(page, timeout=120)
        if success:
            update_account_nickname(args, page)
        output(
            {"logged_in": success, "message": "登录成功" if success else "登录超时"},
            exit_code=0 if success else 2,
        )
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 二维码登录（非阻塞）
# ---------------------------------------------------------------------------
def cmd_get_qrcode(args: argparse.Namespace) -> None:
    """获取二维码并立即返回。"""
    from xhs.login import fetch_qrcode, make_qrcode_url, save_qrcode_to_file

    browser, page = connect(args)
    png_bytes, _b64_orig, already = fetch_qrcode(page)
    if already:
        browser.close()
        output({"logged_in": True, "message": "已登录"})
        return

    qrcode_path = save_qrcode_to_file(png_bytes)
    image_url, login_url = make_qrcode_url(png_bytes)
    open_file_if_display(qrcode_path)

    save_login_tab(page.target_id, args.port)
    clear_session_tab(args.port)
    browser.close()

    result: dict = {
        "qrcode_path": qrcode_path,
        "qrcode_image_url": image_url,
        "message": "二维码已生成，请扫码登录。扫码后运行 wait-login 等待登录结果。",
    }
    if login_url:
        result["qr_login_url"] = login_url
    output(result)


# ---------------------------------------------------------------------------
# 等待扫码完成
# ---------------------------------------------------------------------------
def cmd_wait_login(args: argparse.Namespace) -> None:
    """等待扫码登录完成（配合 get-qrcode 使用）。"""
    from xhs.login import wait_for_login

    browser, page = connect_saved_tab(args)
    try:
        success = wait_for_login(page, timeout=args.timeout)
        if success:
            clear_login_tab(args.port)
            update_account_nickname(args, page)
        output(
            {"logged_in": success,
             "message": "登录成功" if success else "等待超时，请重新运行 get-qrcode 获取新二维码"},
            exit_code=0 if success else 2,
        )
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 手机号登录（单命令交互式）
# ---------------------------------------------------------------------------
def cmd_phone_login(args: argparse.Namespace) -> None:
    """手机号+验证码登录。"""
    from xhs.errors import RateLimitError
    from xhs.login import send_phone_code, submit_phone_code

    browser, page = connect(args)
    try:
        sent = send_phone_code(page, args.phone)
    except RateLimitError:
        logger.info("验证码发送受限，切换为二维码登录")
        qrcode_fallback(browser, page, args)
        return

    try:
        if not sent:
            output({"logged_in": True, "message": "已登录，无需重新登录"})
            return

        print(json.dumps({
            "status": "code_sent",
            "message": f"验证码已发送至 {args.phone[:3]}****{args.phone[-4:]}",
        }, ensure_ascii=False), flush=True)

        if args.code:
            code = args.code.strip()
        else:
            try:
                code = input("请输入验证码: ").strip()
            except EOFError:
                output({"success": False, "error": "未收到验证码输入"}, exit_code=2)
                return

        if not code:
            output({"success": False, "error": "验证码不能为空"}, exit_code=2)
            return

        success = submit_phone_code(page, code)
        output(
            {"logged_in": success, "message": "登录成功" if success else "验证码错误或超时"},
            exit_code=0 if success else 2,
        )
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 分步手机登录
# ---------------------------------------------------------------------------
def cmd_send_code(args: argparse.Namespace) -> None:
    """分步登录第一步：发送验证码。"""
    from xhs.errors import RateLimitError
    from xhs.login import send_phone_code

    browser, page = connect(args)
    try:
        sent = send_phone_code(page, args.phone)
        if not sent:
            output({"logged_in": True, "message": "已登录，无需重新登录"})
            return

        save_login_tab(page.target_id, args.port)
        clear_session_tab(args.port)
        output({
            "status": "code_sent",
            "message": f"验证码已发送至 {args.phone[:3]}****{args.phone[-4:]}，请运行 verify-code --code <验证码>",
        })
    except RateLimitError:
        logger.info("验证码发送受限，切换为二维码登录")
        qrcode_fallback(browser, page, args)
    else:
        browser.close()


def cmd_verify_code(args: argparse.Namespace) -> None:
    """分步登录第二步：填写验证码。"""
    from xhs.login import submit_phone_code

    browser, page = connect_saved_tab(args)
    try:
        success = submit_phone_code(page, args.code)
        if success:
            clear_login_tab(args.port)
            update_account_nickname(args, page)
        output(
            {"logged_in": success, "message": "登录成功" if success else "验证码错误或超时"},
            exit_code=0 if success else 2,
        )
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 登出
# ---------------------------------------------------------------------------
def cmd_delete_cookies(args: argparse.Namespace) -> None:
    """退出登录并删除 cookies。"""
    from xhs.cookies import delete_cookies, get_cookies_file_path
    from xhs.login import logout

    browser, page = connect(args)
    try:
        logged_out = logout(page)
    finally:
        browser.close()

    path = get_cookies_file_path(args.account)
    delete_cookies(path)
    clear_session_tab(args.port)
    msg = "已退出登录并删除 cookies" if logged_out else "未登录，已删除 cookies 文件"
    output({"success": True, "message": msg, "cookies_path": path})


# ---------------------------------------------------------------------------
# 账号管理
# ---------------------------------------------------------------------------
def _import_account_manager():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
    import account_manager
    return account_manager


def cmd_add_account(args: argparse.Namespace) -> None:
    am = _import_account_manager()
    am.add_account(args.name, description=args.description or "")
    port = am.get_account_port(args.name)
    profile = am.get_profile_dir(args.name)
    output({"success": True, "name": args.name, "port": port, "profile_dir": profile})


def cmd_list_accounts(args: argparse.Namespace) -> None:
    am = _import_account_manager()
    accounts = am.list_accounts()
    output({"accounts": accounts, "count": len(accounts)})


def cmd_remove_account(args: argparse.Namespace) -> None:
    am = _import_account_manager()
    am.remove_account(args.name)
    output({"success": True, "name": args.name})


def cmd_set_default_account(args: argparse.Namespace) -> None:
    am = _import_account_manager()
    am.set_default_account(args.name)
    output({"success": True, "default": args.name})


# ---------------------------------------------------------------------------
# Argparse 注册
# ---------------------------------------------------------------------------
def register_auth_commands(subparsers) -> None:
    """向 argparse 注册所有认证场景子命令。"""

    sub = subparsers.add_parser("check-login", help="检查登录状态")
    sub.set_defaults(func=cmd_check_login)

    sub = subparsers.add_parser("login", help="登录（扫码，阻塞等待）")
    sub.set_defaults(func=cmd_login)

    sub = subparsers.add_parser("get-qrcode", help="获取登录二维码截图并立即返回")
    sub.set_defaults(func=cmd_get_qrcode)

    sub = subparsers.add_parser("wait-login", help="等待扫码登录完成")
    sub.add_argument("--timeout", type=float, default=120.0, help="等待超时秒数 (default: 120)")
    sub.set_defaults(func=cmd_wait_login)

    sub = subparsers.add_parser("phone-login", help="手机号+验证码登录（交互式）")
    sub.add_argument("--phone", required=True, help="手机号")
    sub.add_argument("--code", default="", help="短信验证码（省略则交互式输入）")
    sub.set_defaults(func=cmd_phone_login)

    sub = subparsers.add_parser("send-code", help="分步登录：发送验证码")
    sub.add_argument("--phone", required=True, help="手机号")
    sub.set_defaults(func=cmd_send_code)

    sub = subparsers.add_parser("verify-code", help="分步登录：填写验证码")
    sub.add_argument("--code", required=True, help="短信验证码")
    sub.set_defaults(func=cmd_verify_code)

    sub = subparsers.add_parser("delete-cookies", help="退出登录并删除 cookies")
    sub.set_defaults(func=cmd_delete_cookies)

    sub = subparsers.add_parser("add-account", help="添加命名账号")
    sub.add_argument("--name", required=True, help="账号名称")
    sub.add_argument("--description", default="", help="账号描述")
    sub.set_defaults(func=cmd_add_account)

    sub = subparsers.add_parser("list-accounts", help="列出所有命名账号")
    sub.set_defaults(func=cmd_list_accounts)

    sub = subparsers.add_parser("remove-account", help="删除命名账号")
    sub.add_argument("--name", required=True, help="账号名称")
    sub.set_defaults(func=cmd_remove_account)

    sub = subparsers.add_parser("set-default-account", help="设置默认账号")
    sub.add_argument("--name", required=True, help="账号名称")
    sub.set_defaults(func=cmd_set_default_account)
