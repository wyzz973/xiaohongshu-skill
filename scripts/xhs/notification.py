"""通知页面，获取评论回复/赞收藏/新增关注通知。"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from .cdp import Page
from .human import sleep_random

logger = logging.getLogger(__name__)

NOTIFICATION_URL = "https://www.xiaohongshu.com/notification"

# 通知 tab 对应 notificationMap 中的 key
TAB_KEYS = {
    "mentions": "mentions",       # 评论和@
    "likes": "likes",             # 赞和收藏
    "connections": "connections",  # 新增关注
}

# 通知页 DOM 选择器
_CONTAINER = ".tabs-content-container > .container"
_ACTION_REPLY = ".action-reply"
_ACTION_LIKE = ".action-like .like-wrapper"
_LIKE_ACTIVE = ".like-wrapper.like-active"
_COMMENT_INPUT = "textarea.comment-input"
_SUBMIT_BUTTON = "button.submit"


@dataclass
class NotificationUser:
    user_id: str = ""
    nickname: str = ""
    avatar: str = ""
    xsec_token: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> NotificationUser:
        return cls(
            user_id=d.get("userid", ""),
            nickname=d.get("nickname", ""),
            avatar=d.get("image", ""),
            xsec_token=d.get("xsecToken", ""),
        )

    def to_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "nickname": self.nickname,
        }


@dataclass
class NotificationItem:
    """通知条目。"""
    id: str = ""
    type: str = ""                          # comment/comment, like/note 等
    title: str = ""                         # "回复了你的评论"
    time: int = 0                           # unix 时间戳
    user: NotificationUser = field(default_factory=NotificationUser)

    # 帖子信息
    note_id: str = ""
    note_title: str = ""
    note_xsec_token: str = ""

    # 评论信息（仅 mentions 类型）
    comment_id: str = ""                    # 对方的回复评论 ID
    comment_content: str = ""               # 对方的回复内容
    target_comment_id: str = ""             # 我的原评论 ID
    target_comment_content: str = ""        # 我的原评论内容
    comment_liked: bool = False             # 是否已点赞该回复

    # DOM 状态（由 _enrich_dom_state 填充）
    has_reply_button: bool = False          # 是否有回复按钮（已删除的评论没有）
    dom_liked: bool = False                 # DOM 中是否已点赞（比 comment_liked 更准确）

    @classmethod
    def from_dict(cls, d: dict) -> NotificationItem:
        user = NotificationUser.from_dict(d.get("userInfo", {}))

        item_info = d.get("itemInfo", {})
        comment_info = d.get("commentInfo", {})
        target = comment_info.get("targetComment", {})

        return cls(
            id=d.get("id", ""),
            type=d.get("type", ""),
            title=d.get("title", ""),
            time=d.get("time", 0),
            user=user,
            note_id=item_info.get("id", ""),
            note_title=item_info.get("content", ""),
            note_xsec_token=item_info.get("xsecToken", ""),
            comment_id=comment_info.get("id", ""),
            comment_content=comment_info.get("content", ""),
            target_comment_id=target.get("id", ""),
            target_comment_content=target.get("content", ""),
            comment_liked=comment_info.get("liked", False),
        )

    def to_dict(self) -> dict:
        result: dict = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "time": self.time,
            "user": self.user.to_dict(),
            "noteId": self.note_id,
            "noteTitle": self.note_title,
            "noteXsecToken": self.note_xsec_token,
        }
        if self.comment_id:
            result["commentId"] = self.comment_id
            result["commentContent"] = self.comment_content
            result["targetCommentId"] = self.target_comment_id
            result["targetCommentContent"] = self.target_comment_content
            result["commentLiked"] = self.comment_liked
        result["hasReplyButton"] = self.has_reply_button
        result["domLiked"] = self.dom_liked
        return result


def list_notifications(
    page: Page,
    tab: str = "mentions",
) -> list[NotificationItem]:
    """获取通知列表。

    Args:
        page: CDP 页面对象。
        tab: 通知类型，支持 "mentions"（评论和@）、"likes"（赞和收藏）、"connections"（新增关注）。

    Returns:
        通知列表。
    """
    _navigate_to_notification(page)

    # 切换 tab（如需要）
    if tab != "mentions":
        _click_notification_tab(page, tab)

    # 滚动加载更多
    _scroll_to_load_more(page)

    # 从 __INITIAL_STATE__ 提取通知数据
    tab_key = TAB_KEYS.get(tab, "mentions")
    js = f"""(function() {{
        var n = window.__INITIAL_STATE__;
        if (!n || !n.notification || !n.notification.notificationMap) return '';
        var tab = n.notification.notificationMap['{tab_key}'];
        if (!tab || !tab.messageList) return '[]';
        // replacer: 将大数字 ID 转为字符串，防止 JSON.stringify 精度丢失
        return JSON.stringify(tab.messageList, function(key, value) {{
            if (typeof value === 'number' && !Number.isSafeInteger(value)) {{
                return String(value);
            }}
            return value;
        }});
    }})()"""

    result = page.evaluate(js)
    if not result:
        logger.warning("未获取到通知数据 (tab=%s)", tab)
        return []

    items_data = json.loads(result)
    items = [NotificationItem.from_dict(d) for d in items_data]

    # 从 DOM 补充状态（回复按钮、点赞状态）
    if tab == "mentions":
        _enrich_dom_state(page, items)

    logger.info("获取到 %d 条通知 (tab=%s)", len(items), tab)
    return items


def reply_notification(page: Page, index: int, content: str) -> None:
    """在通知页面直接回复指定通知。

    点击通知项的"回复"按钮 → 在内联 textarea 输入 → 点击"发送"。

    Args:
        page: CDP 页面对象。
        index: 通知项索引（0-based，对应 DOM 中的第 index 个 .container）。
        content: 回复内容。

    Raises:
        RuntimeError: 回复失败。
    """
    _ensure_on_notification_page(page)

    count = page.get_elements_count(_CONTAINER)
    if index >= count:
        raise RuntimeError(f"通知索引 {index} 超出范围 (共 {count} 条)")

    # 滚动到目标通知项
    page.scroll_nth_element_into_view(_CONTAINER, index)
    sleep_random(500, 1000)

    # 点击"回复"按钮
    clicked = page.evaluate(f"""(function() {{
        var items = document.querySelectorAll('{_CONTAINER}');
        var item = items[{index}];
        if (!item) return false;
        var btn = item.querySelector('{_ACTION_REPLY}');
        if (!btn) return false;
        btn.click();
        return true;
    }})()""")
    if not clicked:
        raise RuntimeError(f"通知项 {index} 没有回复按钮（可能是已删除的评论）")

    sleep_random(500, 1000)

    # focus textarea 并输入内容
    focused = page.evaluate(f"""(function() {{
        var items = document.querySelectorAll('{_CONTAINER}');
        var item = items[{index}];
        if (!item) return false;
        var textarea = item.querySelector('{_COMMENT_INPUT}');
        if (!textarea) return false;
        textarea.focus();
        return true;
    }})()""")
    if not focused:
        raise RuntimeError("未找到回复输入框")

    sleep_random(300, 600)
    page.type_text(content, delay_ms=50)
    sleep_random(500, 1000)

    # 点击"发送"按钮
    sent = page.evaluate(f"""(function() {{
        var items = document.querySelectorAll('{_CONTAINER}');
        var item = items[{index}];
        if (!item) return false;
        var btn = item.querySelector('{_SUBMIT_BUTTON}');
        if (btn) {{ btn.click(); return true; }}
        return false;
    }})()""")
    if not sent:
        raise RuntimeError("未找到发送按钮")

    sleep_random(800, 1500)
    logger.info("通知回复成功 (index=%d)", index)


def like_notification(page: Page, index: int) -> bool:
    """在通知页面点赞指定通知的评论。

    Args:
        page: CDP 页面对象。
        index: 通知项索引（0-based）。

    Returns:
        True 点赞成功，False 已经点赞过。
    """
    _ensure_on_notification_page(page)

    count = page.get_elements_count(_CONTAINER)
    if index >= count:
        raise RuntimeError(f"通知索引 {index} 超出范围 (共 {count} 条)")

    page.scroll_nth_element_into_view(_CONTAINER, index)
    sleep_random(300, 600)

    # 检查是否已点赞
    already_liked = page.evaluate(f"""(function() {{
        var items = document.querySelectorAll('{_CONTAINER}');
        var item = items[{index}];
        if (!item) return false;
        return !!item.querySelector('{_LIKE_ACTIVE}');
    }})()""")
    if already_liked:
        logger.info("通知项 %d 已点赞，跳过", index)
        return False

    # 点击点赞
    clicked = page.evaluate(f"""(function() {{
        var items = document.querySelectorAll('{_CONTAINER}');
        var item = items[{index}];
        if (!item) return false;
        var btn = item.querySelector('{_ACTION_LIKE}');
        if (!btn) return false;
        btn.click();
        return true;
    }})()""")
    if not clicked:
        logger.warning("通知项 %d 没有点赞按钮", index)
        return False

    sleep_random(500, 1000)
    logger.info("通知点赞成功 (index=%d)", index)
    return True


# ========== 内部辅助 ==========


def _navigate_to_notification(page: Page) -> None:
    """导航到通知页面。"""
    page.navigate(NOTIFICATION_URL)
    page.wait_for_load()
    page.wait_dom_stable()
    time.sleep(2)


def _ensure_on_notification_page(page: Page) -> None:
    """确保当前在通知页面。"""
    current_url = page.evaluate("location.href") or ""
    if "notification" not in current_url:
        _navigate_to_notification(page)


def _click_notification_tab(page: Page, tab: str) -> None:
    """点击通知页面的 tab。"""
    tab_names = {
        "mentions": "评论和@",
        "likes": "赞和收藏",
        "connections": "新增关注",
    }
    tab_text = tab_names.get(tab, tab)

    clicked = page.evaluate(f"""(function() {{
        var tabs = document.querySelectorAll('.reds-tab-item');
        for (var t of tabs) {{
            if (t.textContent.trim() === '{tab_text}') {{
                t.click();
                return true;
            }}
        }}
        return false;
    }})()""")
    if clicked:
        logger.info("切换到通知 tab: %s", tab_text)
        time.sleep(2)
        page.wait_dom_stable()
    else:
        logger.warning("未找到通知 tab: %s", tab_text)


def _scroll_to_load_more(page: Page, max_scrolls: int = 3) -> None:
    """滚动通知页面加载更多数据。"""
    for _ in range(max_scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        sleep_random(800, 1500)


def _enrich_dom_state(page: Page, items: list[NotificationItem]) -> None:
    """批量从 DOM 获取通知项的交互状态。"""
    js = f"""(function() {{
        var containers = document.querySelectorAll('{_CONTAINER}');
        var result = [];
        for (var i = 0; i < containers.length; i++) {{
            var c = containers[i];
            result.push({{
                hasReply: !!c.querySelector('{_ACTION_REPLY}'),
                liked: !!c.querySelector('{_LIKE_ACTIVE}')
            }});
        }}
        return JSON.stringify(result);
    }})()"""

    result = page.evaluate(js)
    if not result:
        return

    dom_states = json.loads(result)
    for i, item in enumerate(items):
        if i < len(dom_states):
            item.has_reply_button = dom_states[i]["hasReply"]
            item.dom_liked = dom_states[i]["liked"]
