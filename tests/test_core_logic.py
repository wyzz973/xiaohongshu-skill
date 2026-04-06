"""核心逻辑 bug 修复测试 — 覆盖 Bug 2, 3, 5, 6, 9。"""
from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "scripts")
)


# ========== Mock Page ==========


class MockPage:
    """最小化的 Page mock，支持 evaluate / navigate / click。"""

    def __init__(self):
        self._eval_returns: list = []
        self._eval_idx = 0
        self._url = "about:blank"
        self._clicks: list[str] = []

    def set_eval_sequence(self, returns: list):
        self._eval_returns = returns
        self._eval_idx = 0

    def evaluate(self, expr: str, **kw) -> object:
        if "location.href" in expr:
            return self._url
        if self._eval_idx < len(self._eval_returns):
            val = self._eval_returns[self._eval_idx]
            self._eval_idx += 1
            return val
        return ""

    def navigate(self, url: str):
        self._url = url

    def wait_for_load(self, **kw):
        pass

    def wait_dom_stable(self, **kw):
        pass

    def click_element(self, selector: str):
        self._clicks.append(selector)

    def _send_session(self, method, params=None):
        pass


# ========== Bug 3: DOM hash 稳定检测 ==========


def test_wait_dom_stable_uses_hash(monkeypatch):
    """wait_dom_stable 应基于 hash+length 判断，非仅 length。"""
    from xhs.cdp import Page

    # 只要 JS 表达式包含 "charCodeAt"（hash 计算），就说明用了 hash
    # 这是个结构性测试
    import inspect
    source = inspect.getsource(Page.wait_dom_stable)
    assert "charCodeAt" in source or "hash" in source.lower(), (
        "wait_dom_stable 应使用 DOM hash 而非仅长度比较"
    )


# ========== Bug 2: xsec_token 过期重定向检测 ==========


def test_extract_feed_detail_detects_redirect():
    """页面被重定向时应抛出 NoFeedDetailError。"""
    from xhs.errors import NoFeedDetailError
    from xhs.feed_detail import _extract_feed_detail

    page = MockPage()
    page._url = "https://www.xiaohongshu.com/explore"  # 被重定向

    with pytest.raises(NoFeedDetailError):
        _extract_feed_detail(page, "69abc123")


def test_extract_feed_detail_success():
    """正常页面应成功提取。"""
    import json
    from xhs.feed_detail import _extract_feed_detail

    feed_id = "69abc123"
    page = MockPage()
    page._url = f"https://www.xiaohongshu.com/explore/{feed_id}"

    mock_data = {
        feed_id: {
            "note": {
                "noteId": feed_id,
                "title": "测试标题",
                "desc": "测试内容",
                "type": "normal",
                "user": {"userId": "u1", "nickname": "test"},
                "interactInfo": {
                    "liked": False,
                    "likedCount": "10",
                    "collectedCount": "5",
                    "collected": False,
                    "commentCount": "2",
                },
                "imageList": [],
            },
            "comments": {"comments": []},
        }
    }
    page.set_eval_sequence([json.dumps(mock_data)])

    result = _extract_feed_detail(page, feed_id)
    assert result.note.title == "测试标题"


def test_get_feed_detail_url_check_after_accessible(monkeypatch):
    """get_feed_detail 在 _check_page_accessible 后应验证 URL。"""
    from xhs.errors import NoFeedDetailError
    from xhs import feed_detail

    page = MockPage()
    feed_id = "69abc123"

    # 模拟: 导航后页面被重定向到 explore
    def fake_navigate(url):
        page._url = "https://www.xiaohongshu.com/explore"

    page.navigate = fake_navigate

    # mock _check_page_accessible 不抛异常
    monkeypatch.setattr(
        feed_detail, "_check_page_accessible", lambda p, u="": None
    )
    monkeypatch.setattr(feed_detail, "sleep_random", lambda *a: None)

    with pytest.raises(NoFeedDetailError):
        feed_detail.get_feed_detail(
            page, feed_id, "fake_token", xsec_source="pc_search"
        )


# ========== Bug 9: 评论加载全局超时 ==========


def test_load_all_comments_has_global_timeout():
    """_load_all_comments 应有全局超时机制。"""
    import inspect
    from xhs.feed_detail import _load_all_comments

    source = inspect.getsource(_load_all_comments)
    assert "monotonic" in source or "GLOBAL_TIMEOUT" in source, (
        "_load_all_comments 应有全局超时保护"
    )


# ========== Bug 6: 点赞重试逻辑 ==========


def test_toggle_like_retry_rechecks_state(monkeypatch):
    """重试前应重新获取状态，避免误撤销。"""
    from xhs import like_favorite
    from xhs.errors import NoFeedDetailError

    page = MockPage()
    feed_id = "69abc123"
    call_count = {"get_state": 0}

    def mock_get_state(p, fid):
        call_count["get_state"] += 1
        if call_count["get_state"] <= 1:
            return (False, False)  # 第一次: 未点赞
        if call_count["get_state"] == 2:
            raise NoFeedDetailError()  # 验证失败
        return (True, False)  # 重试后: 已点赞

    monkeypatch.setattr(
        like_favorite, "_get_interact_state", mock_get_state
    )

    result = like_favorite._toggle_like(page, feed_id, target_liked=True)
    # 应该至少调用 3 次 get_state (初始+验证失败+重试验证)
    assert call_count["get_state"] >= 3


def test_toggle_like_returns_false_on_failure(monkeypatch):
    """重试后仍失败应返回 success=False。"""
    from xhs import like_favorite
    from xhs.errors import NoFeedDetailError

    page = MockPage()

    def always_false(p, fid):
        return (False, False)

    monkeypatch.setattr(
        like_favorite, "_get_interact_state", always_false
    )

    result = like_favorite._toggle_like(
        page, "feed123", target_liked=True
    )
    assert result.success is False


# ========== Bug 5: 异常处理收窄 ==========


def test_feed_detail_navigate_only_catches_expected():
    """导航重试应只捕获网络相关异常。"""
    import inspect
    from xhs.feed_detail import get_feed_detail

    source = inspect.getsource(get_feed_detail)
    # 不应该有裸的 "except Exception"
    assert "except Exception as e:" not in source or (
        "CDPError" in source or "ConnectionError" in source
    ), "导航重试应仅捕获 CDPError/ConnectionError"
