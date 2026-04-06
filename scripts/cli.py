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


def _load_text2image_inputs(args: argparse.Namespace) -> tuple[str, str]:
    """读取文字配图所需标题和正文；标题缺失时回退到正文首行。"""
    title = ""
    if getattr(args, "title_file", None):
        with open(args.title_file, encoding="utf-8") as f:
            title = f.read().strip()

    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    if not title:
        for line in content.splitlines():
            line = line.strip()
            if line:
                title = line[:20]
                logger.warning("文字配图未提供标题文件，自动使用正文首行作为标题: %s", title)
                break

    return title, content


# ========== 子命令实现 ==========


def cmd_list_feeds(args: argparse.Namespace) -> None:
    """获取首页 Feed 列表。"""
    from xhs.feeds import list_feeds

    browser, page = _connect(args)
    try:
        channel = getattr(args, "channel", "") or ""
        feeds = list_feeds(page, channel=channel)
        _output({"channel": channel or "推荐", "feeds": [f.to_dict() for f in feeds], "count": len(feeds)})
    finally:
        browser.close()


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

    browser, page = _connect(args)
    try:
        feeds = search_feeds(page, args.keyword, filter_opt)
        _output({"feeds": [f.to_dict() for f in feeds], "count": len(feeds)})
    finally:
        browser.close()


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

    browser, page = _connect(args)
    try:
        detail = get_feed_detail(
            page,
            args.feed_id,
            args.xsec_token,
            load_all_comments=args.load_all_comments,
            config=config,
            xsec_source=getattr(args, "xsec_source", "pc_feed"),
        )
        _output(detail.to_dict())
    finally:
        # 只断开 CDP 连接，保留 tab（避免 Chrome 关闭最后 tab 后
        # 自动新开 explore 页面，同时保留 session tab 供下次复用）
        browser.close()


def cmd_user_profile(args: argparse.Namespace) -> None:
    """获取用户主页。"""
    from xhs.user_profile import get_user_profile

    browser, page = _connect(args)
    try:
        profile = get_user_profile(page, args.user_id, args.xsec_token)
        _output(profile.to_dict())
    finally:
        browser.close()


def cmd_post_comment(args: argparse.Namespace) -> None:
    """发表评论。"""
    from xhs.comment import post_comment
    from xhs.errors import DuplicateCommentError

    browser, page = _connect(args)
    try:
        post_comment(
            page, args.feed_id, args.xsec_token, args.content,
            xsec_source=getattr(args, "xsec_source", "pc_feed"),
        )
        _output({"success": True, "message": "评论发送成功"})
    except DuplicateCommentError as e:
        _output({"success": False, "message": str(e), "duplicate": True})
    finally:
        browser.close()


def cmd_reply_comment(args: argparse.Namespace) -> None:
    """回复评论。"""
    from xhs.comment import reply_comment

    browser, page = _connect(args)
    try:
        reply_comment(
            page,
            args.feed_id,
            args.xsec_token,
            args.content,
            comment_id=args.comment_id or "",
            user_id=args.user_id or "",
            xsec_source=getattr(args, "xsec_source", "pc_feed"),
        )
        _output({"success": True, "message": "回复成功"})
    finally:
        browser.close()


def cmd_like_feed(args: argparse.Namespace) -> None:
    """点赞/取消点赞。"""
    from xhs.like_favorite import like_feed, unlike_feed

    browser, page = _connect(args)
    try:
        xsec_source = getattr(args, "xsec_source", "pc_feed")
        if args.unlike:
            result = unlike_feed(page, args.feed_id, args.xsec_token, xsec_source)
        else:
            result = like_feed(page, args.feed_id, args.xsec_token, xsec_source)
        _output(result.to_dict())
    finally:
        browser.close()


def cmd_favorite_feed(args: argparse.Namespace) -> None:
    """收藏/取消收藏。"""
    from xhs.like_favorite import favorite_feed, unfavorite_feed

    browser, page = _connect(args)
    try:
        xsec_source = getattr(args, "xsec_source", "pc_feed")
        if args.unfavorite:
            result = unfavorite_feed(page, args.feed_id, args.xsec_token, xsec_source)
        else:
            result = favorite_feed(page, args.feed_id, args.xsec_token, xsec_source)
        _output(result.to_dict())
    finally:
        browser.close()


def cmd_list_notifications(args: argparse.Namespace) -> None:
    """获取通知列表。"""
    from xhs.notification import list_notifications

    browser, page = _connect(args)
    try:
        tab = getattr(args, "tab", "mentions")
        items = list_notifications(page, tab=tab)
        _output({
            "tab": tab,
            "count": len(items),
            "items": [item.to_dict() for item in items],
        })
    finally:
        browser.close()


