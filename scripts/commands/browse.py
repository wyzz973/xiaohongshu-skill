"""浏览场景命令：首页 Feed、搜索、笔记详情、用户主页。"""

from __future__ import annotations

import argparse

from common import connect, output


# ---------------------------------------------------------------------------
# 首页 Feed 列表
# ---------------------------------------------------------------------------
def cmd_list_feeds(args: argparse.Namespace) -> None:
    """获取首页 Feed 列表。"""
    from xhs.feeds import list_feeds

    browser, page = connect(args)
    try:
        channel = getattr(args, "channel", "") or ""
        feeds = list_feeds(page, channel=channel)
        output({"channel": channel or "推荐", "feeds": [f.to_dict() for f in feeds], "count": len(feeds)})
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 搜索 Feeds
# ---------------------------------------------------------------------------
def cmd_search_feeds(args: argparse.Namespace) -> None:
    """搜索 Feeds。"""
    from xhs.search import search_feeds
    from xhs.types import FilterOption

    filter_opt = FilterOption(
        sort_by=args.sort_by or "",
        note_type=args.note_type or "",
        publish_time=args.publish_time or "",
        search_scope=args.search_scope or "",
        location=args.location or "",
    )

    browser, page = connect(args)
    try:
        feeds = search_feeds(page, args.keyword, filter_opt)
        output({"feeds": [f.to_dict() for f in feeds], "count": len(feeds)})
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# Feed 详情
# ---------------------------------------------------------------------------
def cmd_get_feed_detail(args: argparse.Namespace) -> None:
    """获取 Feed 详情。"""
    from xhs.feed_detail import get_feed_detail
    from xhs.types import CommentLoadConfig

    config = CommentLoadConfig(
        click_more_replies=args.click_more_replies,
        max_replies_threshold=args.max_replies_threshold,
        max_comment_items=args.max_comment_items,
        scroll_speed=args.scroll_speed,
    )

    browser, page = connect(args)
    try:
        detail = get_feed_detail(
            page,
            args.feed_id,
            args.xsec_token,
            load_all_comments=args.load_all_comments,
            config=config,
            xsec_source=getattr(args, "xsec_source", "pc_feed"),
        )
        output(detail.to_dict())
    finally:
        # 只断开 CDP 连接，保留 tab（避免 Chrome 关闭最后 tab 后
        # 自动新开 explore 页面，同时保留 session tab 供下次复用）
        browser.close()


# ---------------------------------------------------------------------------
# 用户主页
# ---------------------------------------------------------------------------
def cmd_user_profile(args: argparse.Namespace) -> None:
    """获取用户主页。"""
    from xhs.user_profile import get_user_profile

    browser, page = connect(args)
    try:
        profile = get_user_profile(page, args.user_id, args.xsec_token)
        output(profile.to_dict())
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# Argparse 注册
# ---------------------------------------------------------------------------
def register_browse_commands(subparsers) -> None:
    """向 argparse 注册所有浏览场景子命令。"""

    # list-feeds
    sub = subparsers.add_parser("list-feeds", help="获取首页 Feed 列表")
    sub.add_argument(
        "--channel",
        help="板块名称（推荐/穿搭/美食/彩妆/影视/职场/情感/家居/游戏/旅行/健身）",
    )
    sub.set_defaults(func=cmd_list_feeds)

    # search-feeds
    sub = subparsers.add_parser("search-feeds", help="搜索 Feeds")
    sub.add_argument("--keyword", required=True, help="搜索关键词")
    sub.add_argument("--sort-by", help="排序: 综合|最新|最多点赞|最多评论|最多收藏")
    sub.add_argument("--note-type", help="类型: 不限|视频|图文")
    sub.add_argument("--publish-time", help="时间: 不限|一天内|一周内|半年内")
    sub.add_argument("--search-scope", help="范围: 不限|已看过|未看过|已关注")
    sub.add_argument("--location", help="位置: 不限|同城|附近")
    sub.set_defaults(func=cmd_search_feeds)

    # get-feed-detail
    sub = subparsers.add_parser("get-feed-detail", help="获取 Feed 详情")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument(
        "--xsec-source",
        default="pc_feed",
        help="token 来源: pc_feed(推荐页) | pc_search(搜索)",
    )
    sub.add_argument("--load-all-comments", action="store_true", help="加载全部评论")
    sub.add_argument("--click-more-replies", action="store_true", help="点击展开更多回复")
    sub.add_argument("--max-replies-threshold", type=int, default=10, help="展开回复数阈值")
    sub.add_argument("--max-comment-items", type=int, default=0, help="最大评论数 (0=不限)")
    sub.add_argument("--scroll-speed", default="normal", help="滚动速度: slow|normal|fast")
    sub.set_defaults(func=cmd_get_feed_detail)

    # user-profile
    sub = subparsers.add_parser("user-profile", help="获取用户主页")
    sub.add_argument("--user-id", required=True, help="用户 ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.set_defaults(func=cmd_user_profile)
