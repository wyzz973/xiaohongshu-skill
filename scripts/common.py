"""共享基础设施：连接管理、输出、Tab 持久化。"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import logging.handlers
import os
import platform
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 修复: 原 cli.py 缺少 requests import 导致 _cleanup_extra_tabs() 崩溃
# ---------------------------------------------------------------------------
import requests

# ---------------------------------------------------------------------------
# 版本号
# ---------------------------------------------------------------------------
_VERSION_FILE = Path(__file__).parent / "VERSION"
VERSION = _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else "unknown"

# ---------------------------------------------------------------------------
# 请求 ID（每次 CLI 调用唯一）
# ---------------------------------------------------------------------------
REQUEST_ID = uuid.uuid4().hex[:8]

# ---------------------------------------------------------------------------
# 编码 & 日志
# ---------------------------------------------------------------------------
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("xhs-cli")

# 文件日志 — 所有 CLI/CDP 操作写入 logs/cli.log，方便外部监控
_CLI_LOG_DIR = os.path.join(
    os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
    "logs",
)
os.makedirs(_CLI_LOG_DIR, exist_ok=True)
_cli_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_CLI_LOG_DIR, "cli.log"),
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,
    encoding="utf-8",
)
_cli_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logging.getLogger().addHandler(_cli_file_handler)  # 根 logger，捕获所有子 logger（xhs.cdp/xhs.comment 等）

# ---------------------------------------------------------------------------
# Audit logger — writes structured JSON to logs/audit.jsonl
# ---------------------------------------------------------------------------
_AUDIT_LOG = os.path.join(
    os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
    "logs", "audit.jsonl",
)


def audit_log(action: str, **kwargs) -> None:
    """Write structured audit entry to logs/audit.jsonl."""
    import json as _json
    entry = {
        "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "req_id": REQUEST_ID,
        "action": action,
        **kwargs,
    }
    try:
        os.makedirs(os.path.dirname(_AUDIT_LOG), exist_ok=True)
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logger.debug("Failed to write audit log entry")


# ---------------------------------------------------------------------------
# Tab 文件管理（每账号端口隔离）
# ---------------------------------------------------------------------------
def _session_tab_file(port: int) -> str:
    return os.path.join(tempfile.gettempdir(), "xhs", f"session_tab_{port}.txt")


def _login_tab_file(port: int) -> str:
    return os.path.join(tempfile.gettempdir(), "xhs", f"login_tab_{port}.txt")


def _atomic_write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(content)
    os.replace(tmp_path, path)


def save_login_tab(target_id: str, port: int) -> None:
    _atomic_write_text(_login_tab_file(port), target_id)


def load_login_tab(port: int) -> str | None:
    with contextlib.suppress(FileNotFoundError):
        data = open(_login_tab_file(port)).read().strip()
        return data or None
    return None


def clear_login_tab(port: int) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.remove(_login_tab_file(port))


def save_session_tab(target_id: str, port: int) -> None:
    _atomic_write_text(_session_tab_file(port), target_id)


def load_session_tab(port: int) -> str | None:
    with contextlib.suppress(FileNotFoundError):
        data = open(_session_tab_file(port)).read().strip()
        return data or None
    return None


def clear_session_tab(port: int) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.remove(_session_tab_file(port))


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def output(data: dict, exit_code: int = 0) -> None:
    """输出 JSON 并退出。"""
    data.setdefault("version", VERSION)
    # Audit log every CLI output
    audit_log("cli_output", exit_code=exit_code, success=exit_code == 0)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# 文件打开 & 账号管理
# ---------------------------------------------------------------------------
def open_file_if_display(path: str) -> None:
    from chrome_launcher import has_display
    if not has_display():
        return
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        logger.debug("无法自动打开文件: %s", path)


def resolve_account(args: argparse.Namespace) -> str | None:
    if not getattr(args, "account", ""):
        return None
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import account_manager
    name = args.account
    args.port = account_manager.get_account_port(name)
    return account_manager.get_profile_dir(name)


def update_account_nickname(args: argparse.Namespace, page) -> None:
    if not getattr(args, "account", ""):
        return
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import account_manager
    from xhs.login import get_current_user_nickname
    try:
        nickname = get_current_user_nickname(page)
        if nickname:
            account_manager.update_account_description(args.account, nickname)
            logger.info("账号 %s 昵称已更新: %s", args.account, nickname)
    except Exception as e:
        logger.warning("更新账号昵称失败: %s", e)


# ---------------------------------------------------------------------------
# Chrome 连接
# ---------------------------------------------------------------------------
def connect(args: argparse.Namespace):
    """连接 Chrome 并返回 (browser, page)。优先复用 session tab。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    user_data_dir = resolve_account(args)
    if not ensure_chrome(port=args.port, headless=not has_display(), user_data_dir=user_data_dir):
        output({"success": False, "error": "无法启动 Chrome，请检查 Chrome 是否已安装"}, exit_code=2)

    browser = Browser(host=args.host, port=args.port)
    browser.connect()

    saved_id = load_session_tab(args.port)
    if saved_id:
        page = browser.get_page_by_target_id(saved_id)
        if page:
            logger.debug("复用会话 tab: %s", saved_id)
            save_session_tab(page.target_id, args.port)
            return browser, page
        logger.warning("会话 tab (target_id=%s) 已失效，重新获取", saved_id)

    page = browser.get_or_create_page()
    save_session_tab(page.target_id, args.port)
    cleanup_extra_tabs(browser, page)
    return browser, page