def cmd_reply_notification(args: argparse.Namespace) -> None:
    """在通知页面直接回复评论。"""
    from xhs.notification import list_notifications, reply_notification

    browser, page = _connect(args)
    try:
        # 先获取通知列表（同时导航到通知页面）
        items = list_notifications(page, tab="mentions")

        index = args.index
        if index >= len(items):
            _output({"success": False, "message": f"通知索引 {index} 超出范围 (共 {len(items)} 条)"})
            return

        item = items[index]

        # 在通知页面直接回复
        reply_notification(page, index, args.content)

        # 自动写入通知日志（使 check-interacted --notification-ids 能查到）
        _append_notification_log(item.id)

        _output({
            "success": True,
            "message": "回复成功",
            "replyTo": item.user.nickname,
            "noteId": item.note_id,
            "notificationId": item.id,
            "userId": item.user.user_id,
        })
    finally:
        browser.close()


def cmd_like_notification(args: argparse.Namespace) -> None:
    """在通知页面点赞评论。"""
    from xhs.notification import like_notification, list_notifications

    browser, page = _connect(args)
    try:
        items = list_notifications(page, tab="mentions")

        index = args.index
        if index >= len(items):
            _output({"success": False, "message": f"通知索引 {index} 超出范围 (共 {len(items)} 条)"})
            return

        item = items[index]
        liked = like_notification(page, index)

        # 记录到通知日志（防止重复处理）
        if liked:
            _append_notification_log(item.id)

        _output({
            "success": True,
            "liked": liked,
            "message": "点赞成功" if liked else "已点赞过，跳过",
            "replyFrom": item.user.nickname,
        })
    finally:
        browser.close()


