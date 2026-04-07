"""发布场景命令：图文、视频、文字配图、长文、模板、草稿。"""

from __future__ import annotations

import argparse

from common import (
    connect,
    connect_existing,
    connect_fresh,
    headless_fallback,
    logger,
    normalize_tags,
    output,
    save_session_tab,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------
def cmd_publish(args: argparse.Namespace) -> None:
    """发布图文内容。"""
    from image_downloader import process_images
    from xhs.login import check_login_status
    from xhs.publish import publish_image_content
    from xhs.types import PublishImageContent

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    image_paths = process_images(args.images) if args.images else []
    if not image_paths:
        output({"success": False, "error": "没有有效的图片"}, exit_code=2)

    browser, page = connect(args)
    try:
        headless = getattr(args, "headless", False)
        if headless and not check_login_status(page):
            browser.close()
            headless_fallback(args.port)
            return

        publish_image_content(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output({"success": True, "title": title, "images": len(image_paths), "status": "发布完成"})
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
        output({"success": False, "error": "没有有效的图片"}, exit_code=2)

    browser, page = connect(args)
    try:
        fill_publish_form(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output(
            {
                "success": True,
                "title": title,
                "images": len(image_paths),
                "status": "表单已填写，等待确认发布",
            }
        )
    finally:
        browser.close()


def cmd_fill_publish_video(args: argparse.Namespace) -> None:
    """只填写视频表单，不发布。"""
    from xhs.publish_video import fill_publish_video_form
    from xhs.types import PublishVideoContent

    with open(args.title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(args.content_file, encoding="utf-8") as f:
        content = f.read().strip()

    browser, page = connect(args)
    try:
        fill_publish_video_form(
            page,
            PublishVideoContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output(
            {
                "success": True,
                "title": title,
                "video": args.video,
                "status": "视频表单已填写，等待确认发布",
            }
        )
    finally:
        browser.close()


def cmd_click_publish(args: argparse.Namespace) -> None:
    """点击发布按钮（在用户确认后调用）。复用已有的发布页 tab。"""
    from rate_limiter import check_and_increment
    allowed, count, limit = check_and_increment("publish")
    if not allowed:
        output({"success": False, "error": f"今日发布已达上限 ({count}/{limit})"}, exit_code=2)
        return

    from xhs.publish import click_publish_button

    browser, page = connect_existing(args)
    try:
        click_publish_button(page, tags=normalize_tags(args.tags))
        output({"success": True, "status": "发布完成"})
    finally:
        browser.close()


def cmd_save_draft(args: argparse.Namespace) -> None:
    """保存为草稿（取消发布时调用）。"""
    from xhs.publish import save_as_draft

    browser, page = connect_existing(args)
    try:
        save_as_draft(page)
        output({"success": True, "status": "内容已保存到草稿箱"})
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

    browser, page = connect(args)
    try:
        template_names = publish_long_article(
            page,
            title=title,
            content=content,
            markdown=markdown,
            image_paths=args.images,
        )
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
        save_session_tab(actual_id, args.port)
        logger.info("session tab 已保存: %s", actual_id[:16])
        output(
            {
                "success": True,
                "templates": template_names,
                "status": "长文已填写，请选择模板",
            }
        )
    finally:
        browser.close()


def cmd_select_template(args: argparse.Namespace) -> None:
    """选择排版模板。复用已有的长文编辑页 tab。

    如果传了 --markdown-file，选模板后自动将 Markdown 内容注入为格式化 HTML。
    """
    from xhs.publish_long_article import select_template, upgrade_content_format

    browser, page = connect_existing(args)
    try:
        selected = select_template(page, args.name)
        if not selected:
            output(
                {"success": False, "error": f"未找到模板: {args.name}"},
                exit_code=2,
            )
            return

        upgraded = False
        md_file = getattr(args, "markdown_file", None)
        if md_file:
            with open(md_file, encoding="utf-8") as f:
                md_content = f.read().strip()
            upgraded = upgrade_content_format(page, md_content)

        output({
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

    browser, page = connect_existing(args)
    try:
        click_next_and_fill_description(page, description, tags=normalize_tags(args.tags))
        output({"success": True, "status": "已进入发布页，等待确认发布"})
    finally:
        browser.close()


def cmd_fill_text2image(args: argparse.Namespace) -> None:
    """只填写图文-文字配图表单，不发布。"""
    from xhs.publish import fill_text2image_form
    from xhs.types import PublishImageContent

    title, content = _load_text2image_inputs(args)

    browser, page = connect_fresh(args)
    try:
        fill_text2image_form(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output({"success": True, "status": "文字配图已生成，等待确认发布"})
    finally:
        browser.close()


def cmd_publish_text2image(args: argparse.Namespace) -> None:
    """发布图文-文字配图内容。"""
    from xhs.publish import publish_text2image_content
    from xhs.types import PublishImageContent

    title, content = _load_text2image_inputs(args)

    browser, page = connect_fresh(args)
    try:
        publish_text2image_content(
            page,
            PublishImageContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output({"success": True, "status": "文字配图发布完成"})
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

    browser, page = connect(args)
    try:
        headless = getattr(args, "headless", False)
        if headless and not check_login_status(page):
            browser.close()
            headless_fallback(args.port)
            return

        publish_video_content(
            page,
            PublishVideoContent(
                title=title,
                content=content,
                tags=normalize_tags(args.tags),
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
        output({"success": True, "title": title, "video": args.video, "status": "发布完成"})
    finally:
        browser.close()


# ---------------------------------------------------------------------------
# Argparse 注册
# ---------------------------------------------------------------------------
def register_publish_commands(subparsers) -> None:
    """向 argparse 注册所有发布场景子命令。"""

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

    # fill-publish
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

    # fill-publish-video
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

    # fill-text2image
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

    # publish-text2image
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

    # click-publish
    sub = subparsers.add_parser("click-publish", help="点击发布按钮")
    sub.add_argument("--tags", nargs="*", help="发布前补充标签")
    sub.set_defaults(func=cmd_click_publish)

    # long-article
    sub = subparsers.add_parser("long-article", help="长文模式：填写 + 一键排版")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--content-file", required=True, help="正文文件路径")
    sub.add_argument("--images", nargs="*", help="可选图片路径")
    sub.add_argument("--markdown", action="store_true",
                     help="将正文当作 Markdown 解析，注入格式化 HTML")
    sub.set_defaults(func=cmd_long_article)

    # select-template
    sub = subparsers.add_parser("select-template", help="选择排版模板")
    sub.add_argument("--name", required=True, help="模板名称")
    sub.add_argument("--markdown-file", help="Markdown 正文文件，选模板后自动注入格式化 HTML")
    sub.set_defaults(func=cmd_select_template)

    # next-step
    sub = subparsers.add_parser("next-step", help="点击下一步 + 填写描述")
    sub.add_argument("--content-file", required=True, help="描述内容文件路径")
    sub.add_argument("--tags", nargs="*", help="补充标签")
    sub.set_defaults(func=cmd_next_step)

    # save-draft
    sub = subparsers.add_parser("save-draft", help="保存为草稿（取消发布时使用）")
    sub.set_defaults(func=cmd_save_draft)