def connect_fresh(args: argparse.Namespace):
    """强制新开干净 tab。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    user_data_dir = resolve_account(args)
    if not ensure_chrome(port=args.port, headless=not has_display(), user_data_dir=user_data_dir):
        output({"success": False, "error": "无法启动 Chrome，请检查 Chrome 是否已安装"}, exit_code=2)

    browser = Browser(host=args.host, port=args.port)
    browser.connect()
    page = browser.new_page()
    save_session_tab(page.target_id, args.port)
    return browser, page


def connect_saved_tab(args: argparse.Namespace):
    """连接到登录流程中记录的精确 tab。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    user_data_dir = resolve_account(args)
    if not ensure_chrome(port=args.port, headless=not has_display(), user_data_dir=user_data_dir):
        output({"success": False, "error": "无法连接到 Chrome"}, exit_code=2)

    browser = Browser(host=args.host, port=args.port)
    browser.connect()

    target_id = load_login_tab(args.port)
    if target_id:
        page = browser.get_page_by_target_id(target_id)
        if page:
            return browser, page
        logger.warning("保存的 tab (target_id=%s) 已失效，回退到第一个可用 tab", target_id)

    page = browser.get_existing_page()
    if not page:
        output({"success": False, "error": "未找到已打开的登录页面，请重新执行登录前置步骤"}, exit_code=2)
    return browser, page


def connect_existing(args: argparse.Namespace):
    """复用已有页面（用于分步发布后续步骤）。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    user_data_dir = resolve_account(args)
    if not ensure_chrome(port=args.port, headless=not has_display(), user_data_dir=user_data_dir):
        output({"success": False, "error": "无法连接到 Chrome"}, exit_code=2)

    browser = Browser(host=args.host, port=args.port)
    browser.connect()

    saved_id = load_session_tab(args.port)
    if saved_id:
        page = browser.get_page_by_target_id(saved_id)
        if page:
            logger.debug("复用 session tab: %s", saved_id)
            return browser, page
        logger.warning("session tab (target_id=%s) 已失效，回退到 get_existing_page", saved_id)

    page = browser.get_existing_page()
    if not page:
        output({"success": False, "error": "未找到已打开的页面，请先执行前置步骤"}, exit_code=2)
    return browser, page


def cleanup_extra_tabs(browser, keep_page) -> None:
    """关闭除当前 page 之外的多余 tab。"""
    try:
        resp = requests.get(f"{browser.base_url}/json", timeout=3)
        targets = resp.json()
        for t in targets:
            if t.get("type") != "page":
                continue
            if t["id"] == keep_page.target_id:
                continue
            if "creator.xiaohongshu.com" in t.get("url", ""):
                continue
            with contextlib.suppress(Exception):
                requests.get(f"{browser.base_url}/json/close/{t['id']}", timeout=3)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 标签处理（发布场景也会用）
# ---------------------------------------------------------------------------
def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized = [t.strip().lstrip("#") for t in tags if t and t.strip()]
    if len(normalized) > 10:
        logger.warning("标签数量超过10，自动截取前10个: %s", normalized[:10])
    return normalized[:10]


# ---------------------------------------------------------------------------
# Headless 回退 & QR 回退（auth 场景会用）
# ---------------------------------------------------------------------------
def headless_fallback(port: int) -> None:
    from chrome_launcher import has_display, restart_chrome
    if has_display():
        logger.info("Headless 模式未登录，切换到有窗口模式...")
        restart_chrome(port=port, headless=False)
        output(
            {"success": False, "error": "未登录", "action": "switched_to_headed",
             "message": "已切换到有窗口模式，请在浏览器中扫码登录"},
            exit_code=1,
        )
    else:
        output(
            {"success": False, "error": "未登录", "action": "login_required",
             "message": "无界面环境下请先运行 send-code --phone <手机号> 完成登录"},
            exit_code=1,
        )


def qrcode_fallback(browser, page, args: argparse.Namespace) -> None:
    from xhs.login import fetch_qrcode, make_qrcode_url, save_qrcode_to_file
    from xhs.urls import EXPLORE_URL

    page.navigate(EXPLORE_URL)
    page.wait_for_load()

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
        "logged_in": False, "login_method": "qrcode",
        "qrcode_path": qrcode_path, "qrcode_image_url": image_url,
        "message": "验证码发送受限，已切换为二维码登录，请扫码。扫码后运行 wait-login 等待登录结果。",
    }
    if login_url:
        result["qr_login_url"] = login_url
    output(result, exit_code=1)


# ---------------------------------------------------------------------------
# CORE 文件保护检查
# ---------------------------------------------------------------------------
def check_core_protection() -> None:
    """Verify CORE memory files are read-only. Warn if not."""
    import stat
    core_file = os.path.join(
        os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
        "logs", "memory", "identity.md"
    )
    if os.path.exists(core_file):
        mode = os.stat(core_file).st_mode
        if mode & stat.S_IWUSR or mode & stat.S_IWGRP or mode & stat.S_IWOTH:
            logger.warning("CORE file is writable (should be read-only): %s", core_file)