def cmd_publish(args: argparse.Namespace) -> None:
    """发布图文内容。"""
    from image_downloader import process_images
    from xhs.login import check_login_status
    from xhs.publish import publish_image_content
    from xhs.types import PublishImageContent

    # 读取标题和正文
    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    # 处理图片
    image_paths = process_images(args.images) if args.images else []
    if not image_paths:
        _output({"success": False, "error": "没有有效的图片"}, exit_code=2)

    browser, page = _connect(args)
    try:
        # headless 模式登录检查 + 自动降级
        headless = getattr(args, "headless", False)
        if headless and not check_login_status(page):
            browser.close()
            _headless_fallback(args.port)
            return

        publish_image_content(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                image_paths=image_paths,
                schedule_time=args.schedule_at,
                is_original=args.original,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output({"success": True, "title": title, "images": len(image_paths), "status": "发布完成"})
    finally:
        browser.close()


def cmd_fill_publish(args: argparse.Namespace) -> None:
    """只填写图文表单，不发布。"""
    from image_downloader import process_images
    from xhs.publish import fill_publish_form
    from xhs.types import PublishImageContent

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    image_paths = process_images(args.images) if args.images else []
    if not image_paths:
        _output({"success": False, "error": "没有有效的图片"}, exit_code=2)

    browser, page = _connect(args)
    try:
        fill_publish_form(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                image_paths=image_paths,
                schedule_time=args.schedule_at,
                is_original=args.original,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output(
            {
                "success": True,
                "title": title,
                "images": len(image_paths),
                "status": "表单已填写，等待确认发布",
            }
        )
    finally:
        # 不关闭页面，让用户在浏览器中预览
        browser.close()


def cmd_fill_publish_video(args: argparse.Namespace) -> None:
    """只填写视频表单，不发布。"""
    from xhs.publish_video import fill_publish_video_form
    from xhs.types import PublishVideoContent

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    browser, page = _connect(args)
    try:
        fill_publish_video_form(
            page,
            PublishVideoContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                video_path=args.video,
                schedule_time=args.schedule_at,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output(
            {
                "success": True,
                "title": title,
                "video": args.video,
                "status": "视频表单已填写，等待确认发布",
            }
        )
    finally:
        # 不关闭页面，让用户在浏览器中预览
        browser.close()


def cmd_click_publish(args: argparse.Namespace) -> None:
    """点击发布按钮（在用户确认后调用）。复用已有的发布页 tab。"""
    from xhs.publish import click_publish_button

    browser, page = _connect_existing(args)
    try:
        click_publish_button(page, tags=_normalize_tags(args.tags))
        _output({"success": True, "status": "发布完成"})
    finally:
        browser.close()


def cmd_save_draft(args: argparse.Namespace) -> None:
    """保存为草稿（取消发布时调用）。"""
    from xhs.publish import save_as_draft

    browser, page = _connect_existing(args)
    try:
        save_as_draft(page)
        _output({"success": True, "status": "内容已保存到草稿箱"})
    finally:
        browser.close()


def cmd_long_article(args: argparse.Namespace) -> None:
    """长文模式：填写内容 + 一键排版，返回模板列表。"""
    from xhs.publish_long_article import publish_long_article

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    markdown = getattr(args, "markdown", False)

    browser, page = _connect(args)
    try:
        template_names = publish_long_article(
            page,
            title=title,
            content=content,
            markdown=markdown,
            image_paths=args.images,
        )
        # XHS 创作者平台可能在新 tab 中打开长文编辑器，
        # 原 tab 被跳回 explore。扫描所有 tab 找到实际的编辑器 tab。
        import requests as _req
        actual_id = page.target_id
        try:
            resp = _req.get(
                f"http://{args.host}:{args.port}/json", timeout=3
            )
            for t in resp.json():
                if t.get("type") != "page":
                    continue
                url = t.get("url", "")
                logger.debug("扫描 tab: %s | %s", t["id"][:16], url[:60])
                if "publish" in url and "creator" in url:
                    actual_id = t["id"]
                    logger.info("找到编辑器 tab: %s", actual_id[:16])
                    break
        except Exception as e:
            logger.warning("扫描 tab 失败: %s", e)
        _save_session_tab(actual_id, args.port)
        logger.info("session tab 已保存: %s", actual_id[:16])
        _output(
            {
                "success": True,
                "templates": template_names,
                "status": "长文已填写，请选择模板",
            }
        )
    finally:
        # 不关闭页面，后续 select-template / next-step 需要复用
        browser.close()


def cmd_select_template(args: argparse.Namespace) -> None:
    """选择排版模板。复用已有的长文编辑页 tab。

    如果传了 --markdown-file，选模板后自动将 Markdown 内容注入为格式化 HTML。
    """
    from xhs.publish_long_article import select_template, upgrade_content_format

    browser, page = _connect_existing(args)
    try:
        selected = select_template(page, args.name)
        if not selected:
            _output(
                {"success": False, "error": f"未找到模板: {args.name}"},
                exit_code=2,
            )
            return

        # 如果传了 markdown 文件，选模板后注入格式化内容
        upgraded = False
        md_file = getattr(args, "markdown_file", None)
        if md_file:
            with open(md_file, encoding="utf-8") as f:
                md_content = f.read().strip()
            upgraded = upgrade_content_format(page, md_content)

        _output({
            "success": True,
            "template": args.name,
            "upgraded": upgraded,
            "status": "模板已选择" + ("，内容已格式化" if upgraded else ""),
        })
    finally:
        browser.close()


def cmd_next_step(args: argparse.Namespace) -> None:
    """点击下一步 + 填写发布页描述。复用已有的长文编辑页 tab。"""
    from xhs.publish_long_article import click_next_and_fill_description

    with open(args.content_file, encoding="utf-8") as f:
        description = f.read().strip()

    browser, page = _connect_existing(args)
    try:
        click_next_and_fill_description(page, description, tags=_normalize_tags(args.tags))
        _output({"success": True, "status": "已进入发布页，等待确认发布"})
    finally:
        # 不关闭页面，等待 click-publish
        browser.close()


def cmd_fill_text2image(args: argparse.Namespace) -> None:
    """只填写图文-文字配图表单，不发布。"""
    from xhs.publish import fill_text2image_form
    from xhs.types import PublishImageContent

    title, content = _load_text2image_inputs(args)

    browser, page = _connect_fresh(args)
    try:
        fill_text2image_form(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                image_paths=[],
                schedule_time=args.schedule_at,
                is_original=args.original,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output({"success": True, "status": "文字配图已生成，等待确认发布"})
    finally:
        browser.close()


def cmd_publish_text2image(args: argparse.Namespace) -> None:
    """发布图文-文字配图内容。"""
    from xhs.publish import publish_text2image_content
    from xhs.types import PublishImageContent

    title, content = _load_text2image_inputs(args)

    browser, page = _connect_fresh(args)
    try:
        publish_text2image_content(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                image_paths=[],
                schedule_time=args.schedule_at,
                is_original=args.original,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output({"success": True, "status": "文字配图发布完成"})
    finally:
        browser.close()


def cmd_publish_video(args: argparse.Namespace) -> None:
    """发布视频内容。"""
    from xhs.login import check_login_status
    from xhs.publish_video import publish_video_content
    from xhs.types import PublishVideoContent

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    browser, page = _connect(args)
    try:
        # headless 模式登录检查 + 自动降级
        headless = getattr(args, "headless", False)
        if headless and not check_login_status(page):
            browser.close()
            _headless_fallback(args.port)
            return

        publish_video_content(
            page,
            PublishVideoContent(
                title=title,
                content=content,
                tags=_normalize_tags(args.tags),
                video_path=args.video,
                schedule_time=args.schedule_at,
                visibility=args.visibility or "",
                location=args.location or "",
                content_type=getattr(args, "content_type", "") or "",
                allow_duet=not getattr(args, "no_duet", False),
                allow_copy=not getattr(args, "no_copy", False),
                collection=args.collection or "",
            ),
        )
        _output({"success": True, "title": title, "video": args.video, "status": "发布完成"})
    finally:
        browser.close()



# ---------------------------------------------------------------------------
# check-interacted / record-interact — 去重索引管理（纯本地，不连 Chrome）
# ---------------------------------------------------------------------------

def _get_workspace_dir() -> str:
    """获取 workspace 根目录。优先使用 XHS_WORKSPACE 环境变量，否则回退到 openclaw 路径。"""
    return os.environ.get(
        "XHS_WORKSPACE",
        os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "xhs-autopilot"),
    )


_DEFAULT_INDEX_PATH = os.path.join(_get_workspace_dir(), "logs", "interacted-index.json")

_DEFAULT_LOG_DIR = os.path.join(_get_workspace_dir(), "logs")


def _append_notification_log(notification_id: str) -> None:
    """将已回复的通知 ID 追加到当天的通知日志文件。

    日志文件格式: notification-YYYY-MM-DD.json
    内容: {"replied_ids": ["id1", "id2", ...]}
    """
    from datetime import datetime, timedelta, timezone

    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz).date().isoformat()
    log_file = os.path.join(_DEFAULT_LOG_DIR, f"notification-{today}.json")

    os.makedirs(_DEFAULT_LOG_DIR, exist_ok=True)

    data: dict = {"replied_ids": []}
    try:
        with open(log_file, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    replied_ids = data.get("replied_ids", [])
    if notification_id and notification_id not in replied_ids:
        replied_ids.append(notification_id)
        data["replied_ids"] = replied_ids
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _load_index(path: str) -> dict:
    """加载去重索引，不存在则返回空结构。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("feeds", {}) if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_index(feeds: dict, path: str) -> None:
    """写回去重索引。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "_description": "已互动帖子索引，防止重复评论/互动。巡逻前必读此文件，互动后必更新。",
        "feeds": feeds,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_check_interacted(args: argparse.Namespace) -> None:
    """批量查询 feed_id / notification_id 是否已互动过。

    输入：--feed-ids id1 id2 ...  和/或  --notification-ids id1 id2 ...
    输出 JSON：
    {
      "success": true,
      "results": {
        "id1": {"interacted": true,  "types": ["comment"], "first_interact": "2026-03-12", "author": "xxx"},
        "id2": {"interacted": false}
      },
      "summary": {"total": 2, "already_interacted": 1, "new": 1}
    }
    """
    from datetime import datetime, timedelta, timezone

    index_path = args.index_file or _DEFAULT_INDEX_PATH
    feeds_index = _load_index(index_path)

    query_ids = list(args.feed_ids or []) + list(args.notification_ids or [])
    if not query_ids:
        _output({"success": False, "error": "至少提供 --feed-ids 或 --notification-ids"}, exit_code=2)

    # 也检查最近 N 天的 notification 日志
    notif_replied: set[str] = set()
    if args.notification_ids:
        log_dir = os.path.join(os.path.dirname(index_path))
        tz = timezone(timedelta(hours=8))
        today = datetime.now(tz).date()
        for delta in range(args.lookback_days):
            day = today - timedelta(days=delta)
            notif_file = os.path.join(log_dir, f"notification-{day.isoformat()}.json")
            try:
                with open(notif_file, encoding="utf-8") as f:
                    notif_data = json.load(f)
                if isinstance(notif_data, list):
                    for entry in notif_data:
                        if isinstance(entry, dict):
                            nid = entry.get("id") or entry.get("notification_id", "")
                            if nid:
                                notif_replied.add(str(nid))
                elif isinstance(notif_data, dict):
                    for nid in notif_data.get("replied_ids", []):
                        notif_replied.add(str(nid))
            except (FileNotFoundError, json.JSONDecodeError):
                continue

    # 同作者去重检查
    author_recent: dict[str, str] = {}  # author -> most recent date
    if args.check_author_days > 0:
        cutoff = (datetime.now(timezone(timedelta(hours=8))).date()
                  - timedelta(days=args.check_author_days))
        for fid, info in feeds_index.items():
            if isinstance(info, dict):
                author = info.get("author", "")
                first = info.get("first_interact", "")
                if author and first >= cutoff.isoformat():
                    if author not in author_recent or first > author_recent[author]:
                        author_recent[author] = first

    results = {}
    already = 0
    for qid in query_ids:
        if qid in feeds_index:
            info = feeds_index[qid]
            results[qid] = {
                "interacted": True,
                "types": info.get("types", []) if isinstance(info, dict) else [],
                "first_interact": info.get("first_interact", "") if isinstance(info, dict) else "",
                "author": info.get("author", "") if isinstance(info, dict) else "",
            }
            already += 1
        elif qid in notif_replied:
            results[qid] = {"interacted": True, "source": "notification_log"}
            already += 1
        else:
            results[qid] = {"interacted": False}

    # 附加同作者警告（模型可传 --authors '{"feed_id":"author_name",...}'）
    author_warnings = {}
    if args.authors:
        try:
            author_map = json.loads(args.authors)
        except json.JSONDecodeError:
            author_map = {}
        for fid, author in author_map.items():
            if author and author in author_recent and fid not in feeds_index:
                author_warnings[fid] = {
                    "author": author,
                    "last_interact": author_recent[author],
                    "warning": f"同作者 {args.check_author_days} 天内已互动",
                }

    total = len(query_ids)
    out: dict = {
        "success": True,
        "results": results,
        "summary": {
            "total": total,
            "already_interacted": already,
            "new": total - already,
        },
    }
    if author_warnings:
        out["author_warnings"] = author_warnings

    _output(out)


def cmd_record_interact(args: argparse.Namespace) -> None:
    """记录新的互动到索引。

    输入：--feed-id ID --type comment|like|favorite [--author 作者昵称]
    """
    from datetime import datetime, timedelta, timezone

    index_path = args.index_file or _DEFAULT_INDEX_PATH
    feeds_index = _load_index(index_path)

    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz).date().isoformat()

    fid = args.feed_id
    interact_type = args.type
    author = args.author or ""

    if fid in feeds_index and isinstance(feeds_index[fid], dict):
        entry = feeds_index[fid]
        if interact_type not in entry.get("types", []):
            entry.setdefault("types", []).append(interact_type)
        if author and not entry.get("author"):
            entry["author"] = author
    else:
        feeds_index[fid] = {
            "first_interact": today,
            "types": [interact_type],
            "author": author,
        }

    _save_index(feeds_index, index_path)

    _output({
        "success": True,
        "feed_id": fid,
        "recorded": feeds_index[fid],
        "total_indexed": len(feeds_index),
    })


# ---------------------------------------------------------------------------
# check-reply-limit / record-reply — 同帖同用户回复次数限制
# ---------------------------------------------------------------------------

_DEFAULT_REPLY_TRACKER_PATH = os.path.join(_get_workspace_dir(), "logs", "reply-tracker.json")


def _load_reply_tracker(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_reply_tracker(tracker: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def cmd_check_reply_limit(args: argparse.Namespace) -> None:
    """检查同帖同用户的回复次数是否已达上限。

    支持批量查询：--pairs '[{"feed_id":"x","user_id":"y"}, ...]'
    或单条查询：--feed-id x --user-id y
    """
    tracker_path = args.tracker_file or _DEFAULT_REPLY_TRACKER_PATH
    tracker = _load_reply_tracker(tracker_path)
    max_replies = args.max_replies

    pairs = []
    if args.pairs:
        try:
            pairs = json.loads(args.pairs)
        except json.JSONDecodeError:
            _output({"success": False, "error": "--pairs JSON 解析失败"}, exit_code=2)
    elif args.feed_id and args.user_id:
        pairs = [{"feed_id": args.feed_id, "user_id": args.user_id}]
    else:
        _output({"success": False, "error": "需要 --pairs 或 --feed-id + --user-id"}, exit_code=2)

    results = {}
    blocked = 0
    for p in pairs:
        fid = p.get("feed_id", "")
        uid = p.get("user_id", "") or p.get("nickname", "")
        key = f"{fid}:{uid}"
        entry = tracker.get(key, {})
        count = entry.get("count", 0) if isinstance(entry, dict) else 0
        can_reply = count < max_replies
        results[key] = {
            "feed_id": fid,
            "user_id": uid,
            "replied_count": count,
            "max_replies": max_replies,
            "can_reply": can_reply,
        }
        if not can_reply:
            blocked += 1

    _output({
        "success": True,
        "results": results,
        "summary": {
            "total": len(pairs),
            "can_reply": len(pairs) - blocked,
            "blocked": blocked,
        },
    })


def cmd_record_reply(args: argparse.Namespace) -> None:
    """记录一次回复，更新同帖同用户计数。

    输入：--feed-id X --user-id Y [--notification-id Z]
    """
    from datetime import datetime, timedelta, timezone

    tracker_path = args.tracker_file or _DEFAULT_REPLY_TRACKER_PATH
    tracker = _load_reply_tracker(tracker_path)

    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).isoformat()

    fid = args.feed_id
    uid = args.user_id
    key = f"{fid}:{uid}"

    if key in tracker and isinstance(tracker[key], dict):
        tracker[key]["count"] = tracker[key].get("count", 0) + 1
        tracker[key]["last_reply"] = now
        if args.notification_id:
            tracker[key].setdefault("notification_ids", []).append(args.notification_id)
    else:
        tracker[key] = {
            "feed_id": fid,
            "user_id": uid,
            "count": 1,
            "first_reply": now,
            "last_reply": now,
            "notification_ids": [args.notification_id] if args.notification_id else [],
        }

    _save_reply_tracker(tracker, tracker_path)

    _output({
        "success": True,
        "key": key,
        "replied_count": tracker[key]["count"],
    })


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


# ---------------------------------------------------------------------------
# sync-notifications — 首次同步，标记所有已有通知为已处理
# ---------------------------------------------------------------------------

_DEFAULT_WATERMARK_PATH = os.path.join(
    _get_workspace_dir(), "logs", "notification-watermark.json",
)


def cmd_sync_notifications(args: argparse.Namespace) -> None:
    """首次同步：获取当前所有通知，批量标记为已处理，设置时间水位线。

    后续 Phase 5 应只处理水位线之后的新通知。
    """
    from datetime import datetime, timedelta, timezone
    from xhs.notification import list_notifications

    browser, page = _connect(args)
    try:
        items = list_notifications(page, tab="mentions")
    finally:
        browser.close()

    # 批量写入通知日志
    synced_ids = []
    for item in items:
        if item.id:
            _append_notification_log(item.id)
            synced_ids.append(item.id)

    # 保存水位线（最新通知的时间戳）
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).isoformat()
    watermark_path = args.watermark_file or _DEFAULT_WATERMARK_PATH
    watermark = {
        "last_sync": now,
        "last_notification_time": items[0].time if items else 0,
        "synced_count": len(synced_ids),
    }
    os.makedirs(os.path.dirname(watermark_path), exist_ok=True)
    with open(watermark_path, "w", encoding="utf-8") as f:
        json.dump(watermark, f, ensure_ascii=False, indent=2)

    _output({
        "success": True,
        "synced_count": len(synced_ids),
        "total_notifications": len(items),
        "watermark": watermark,
        "message": f"已标记 {len(synced_ids)} 条通知为已处理，"
                   f"后续只处理新通知",
    })


def cmd_check_watermark(args: argparse.Namespace) -> None:
    """检查通知水位线状态。

    返回水位线信息，如果未初始化则提示需要先运行 sync-notifications。
    """
    watermark_path = args.watermark_file or _DEFAULT_WATERMARK_PATH
    try:
        with open(watermark_path, encoding="utf-8") as f:
            watermark = json.load(f)
        _output({
            "success": True,
            "initialized": True,
            "watermark": watermark,
        })
    except (FileNotFoundError, json.JSONDecodeError):
        _output({
            "success": True,
            "initialized": False,
            "message": "水位线未初始化，请先运行 sync-notifications",
        })


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

    # list-feeds
    sub = subparsers.add_parser("list-feeds", help="获取首页 Feed 列表")
    sub.add_argument("--channel", help="板块名称（推荐/穿搭/美食/彩妆/影视/职场/情感/家居/游戏/旅行/健身）")
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
    sub.add_argument("--xsec-source", default="pc_feed", help="token 来源: pc_feed(推荐页) | pc_search(搜索)")
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

    # post-comment
    sub = subparsers.add_parser("post-comment", help="发表评论")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument("--xsec-source", default="pc_feed", help="token 来源: pc_feed | pc_search")
    sub.add_argument("--content", required=True, help="评论内容")
    sub.set_defaults(func=cmd_post_comment)

    # reply-comment
    sub = subparsers.add_parser("reply-comment", help="回复评论")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument("--xsec-source", default="pc_feed", help="token 来源: pc_feed | pc_search")
    sub.add_argument("--content", required=True, help="回复内容")
    sub.add_argument("--comment-id", help="目标评论 ID")
    sub.add_argument("--user-id", help="目标用户 ID")
    sub.set_defaults(func=cmd_reply_comment)

    # like-feed
    sub = subparsers.add_parser("like-feed", help="点赞")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument("--xsec-source", default="pc_feed", help="token 来源: pc_feed | pc_search")
    sub.add_argument("--unlike", action="store_true", help="取消点赞")
    sub.set_defaults(func=cmd_like_feed)

    # favorite-feed
    sub = subparsers.add_parser("favorite-feed", help="收藏")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument("--xsec-source", default="pc_feed", help="token 来源: pc_feed | pc_search")
    sub.add_argument("--unfavorite", action="store_true", help="取消收藏")
    sub.set_defaults(func=cmd_favorite_feed)

    # list-notifications
    sub = subparsers.add_parser("list-notifications", help="获取通知列表")
    sub.add_argument("--tab", default="mentions", choices=["mentions", "likes", "connections"],
                     help="通知类型: mentions=评论和@, likes=赞和收藏, connections=新增关注")
    sub.set_defaults(func=cmd_list_notifications)

    # reply-notification
    sub = subparsers.add_parser("reply-notification", help="回复通知中的评论")
    sub.add_argument("--index", type=int, required=True, help="通知索引 (0-based)")
    sub.add_argument("--content", required=True, help="回复内容")
    sub.set_defaults(func=cmd_reply_notification)

    # like-notification
    sub = subparsers.add_parser("like-notification", help="在通知页面点赞评论")
    sub.add_argument("--index", type=int, required=True, help="通知索引 (0-based)")
    sub.set_defaults(func=cmd_like_notification)

    # publish
    sub = subparsers.add_parser("publish", help="发布图文")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--images", nargs="+", required=True, help="图片路径/URL")
    sub.add_argument("--tags", nargs="*", help="标签")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.add_argument("--headless", action="store_true", help="无头模式（未登录自动降级）")
    sub.set_defaults(func=cmd_publish)

    # publish-video
    sub = subparsers.add_parser("publish-video", help="发布视频")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--video", required=True, help="视频文件路径")
    sub.add_argument("--tags", nargs="*", help="标签")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.add_argument("--headless", action="store_true", help="无头模式（未登录自动降级）")
    sub.set_defaults(func=cmd_publish_video)

    # fill-publish（只填写图文表单，不发布）
    sub = subparsers.add_parser("fill-publish", help="填写图文表单（不发布）")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--images", nargs="+", required=True, help="图片路径/URL")
    sub.add_argument("--tags", nargs="*", help="标签")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.set_defaults(func=cmd_fill_publish)

    # fill-publish-video（只填写视频表单，不发布）
    sub = subparsers.add_parser("fill-publish-video", help="填写视频表单（不发布）")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--video", required=True, help="视频文件路径")
    sub.add_argument("--tags", nargs="*", help="标签")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.set_defaults(func=cmd_fill_publish_video)

    # fill-text2image（只填写图文-文字配图，不发布）
    sub = subparsers.add_parser("fill-text2image", help="填写图文-文字配图（不发布）")
    sub.add_argument("--title-file", help="标题文件路径（用于文字配图生成；未提供则回退到正文首行）")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--tags", nargs="*", help="标签候选池")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.set_defaults(func=cmd_fill_text2image)

    # publish-text2image（图文-文字配图一键发布）
    sub = subparsers.add_parser("publish-text2image", help="发布图文-文字配图")
    sub.add_argument("--title-file", help="标题文件路径（用于文字配图生成；未提供则回退到正文首行）")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--tags", nargs="*", help="标签候选池")
    sub.add_argument("--schedule-at", help="定时发布 (ISO8601)")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--visibility", help="可见范围")
    sub.add_argument("--location", help="添加地点")
    sub.add_argument("--content-type", help="内容类型声明")
    sub.add_argument("--no-duet", action="store_true", help="禁止合拍")
    sub.add_argument("--no-copy", action="store_true", help="禁止正文复制")
    sub.add_argument("--collection", help="加入合集名称")
    sub.set_defaults(func=cmd_publish_text2image)

    # click-publish（点击发布按钮）
    sub = subparsers.add_parser("click-publish", help="点击发布按钮")
    sub.add_argument("--tags", nargs="*", help="发布前补充标签")
    sub.set_defaults(func=cmd_click_publish)

    # long-article（长文模式）
    sub = subparsers.add_parser("long-article", help="长文模式：填写 + 一键排版")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--images", nargs="*", help="可选图片路径")
    sub.add_argument("--markdown", action="store_true", help="将正文当作 Markdown 解析，注入格式化 HTML")
    sub.set_defaults(func=cmd_long_article)

    # select-template（选择模板）
    sub = subparsers.add_parser("select-template", help="选择排版模板")
    sub.add_argument("--name", required=True, help="模板名称")
    sub.add_argument("--markdown-file", help="Markdown 正文文件，选模板后自动注入格式化 HTML")
    sub.set_defaults(func=cmd_select_template)

    # next-step（下一步 + 填写描述）
    sub = subparsers.add_parser("next-step", help="点击下一步 + 填写描述")
    sub.add_argument("--content-file", required=True, help="描述内容文件路径")
    sub.add_argument("--tags", nargs="*", help="补充标签")
    sub.set_defaults(func=cmd_next_step)

    # save-draft（保存草稿）
    sub = subparsers.add_parser("save-draft", help="保存为草稿（取消发布时使用）")
    sub.set_defaults(func=cmd_save_draft)

    # check-reply-limit（检查同帖同用户回复次数限制，纯本地）
    sub = subparsers.add_parser("check-reply-limit", help="检查同帖同用户回复次数是否已达上限")
    sub.add_argument("--feed-id", default="", help="帖子 feed_id（单条查询）")
    sub.add_argument("--user-id", default="", help="用户 ID 或昵称（单条查询）")
    sub.add_argument("--pairs", default="", help='批量查询 JSON: [{"feed_id":"x","user_id":"y"}, ...]')
    sub.add_argument(
        "--max-replies", type=int, default=2,
        help="同帖同用户最大回复次数 (default: 2)",
    )
    sub.add_argument("--tracker-file", default="", help="追踪文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_check_reply_limit)

    # record-reply（记录回复到追踪器，纯本地）
    sub = subparsers.add_parser("record-reply", help="记录回复到同帖同用户追踪器")
    sub.add_argument("--feed-id", required=True, help="帖子 feed_id")
    sub.add_argument("--user-id", required=True, help="用户 ID 或昵称")
    sub.add_argument("--notification-id", default="", help="通知 ID（可选）")
    sub.add_argument("--tracker-file", default="", help="追踪文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_record_reply)

    # check-interacted（批量查询是否已互动，纯本地，不连 Chrome）
    sub = subparsers.add_parser("check-interacted", help="批量查询 feed/notification 是否已互动过")
    sub.add_argument("--feed-ids", nargs="*", default=[], help="要查询的 feed_id 列表")
    sub.add_argument("--notification-ids", nargs="*", default=[], help="要查询的通知 id 列表")
    sub.add_argument("--authors", default="", help='同作者去重：JSON 格式 {"feed_id":"author_name",...}')
    sub.add_argument("--check-author-days", type=int, default=7, help="同作者去重天数 (default: 7)")
    sub.add_argument("--lookback-days", type=int, default=7, help="通知日志回查天数 (default: 7)")
    sub.add_argument("--index-file", default="", help="索引文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_check_interacted)

    # record-interact（记录互动到索引，纯本地，不连 Chrome）
    sub = subparsers.add_parser("record-interact", help="记录新互动到去重索引")
    sub.add_argument("--feed-id", required=True, help="帖子 feed_id")
    sub.add_argument("--type", required=True, choices=["comment", "like", "favorite"], help="互动类型")
    sub.add_argument("--author", default="", help="作者昵称（用于同作者去重）")
    sub.add_argument("--index-file", default="", help="索引文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_record_interact)

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

    # sync-notifications（首次同步，批量标记已有通知为已处理）
    sub = subparsers.add_parser(
        "sync-notifications",
        help="首次同步：标记所有已有通知为已处理，设置时间水位线",
    )
    sub.add_argument(
        "--watermark-file", default="",
        help="水位线文件路径（默认自动定位）",
    )
    sub.set_defaults(func=cmd_sync_notifications)

    # check-watermark（检查通知水位线状态，纯本地）
    sub = subparsers.add_parser(
        "check-watermark",
        help="检查通知水位线是否已初始化",
    )
    sub.add_argument(
        "--watermark-file", default="",
        help="水位线文件路径（默认自动定位）",
    )
    sub.set_defaults(func=cmd_check_watermark)

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
