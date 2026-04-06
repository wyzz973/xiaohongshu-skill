"""创作服务平台数据采集模块。

从 creator.xiaohongshu.com 获取：
- 笔记列表及深度分析数据
- 账号总览仪表盘
- 粉丝画像
- 审核处罚详情
"""

from __future__ import annotations

import json
import logging
import re
import time

from .cdp import Page
from .human import sleep_random

logger = logging.getLogger(__name__)

CREATOR_NOTE_MANAGER = (
    "https://creator.xiaohongshu.com/new/note-manager?source=official"
)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _evaluate_async(page: Page, js: str, timeout: float = 30.0):
    """执行异步 JS（含 await），返回结果值。"""
    result = page._send_session(
        "Runtime.evaluate",
        {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    if "exceptionDetails" in result:
        logger.warning("JS async 异常: %s", result["exceptionDetails"])
        return None
    return result.get("result", {}).get("value")


def _setup_xhr_interceptor(page: Page) -> None:
    """注入 XHR 拦截器，捕获所有 galaxy API 响应。"""
    page.evaluate(
        'window._xhrCaptures = {};'
        'var _origOpen = XMLHttpRequest.prototype.open;'
        'var _origSend = XMLHttpRequest.prototype.send;'
        'XMLHttpRequest.prototype.open = function(m, url) {'
        '  this._url = url; return _origOpen.apply(this, arguments);'
        '};'
        'XMLHttpRequest.prototype.send = function() {'
        '  var xhr = this;'
        '  xhr.addEventListener("load", function() {'
        '    if (xhr._url && xhr.status === 200 && xhr._url.indexOf("galaxy") >= 0) {'
        '      window._xhrCaptures[xhr._url] = xhr.responseText;'
        '    }'
        '  });'
        '  return _origSend.apply(this, arguments);'
        '};'
    )


def _navigate_via_router(page: Page, path: str) -> None:
    """通过 Vue Router 导航到指定路径。"""
    page.evaluate(
        f'document.querySelector("#app").__vue_app__'
        f'.config.globalProperties.$router.push("{path}")'
    )
    time.sleep(4)


def _get_captured_response(page: Page, url_fragment: str) -> dict | None:
    """从 XHR 捕获中获取匹配的响应。"""
    js = (
        f'(function(){{'
        f'  for (var url in window._xhrCaptures) {{'
        f'    if (url.indexOf("{url_fragment}") >= 0) {{'
        f'      return window._xhrCaptures[url];'
        f'    }}'
        f'  }}'
        f'  return null;'
        f'}})()'
    )
    raw = page.evaluate(js)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def _ensure_creator_platform(page: Page) -> None:
    """确保在创作服务平台上，如果不在则导航过去。"""
    current = page.evaluate("window.location.href")
    if "creator.xiaohongshu.com" not in (current or ""):
        page.navigate(CREATOR_NOTE_MANAGER)
        time.sleep(5)
        page.wait_dom_stable(timeout=8)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def list_my_notes(page: Page) -> dict:
    """获取我的全部笔记及深度分析数据。

    流程：
    1. 导航到笔记管理页 → 拿笔记基础列表（含 xsec_token）
    2. Vue Router 到 data-analysis → 拦截笔记分析 API
    3. 合并两份数据

    Returns:
        {
            "notes": [...],       # 合并后的笔记列表
            "total": int,
            "summary": {...},     # 汇总统计
        }
    """
    _ensure_creator_platform(page)
    _setup_xhr_interceptor(page)

    # --- Step 1: 从笔记管理页获取基础列表 ---
    _navigate_via_router(page, "/new/note-manager")
    time.sleep(3)

    # 等页面 XHR 触发
    basic_data = _get_captured_response(page, "note/user/posted")
    basic_notes = {}
    if basic_data and basic_data.get("code") == 0:
        for note in basic_data.get("data", {}).get("notes", []):
            basic_notes[note["id"]] = note

    # 翻页获取更多（如果有分页）
    page_num = 1
    while basic_data and basic_data.get("data", {}).get("has_more", False):
        page_num += 1
        # 重置捕获，翻页
        page.evaluate('window._xhrCaptures = {}')
        page.evaluate(
            f'var items = document.querySelectorAll("li");'
            f'for (var i = 0; i < items.length; i++) {{'
            f'  if (items[i].textContent.trim() === "{page_num}") {{'
            f'    items[i].click(); break;'
            f'  }}'
            f'}}'
        )
        time.sleep(3)
        basic_data = _get_captured_response(page, "note/user/posted")
        if basic_data and basic_data.get("code") == 0:
            for note in basic_data.get("data", {}).get("notes", []):
                basic_notes[note["id"]] = note

    logger.info("笔记管理页获取到 %d 篇笔记", len(basic_notes))

    # --- Step 2: 从数据分析页获取深度分析 ---
    page.evaluate('window._xhrCaptures = {}')
    _navigate_via_router(page, "/statistics/data-analysis")
    time.sleep(5)

    analytics = {}
    analysis_data = _get_captured_response(page, "analyze/list")
    if analysis_data and analysis_data.get("code") == 0:
        total_analysis = analysis_data.get("data", {}).get("total", 0)
        for note in analysis_data.get("data", {}).get("note_infos", []):
            analytics[note["id"]] = note

        # 翻页获取剩余分析数据
        page_num = 1
        while len(analytics) < total_analysis:
            page_num += 1
            page.evaluate('window._xhrCaptures = {}')
            page.evaluate(
                f'var items = document.querySelectorAll("li");'
                f'for (var i = 0; i < items.length; i++) {{'
                f'  if (items[i].textContent.trim() === "{page_num}"'
                f'    && items[i].className.indexOf("number") >= 0) {{'
                f'    items[i].click(); break;'
                f'  }}'
                f'}}'
            )
            time.sleep(3)
            more = _get_captured_response(page, "analyze/list")
            if more and more.get("code") == 0:
                for note in more.get("data", {}).get("note_infos", []):
                    analytics[note["id"]] = note
            else:
                break

    logger.info("数据分析页获取到 %d 篇分析数据", len(analytics))

    # --- Step 3: 合并数据 ---
    merged = []
    all_ids = set(list(basic_notes.keys()) + list(analytics.keys()))
    for nid in all_ids:
        basic = basic_notes.get(nid, {})
        anal = analytics.get(nid, {})
        note = {
            "id": nid,
            "title": (
                basic.get("display_title")
                or anal.get("title")
                or "(无标题)"
            ),
            "post_time": (
                basic.get("time")
                or _format_post_time(anal.get("post_time"))
            ),
            "type": _note_type_str(anal.get("type", 0)),
            "xsec_token": basic.get("xsec_token", ""),
            "xsec_source": basic.get("xsec_source", ""),
            "sticky": basic.get("sticky", False),
            # 审核状态
            "audit_status": _audit_status_str(
                anal.get("audit_status", basic.get("tab_status", 1))
            ),
            # 基础互动（来自笔记管理页，实时）
            "views": basic.get("view_count", anal.get("read_count", 0)),
            "likes": basic.get("likes", anal.get("like_count", 0)),
            "comments": basic.get("comments_count", anal.get("comment_count", 0)),
            "favorites": basic.get("collected_count", anal.get("fav_count", 0)),
            "shares": basic.get("shared_count", anal.get("share_count", 0)),
            # 深度分析（来自数据分析页）
            "impressions": anal.get("imp_count", 0),
            "click_through_rate": anal.get("coverClickRate", 0),
            "avg_view_duration": anal.get("view_time_avg", 0),
            "fans_gained": anal.get("increase_fans_count", 0),
            "danmaku": anal.get("danmaku_count", 0),
            "cover_url": (
                basic.get("images_list", [{}])[0].get("url", "")
                if basic.get("images_list")
                else anal.get("cover_url", "")
            ),
        }
        merged.append(note)

    # 按发布时间倒序
    merged.sort(
        key=lambda n: n.get("post_time", ""),
        reverse=True,
    )

    # 汇总
    summary = {
        "total_notes": len(merged),
        "total_views": sum(n["views"] for n in merged),
        "total_impressions": sum(n["impressions"] for n in merged),
        "total_likes": sum(n["likes"] for n in merged),
        "total_favorites": sum(n["favorites"] for n in merged),
        "total_comments": sum(n["comments"] for n in merged),
        "total_shares": sum(n["shares"] for n in merged),
        "total_fans_gained": sum(n["fans_gained"] for n in merged),
        "avg_ctr": (
            round(
                sum(n["click_through_rate"] for n in merged if n["impressions"] > 0)
                / max(1, sum(1 for n in merged if n["impressions"] > 0)),
                3,
            )
        ),
        "avg_view_duration": (
            round(
                sum(n["avg_view_duration"] for n in merged if n["avg_view_duration"] > 0)
                / max(1, sum(1 for n in merged if n["avg_view_duration"] > 0)),
            )
        ),
    }

    return {"notes": merged, "total": len(merged), "summary": summary}


def get_dashboard(page: Page) -> dict:
    """获取账号总览仪表盘数据。

    从 /new/home 页面提取账号级汇总数据。

    Returns:
        {
            "account": {...},     # 基础信息
            "overview_7d": {...}, # 7 日数据总览 + 环比
            "diagnosis": {...},   # 账号诊断（超过同类百分比）
        }
    """
    _ensure_creator_platform(page)
    _navigate_via_router(page, "/new/home")
    time.sleep(5)

    text = page.evaluate("document.body.innerText")

    result: dict = {
        "account": _parse_account_basic(text),
        "overview_7d": _parse_overview(text),
    }

    # 跳转到账号诊断获取百分位数据
    _setup_xhr_interceptor(page)
    _navigate_via_router(page, "/statistics/account/v2")
    time.sleep(4)

    diag_text = page.evaluate("document.body.innerText")
    result["diagnosis"] = _parse_diagnosis(diag_text)

    return result


def get_fans_profile(page: Page) -> dict:
    """获取粉丝画像数据。

    Returns:
        {
            "total": int,
            "new": int,
            "lost": int,
            "gender": {...},
            "interests": [...],
            "active_fans": [...],
        }
    """
    _ensure_creator_platform(page)
    _navigate_via_router(page, "/statistics/fans-data")
    time.sleep(4)

    text = page.evaluate("document.body.innerText")
    return _parse_fans_data(text)


def get_audit_detail(page: Page, note_id: str) -> dict | None:
    """获取指定笔记的审核处罚详情。

    需要先导航到笔记管理页，找到未通过笔记并点击"查看修改建议"。
    如果该笔记没有审核问题，返回 None。

    由于需要精确匹配 note_id，这里通过 API 直接获取。
    """
    _ensure_creator_platform(page)
    _setup_xhr_interceptor(page)
    _navigate_via_router(page, "/new/note-manager")
    time.sleep(3)

    # 点击"查看修改建议"（如果存在）
    page.evaluate(
        'var els = document.querySelectorAll("[class*=audit-toast]");'
        'for (var i = 0; i < els.length; i++) {'
        '  if (els[i].textContent.indexOf("修改建议") >= 0) {'
        '    els[i].click(); break;'
        '  }'
        '}'
    )
    time.sleep(3)

    data = _get_captured_response(page, "punish/detail")
    if not data or data.get("code") != 0:
        return None

    detail = data.get("data", {})
    rules = []
    for item in detail.get("detail_list", []):
        rules.append({
            "tag": item.get("tag_name", ""),
            "brief": item.get("tag_reason_brief", ""),
            "reason": item.get("punish_reason", ""),
            "advice": item.get("modify_advice", ""),
        })

    return {
        "note_id": note_id,
        "punish_name": detail.get("punish_name", ""),
        "limit_time": detail.get("limit_time", ""),
        "process_time": detail.get("process_time", ""),
        "actions": detail.get("action_display_names", []),
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# DOM 文本解析工具
# ---------------------------------------------------------------------------


def _parse_account_basic(text: str) -> dict:
    """从首页文本提取账号基础信息。"""
    result: dict = {}
    m = re.search(r"(\d+)\s*关注数", text)
    if m:
        result["following"] = int(m.group(1))
    m = re.search(r"(\d+)\s*粉丝数", text)
    if m:
        result["followers"] = int(m.group(1))
    m = re.search(r"(\d+)\s*获赞与收藏", text)
    if m:
        result["total_likes_favs"] = int(m.group(1))
    m = re.search(r"小红书账号:\s*(\S+)", text)
    if m:
        result["red_id"] = m.group(1)
    return result


def _parse_overview(text: str) -> dict:
    """从首页文本提取 7 日数据总览。"""
    result: dict = {}
    patterns = [
        ("impressions", r"曝光数\s*([\d.]+万?)"),
        ("views", r"观看数\s*([\d.]+万?)"),
        ("cover_ctr", r"封面点击率\s*([\d.]+%)"),
        ("avg_view_duration", r"平均观看时长\s*(\d+秒)"),
        ("completion_rate", r"视频完播率\s*(\d+%)"),
        ("likes", r"点赞数\s*(\d+)"),
        ("comments", r"评论数\s*(\d+)"),
        ("favorites", r"收藏数\s*(\d+)"),
        ("shares", r"分享数\s*(\d+)"),
        ("net_followers", r"净涨粉\s*(\d+)"),
        ("new_followers", r"新增关注\s*(\d+)"),
        ("unfollowers", r"取消关注\s*(\d+)"),
        ("profile_visitors", r"主页访客\s*(\d+)"),
    ]
    for key, pattern in patterns:
        m = re.search(pattern, text)
        if m:
            result[key] = m.group(1)

    # 提取环比
    trends = {}
    trend_pattern = re.finditer(r"环比([+-]?\d+%?)", text)
    keys_order = [p[0] for p in patterns]
    for i, m in enumerate(trend_pattern):
        if i < len(keys_order):
            trends[keys_order[i]] = m.group(1)
    if trends:
        result["trends"] = trends

    return result


def _parse_diagnosis(text: str) -> dict:
    """从账号诊断页提取百分位排名。"""
    result: dict = {}
    pattern = re.finditer(
        r"你的(\S+?)为\s*([\d.]+\S*)\s*，超过\s*(\d+)%\s*的同类创作者",
        text,
    )
    for m in pattern:
        key = m.group(1).replace("数", "")
        result[key] = {
            "value": m.group(2),
            "percentile": int(m.group(3)),
        }
    return result


def _parse_fans_data(text: str) -> dict:
    """从粉丝数据页提取画像信息。"""
    result: dict = {}

    m = re.search(r"总粉丝数\s*(\d+)", text)
    if m:
        result["total"] = int(m.group(1))
    m = re.search(r"新增粉丝数\s*(\d+)", text)
    if m:
        result["new"] = int(m.group(1))
    m = re.search(r"流失粉丝数\s*(\d+)", text)
    if m:
        result["lost"] = int(m.group(1))

    # 性别
    gender = {}
    m = re.search(r"男性\s*(\d+)%", text)
    if m:
        gender["male"] = int(m.group(1))
    m = re.search(r"女性\s*(\d+)%", text)
    if m:
        gender["female"] = int(m.group(1))
    if gender:
        result["gender"] = gender

    # 兴趣
    interests = re.findall(
        r"(教育|生活记录|职场|科技数码|美食|娱乐|时尚|情感|美妆|旅行|健身|家居|游戏|影视)",
        text,
    )
    if interests:
        result["interests"] = list(dict.fromkeys(interests))

    return result


def _note_type_str(t: int) -> str:
    return {1: "image", 2: "video"}.get(t, "unknown")


def _audit_status_str(s: int) -> str:
    return {0: "reviewing", 1: "published", 2: "rejected", 3: "deleted"}.get(
        s, str(s)
    )


def _format_post_time(ts: int | None) -> str:
    if not ts:
        return ""
    import datetime

    dt = datetime.datetime.fromtimestamp(
        ts / 1000, tz=datetime.timezone(datetime.timedelta(hours=8))
    )
    return dt.strftime("%Y-%m-%d %H:%M")
