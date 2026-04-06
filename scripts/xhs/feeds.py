"""首页 Feed 列表，对应 Go xiaohongshu/feeds.go。"""

from __future__ import annotations

import json
import logging
import time

from .cdp import Page
from .errors import NoFeedsError
from .types import Feed
from .urls import EXPLORE_URL

logger = logging.getLogger(__name__)

# 从 __INITIAL_STATE__ 提取 feeds 的 JS
_EXTRACT_FEEDS_JS = """
(() => {
    if (window.__INITIAL_STATE__ &&
        window.__INITIAL_STATE__.feed &&
        window.__INITIAL_STATE__.feed.feeds) {
        const feeds = window.__INITIAL_STATE__.feed.feeds;
        const feedsData = feeds.value !== undefined ? feeds.value : feeds._value;
        if (feedsData) {
            return JSON.stringify(feedsData);
        }
    }
    return "";
})()
"""

# 可用板块（与小红书首页 tab 一一对应）
CHANNELS = [
    "推荐", "穿搭", "美食", "彩妆", "影视",
    "职场", "情感", "家居", "游戏", "旅行", "健身",
]


def list_feeds(page: Page, channel: str = "") -> list[Feed]:
    """获取首页 Feed 列表。

    Args:
        page: CDP 页面对象。
        channel: 板块名称（如 "美食"、"旅行"），空字符串或"推荐"表示默认推荐页。

    Raises:
        NoFeedsError: 没有捕获到 feeds 数据。
    """
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    page.wait_dom_stable()
    time.sleep(1)

    # 切换板块（非推荐）
    if channel and channel != "推荐":
        _click_channel_tab(page, channel)

    result = page.evaluate(_EXTRACT_FEEDS_JS)
    if not result:
        raise NoFeedsError()

    feeds_data = json.loads(result)
    logger.info("获取到 %d 条 Feed（板块: %s）", len(feeds_data), channel or "推荐")
    return [Feed.from_dict(f) for f in feeds_data]


def list_channels(page: Page) -> list[str]:
    """获取首页可用板块列表。"""
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    page.wait_dom_stable()
    time.sleep(1)

    result = page.evaluate(
        """
        (() => {
            const container = document.querySelector('.channel-container');
            if (!container) return '[]';
            const divs = container.querySelectorAll('div.channel');
            const names = ['推荐'];
            for (const d of divs) {
                const text = d.textContent.trim();
                if (text && text.length < 10) names.push(text);
            }
            return JSON.stringify(names);
        })()
        """
    )
    return json.loads(result) if result else CHANNELS


def _click_channel_tab(page: Page, channel: str) -> None:
    """点击指定板块 tab。"""
    clicked = page.evaluate(
        f"""
        (() => {{
            const container = document.querySelector('.channel-container');
            if (!container) return false;
            const divs = container.querySelectorAll('div.channel');
            for (const d of divs) {{
                if (d.textContent.trim() === {json.dumps(channel)}) {{
                    d.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        logger.warning("未找到板块 tab: %s，使用默认推荐页", channel)
        return

    logger.info("已切换到板块: %s", channel)
    time.sleep(3)
    page.wait_dom_stable()
