"""互动场景命令：评论、点赞、收藏、通知、去重索引、回复追踪、水位线。"""

from __future__ import annotations

import argparse
import json
import os

from common import connect, output, logger


# ---------------------------------------------------------------------------
# Workspace 路径
# ---------------------------------------------------------------------------
def _get_workspace_dir() -> str:
    """获取 workspace 根目录。优先使用 XHS_WORKSPACE 环境变量，否则回退到 openclaw 路径。"""
    return os.environ.get(
        "XHS_WORKSPACE",
        os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "xhs-autopilot"),
    )


_DEFAULT_INDEX_PATH = os.path.join(_get_workspace_dir(), "logs", "interacted-index.json")

_DEFAULT_LOG_DIR = os.path.join(_get_workspace_dir(), "logs")

_DEFAULT_REPLY_TRACKER_PATH = os.path.join(_get_workspace_dir(), "logs", "reply-tracker.json")

_DEFAULT_WATERMARK_PATH = os.path.join(
    _get_workspace_dir(), "logs", "notification-watermark.json",
)


# ---------------------------------------------------------------------------
# 通知日志 helper
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 去重索引 helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 回复追踪 helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 评论 / 回复
# ---------------------------------------------------------------------------
def cmd_post_comment(args: argparse.Namespace) -> None:
    """发表评论。"""
    from xhs.comment import post_comment
    from xhs.errors import DuplicateCommentError

    browser, page = connect(args)
    try:
        post_comment(
            page, args.feed_id, args.xsec_token, args.content,
            xsec_source=getattr(args, "xsec_source", "pc_feed"),
        )
        output({"success": True, "message": "评论发送成功"})
    except DuplicateCommentError as e:
        output({"success": False, "message": str(e), "duplicate": True})
    finally:
        browser.close()


def cmd_reply_comment(args: argparse.Namespace) -> None:
    """回复评论。"""
    from xhs.comment import reply_comment

    browser, page = connect(args)
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
        output({"success": True, "message": "回复成功"})
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 点赞 / 收藏
# ---------------------------------------------------------------------------
def cmd_like_feed(args: argparse.Namespace) -> None:
    """点赞/取消点赞。"""
    from xhs.like_favorite import like_feed, unlike_feed

    browser, page = connect(args)
    try:
        xsec_source = getattr(args, "xsec_source", "pc_feed")
        if args.unlike:
            result = unlike_feed(page, args.feed_id, args.xsec_token, xsec_source)
        else:
            result = like_feed(page, args.feed_id, args.xsec_token, xsec_source)
        output(result.to_dict())
    finally:
        browser.close()


def cmd_favorite_feed(args: argparse.Namespace) -> None:
    """收藏/取消收藏。"""
    from xhs.like_favorite import favorite_feed, unfavorite_feed

    browser, page = connect(args)
    try:
        xsec_source = getattr(args, "xsec_source", "pc_feed")
        if args.unfavorite:
            result = unfavorite_feed(page, args.feed_id, args.xsec_token, xsec_source)
        else:
            result = favorite_feed(page, args.feed_id, args.xsec_token, xsec_source)
        output(result.to_dict())
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 通知
# ---------------------------------------------------------------------------
def cmd_list_notifications(args: argparse.Namespace) -> None:
    """获取通知列表。"""
    from xhs.notification import list_notifications

    browser, page = connect(args)
    try:
        tab = getattr(args, "tab", "mentions")
        items = list_notifications(page, tab=tab)
        output({
            "tab": tab,
            "count": len(items),
            "items": [item.to_dict() for item in items],
        })
    finally:
        browser.close()


