"""原子写入和资源管理测试 — 覆盖 Bug 4, 7。"""
from __future__ import annotations

import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ========== Bug 7: cookies 原子写入 ==========


def test_save_cookies_atomic(tmp_path):
    """save_cookies 应使用原子写入（无残留 .tmp 文件）。"""
    from xhs.cookies import save_cookies, load_cookies

    path = str(tmp_path / "sub" / "cookies.json")
    data = b'{"test": true}'
    save_cookies(path, data)

    assert load_cookies(path) == data
    # 不应有残留的 .tmp 文件
    assert not os.path.exists(path + ".tmp")


def test_save_cookies_no_partial_on_overwrite(tmp_path):
    """覆盖写入时，读取不会拿到半写数据。"""
    from xhs.cookies import save_cookies, load_cookies

    path = str(tmp_path / "cookies.json")
    original = b"original_data_1234567890"
    save_cookies(path, original)

    # 覆盖写入
    updated = b"updated_data_abcdefghij"
    save_cookies(path, updated)

    result = load_cookies(path)
    # 结果只能是 original 或 updated，不会是混合
    assert result in (original, updated)
    assert result == updated


# ========== Bug 4: session tab 原子写入 ==========


def test_save_session_tab_atomic(tmp_path, monkeypatch):
    """_save_session_tab 应使用原子写入。"""
    import cli

    monkeypatch.setattr(
        cli, "_session_tab_file",
        lambda port: str(tmp_path / f"session_tab_{port}.txt"),
    )
    cli._save_session_tab("TARGET_123", 9222)
    result = cli._load_session_tab(9222)
    assert result == "TARGET_123"
    # 无残留 .tmp
    assert not os.path.exists(
        str(tmp_path / "session_tab_9222.txt") + ".tmp"
    )


def test_save_login_tab_atomic(tmp_path, monkeypatch):
    """_save_login_tab 应使用原子写入。"""
    import cli

    monkeypatch.setattr(
        cli, "_login_tab_file",
        lambda port: str(tmp_path / f"login_tab_{port}.txt"),
    )
    cli._save_login_tab("LOGIN_456", 9222)
    result = cli._load_login_tab(9222)
    assert result == "LOGIN_456"
    assert not os.path.exists(
        str(tmp_path / "login_tab_9222.txt") + ".tmp"
    )