def cmd_reply_notification(args: argparse.Namespace) -> None:
    """在通知页面直接回复评论。"""
    from xhs.notification import list_notifications, reply_notification

    browser, page = connect(args)
    try:
        # 先获取通知列表（同时导航到通知页面）
        items = list_notifications(page, tab="mentions")

        index = args.index
        if index >= len(items):
            output({"success": False, "message": f"通知索引 {index} 超出范围 (共 {len(items)} 条)"})
            return

        item = items[index]

        # 在通知页面直接回复
        reply_notification(page, index, args.content)

        # 自动写入通知日志（使 check-interacted --notification-ids 能查到）
        _append_notification_log(item.id)

        output({
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

    browser, page = connect(args)
    try:
        items = list_notifications(page, tab="mentions")

        index = args.index
        if index >= len(items):
            output({"success": False, "message": f"通知索引 {index} 超出范围 (共 {len(items)} 条)"})
            return

        item = items[index]
        liked = like_notification(page, index)

        # 记录到通知日志（防止重复处理）
        if liked:
            _append_notification_log(item.id)

        output({
            "success": True,
            "liked": liked,
            "message": "点赞成功" if liked else "已点赞过，跳过",
            "replyFrom": item.user.nickname,
        })
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# 去重索引管理（纯本地，不连 Chrome）
# ---------------------------------------------------------------------------
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
        output({"success": False, "error": "至少提供 --feed-ids 或 --notification-ids"}, exit_code=2)

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

    output(out)


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

    output({
        "success": True,
        "feed_id": fid,
        "recorded": feeds_index[fid],
        "total_indexed": len(feeds_index),
    })


# ---------------------------------------------------------------------------
# 同帖同用户回复次数限制
# ---------------------------------------------------------------------------
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
            output({"success": False, "error": "--pairs JSON 解析失败"}, exit_code=2)
    elif args.feed_id and args.user_id:
        pairs = [{"feed_id": args.feed_id, "user_id": args.user_id}]
    else:
        output({"success": False, "error": "需要 --pairs 或 --feed-id + --user-id"}, exit_code=2)

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

    output({
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

    output({
        "success": True,
        "key": key,
        "replied_count": tracker[key]["count"],
    })


# ---------------------------------------------------------------------------
# sync-notifications / check-watermark
# ---------------------------------------------------------------------------
def cmd_sync_notifications(args: argparse.Namespace) -> None:
    """首次同步：获取当前所有通知，批量标记为已处理，设置时间水位线。

    后续 Phase 5 应只处理水位线之后的新通知。
    """
    from datetime import datetime, timedelta, timezone
    from xhs.notification import list_notifications

    browser, page = connect(args)
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

    output({
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
        output({
            "success": True,
            "initialized": True,
            "watermark": watermark,
        })
    except (FileNotFoundError, json.JSONDecodeError):
        output({
            "success": True,
            "initialized": False,
            "message": "水位线未初始化，请先运行 sync-notifications",
        })


# ---------------------------------------------------------------------------
# Argparse 注册
# ---------------------------------------------------------------------------
def register_interact_commands(subparsers) -> None:
    """向 argparse 注册所有互动场景子命令。"""

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
    sub.add_argument(
        "--tab", default="mentions",
        choices=["mentions", "likes", "connections"],
        help="通知类型: mentions=评论和@, likes=赞和收藏, connections=新增关注",
    )
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

    # check-interacted
    sub = subparsers.add_parser("check-interacted", help="批量查询 feed/notification 是否已互动过")
    sub.add_argument("--feed-ids", nargs="*", default=[], help="要查询的 feed_id 列表")
    sub.add_argument("--notification-ids", nargs="*", default=[], help="要查询的通知 id 列表")
    sub.add_argument(
        "--authors", default="",
        help='同作者去重：JSON 格式 {"feed_id":"author_name",...}',
    )
    sub.add_argument("--check-author-days", type=int, default=7, help="同作者去重天数 (default: 7)")
    sub.add_argument("--lookback-days", type=int, default=7, help="通知日志回查天数 (default: 7)")
    sub.add_argument("--index-file", default="", help="索引文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_check_interacted)

    # record-interact
    sub = subparsers.add_parser("record-interact", help="记录新互动到去重索引")
    sub.add_argument("--feed-id", required=True, help="帖子 feed_id")
    sub.add_argument(
        "--type", required=True,
        choices=["comment", "like", "favorite"],
        help="互动类型",
    )
    sub.add_argument("--author", default="", help="作者昵称（用于同作者去重）")
    sub.add_argument("--index-file", default="", help="索引文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_record_interact)

    # check-reply-limit
    sub = subparsers.add_parser("check-reply-limit", help="检查同帖同用户回复次数是否已达上限")
    sub.add_argument("--feed-id", default="", help="帖子 feed_id（单条查询）")
    sub.add_argument("--user-id", default="", help="用户 ID 或昵称（单条查询）")
    sub.add_argument(
        "--pairs", default="",
        help='批量查询 JSON: [{"feed_id":"x","user_id":"y"}, ...]',
    )
    sub.add_argument(
        "--max-replies", type=int, default=2,
        help="同帖同用户最大回复次数 (default: 2)",
    )
    sub.add_argument("--tracker-file", default="", help="追踪文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_check_reply_limit)

    # record-reply
    sub = subparsers.add_parser("record-reply", help="记录回复到同帖同用户追踪器")
    sub.add_argument("--feed-id", required=True, help="帖子 feed_id")
    sub.add_argument("--user-id", required=True, help="用户 ID 或昵称")
    sub.add_argument("--notification-id", default="", help="通知 ID（可选）")
    sub.add_argument("--tracker-file", default="", help="追踪文件路径（默认自动定位）")
    sub.set_defaults(func=cmd_record_reply)

    # sync-notifications
    sub = subparsers.add_parser(
        "sync-notifications",
        help="首次同步：标记所有已有通知为已处理，设置时间水位线",
    )
    sub.add_argument(
        "--watermark-file", default="",
        help="水位线文件路径（默认自动定位）",
    )
    sub.set_defaults(func=cmd_sync_notifications)

    # check-watermark
    sub = subparsers.add_parser(
        "check-watermark",
        help="检查通知水位线是否已初始化",
    )
    sub.add_argument(
        "--watermark-file", default="",
        help="水位线文件路径（默认自动定位）",
    )
    sub.set_defaults(func=cmd_check_watermark)
