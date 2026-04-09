"""图文发布，对应 Go xiaohongshu/publish.go（837 行）。"""

from __future__ import annotations

import json
import logging
import random
import re
import time

from .cdp import Page
from .errors import ContentTooLongError, PublishError, TitleTooLongError, UploadTimeoutError
from .selectors import (
    COLLECTION_TRIGGER,
    CONTENT_EDITOR,
    CONTENT_LENGTH_ERROR,
    CONTENT_TYPE_DROPDOWN,
    CONTENT_TYPE_OPTIONS,
    CREATOR_TAB,
    DATETIME_INPUT,
    FILE_INPUT,
    IMAGE_PREVIEW,
    LOCATION_DROPDOWN,
    LOCATION_INPUT,
    LOCATION_OPTIONS,
    ORIGINAL_SWITCH,
    ORIGINAL_SWITCH_CARD,
    POPOVER,
    PUBLISH_BUTTON,
    SCHEDULE_SWITCH,
    TAG_FIRST_ITEM,
    TAG_TOPIC_CONTAINER,
    TITLE_INPUT,
    TITLE_MAX_SUFFIX,
    UPLOAD_CONTENT,
    UPLOAD_INPUT,
    VISIBILITY_DROPDOWN,
    VISIBILITY_OPTIONS,
)
from .types import PublishImageContent
from .urls import PUBLISH_URL

TEXT2IMAGE_EDITOR = "div.tiptap.ProseMirror, div.ProseMirror"
TEXT2IMAGE_TRIGGER = "button.text2image-button"
TEXT2IMAGE_GENERATE_BUTTON = ".edit-text-button"

logger = logging.getLogger(__name__)


def _derive_text2image_prompt(title: str, content: str) -> str:
    """文字配图阶段只使用短标题/封面句作为生成提示。"""
    prompt = (title or "").strip()
    if prompt:
        return prompt

    for line in content.splitlines():
        line = line.strip()
        if line:
            fallback = line[:20]
            logger.warning("文字配图未提供标题，退化使用正文首行作为提示词: %s", fallback)
            return fallback
    raise PublishError("文字配图缺少可用标题/提示词")


def _pick_text2image_tags(title: str, content: str, candidate_tags: list[str]) -> list[str]:
    """从候选标签里随机挑选 3-6 个，更像真人发布。"""
    normalized: list[str] = []
    for tag in candidate_tags or []:
        t = tag.strip().lstrip("#")
        if t and t not in normalized:
            normalized.append(t)

    if not normalized:
        return []

    desired = min(len(normalized), random.randint(3, 6))
    haystack = re.sub(r"\s+", "", f"{title}\n{content}").lower()
    related: list[str] = []
    rest: list[str] = []

    for tag in normalized:
        needle = re.sub(r"\s+", "", tag).lower()
        if needle and needle in haystack:
            related.append(tag)
        else:
            rest.append(tag)

    random.shuffle(related)
    random.shuffle(rest)
    selected = (related + rest)[:desired]
    random.shuffle(selected)
    logger.info("文字配图随机标签: candidates=%s selected=%s", normalized, selected)
    return selected


def publish_image_content(page: Page, content: PublishImageContent) -> None:
    """发布图文内容（填写表单 + 点击发布）。

    Args:
        page: CDP 页面对象。
        content: 发布内容。

    Raises:
        PublishError: 发布失败。
        UploadTimeoutError: 上传超时。
        TitleTooLongError: 标题超长。
        ContentTooLongError: 正文超长。
    """
    fill_publish_form(page, content)
    click_publish_button(page)


def fill_text2image_form(page: Page, content: PublishImageContent) -> None:
    """填写图文-文字配图表单，不立即发布。"""
    _navigate_to_publish_page(page)
    _click_publish_tab(page, "上传图文")
    time.sleep(1)

    clicked = page.evaluate(
        f"""
        (() => {{
            const btn = document.querySelector({json.dumps(TEXT2IMAGE_TRIGGER)});
            if (!btn) return false;
            btn.click();
            return true;
        }})()
        """
    )
    if not clicked:
        raise PublishError("未找到'文字配图'按钮")
    time.sleep(2)
    page.wait_dom_stable()

    # 输入文字配图提示词（只用短标题/封面句，不直接灌整段正文）
    prompt_text = _derive_text2image_prompt(content.title, content.content)
    safe_text = json.dumps(prompt_text)
    safe_selector = json.dumps(TEXT2IMAGE_EDITOR)
    ok = page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({safe_selector});
            if (!el) return false;
            el.focus();
            el.innerHTML = '<p></p>';
            const p = el.querySelector('p') || document.createElement('p');
            p.textContent = {safe_text};
            if (!p.parentElement) el.appendChild(p);
            el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: null }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
    )
    if not ok:
        raise PublishError("未找到文字配图输入框")
    logger.info("已填写文字配图提示词: %s", prompt_text)
    time.sleep(1)

    # 生成图片
    page.click_element(TEXT2IMAGE_GENERATE_BUTTON)
    logger.info("已点击'生成图片'")
    time.sleep(8)
    page.wait_dom_stable()

    # 点击下一步进入最终发布页
    next_clicked = page.evaluate(
        """
        (() => {
            const els = [...document.querySelectorAll('button,[role="button"],div,span')];
            const el = els.find(x => (x.textContent || '').trim() === '下一步');
            if (!el) return false;
            (el.closest('button,[role="button"]') || el).click();
            return true;
        })()
        """
    )
    if not next_clicked:
        raise PublishError("文字配图流程未找到'下一步'按钮")
    time.sleep(6)
    page.wait_dom_stable()

    final_title = (content.title or prompt_text).strip()
    final_tags = _pick_text2image_tags(final_title, content.content, content.tags)

    # 进入最终发布页后，覆盖掉生成阶段残留提示词，再填标题/正文/随机标签
    _fill_text2image_publish_form(
        page,
        final_title,
        content.content,
        final_tags,
        content.schedule_time,
        content.is_original,
        content.visibility,
        location=content.location,
        content_type=content.content_type,
        allow_duet=content.allow_duet,
        allow_copy=content.allow_copy,
        collection=content.collection,
    )
    logger.info("文字配图表单填写完成，等待确认发布")


def publish_text2image_content(page: Page, content: PublishImageContent) -> None:
    """发布图文-文字配图内容。"""
    fill_text2image_form(page, content)
    click_publish_button(page)


def fill_publish_form(page: Page, content: PublishImageContent) -> None:
    """填写图文发布表单，不点击发布按钮。

    Args:
        page: CDP 页面对象。
        content: 发布内容。

    Raises:
        PublishError: 填写失败。
        UploadTimeoutError: 上传超时。
        TitleTooLongError: 标题超长。
        ContentTooLongError: 正文超长。
    """
    if not content.image_paths:
        raise PublishError("图片不能为空")

    # 导航到发布页
    _navigate_to_publish_page(page)

    # 点击"上传图文" TAB
    _click_publish_tab(page, "上传图文")
    time.sleep(1)

    # 上传图片
    _upload_images(page, content.image_paths)

    tags = content.tags

    logger.info(
        "发布内容: title=%s, images=%d, tags=%d, schedule=%s, original=%s, visibility=%s",
        content.title,
        len(content.image_paths),
        len(tags),
        content.schedule_time,
        content.is_original,
        content.visibility,
    )

    # 填写表单（不点击发布）
    _fill_publish_form(
        page,
        content.title,
        content.content,
        tags,
        content.schedule_time,
        content.is_original,
        content.visibility,
        location=content.location,
        content_type=content.content_type,
        allow_duet=content.allow_duet,
        allow_copy=content.allow_copy,
        collection=content.collection,
    )


def input_publish_tags(page: Page, tags: list[str]) -> None:
    """在最终发布页补充话题标签。"""
    if not tags:
        return
    content_selector = _find_content_element(page)
    existing_text = page.get_element_text(content_selector) or ""
    normalized = [t.lstrip("#") for t in tags]
    pending = [t for t in normalized if f"#{t}" not in existing_text]
    if not pending:
        logger.info("发布页标签已存在，跳过重复补充")
        return
    _input_tags(page, content_selector, pending)
    logger.info("已补充 %d 个标签到发布页", len(pending))


def click_publish_button(page: Page, tags: list[str] | None = None) -> None:
    """点击发布按钮。

    Args:
        page: CDP 页面对象。
        tags: 可选，发布前在最终发布页补充的话题标签。

    Raises:
        PublishError: 点击失败。
    """
    if tags:
        input_publish_tags(page, tags)
        time.sleep(1)
    page.click_element(PUBLISH_BUTTON)
    time.sleep(3)
    logger.info("发布完成")


def save_as_draft(page: Page) -> None:
    """点击「暂存离开」按钮保存草稿。"""
    clicked = page.evaluate(
        """
        (() => {
            const buttons = document.querySelectorAll('button.custom-button');
            for (const btn of buttons) {
                if (btn.textContent.trim() === '暂存离开') {
                    btn.click();
                    return true;
                }
            }
            return false;
        })()
        """
    )
    if clicked:
        time.sleep(2)
        logger.info("已点击「暂存离开」，内容已保存到草稿箱")
    else:
        logger.warning("未找到「暂存离开」按钮")
        raise PublishError("未找到「暂存离开」按钮")


# ========== 页面导航 ==========


def _navigate_to_publish_page(page: Page) -> None:
    """导航到发布页面。"""
    page.navigate(PUBLISH_URL)
    page.wait_for_load(timeout=300)
    time.sleep(3)
    page.wait_dom_stable()
    time.sleep(2)


def _click_publish_tab(page: Page, tab_name: str) -> None:
    """点击发布页 TAB（上传图文/上传视频）。"""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        # 查找匹配的 TAB（支持多种结构）
        found = page.evaluate(
            f"""
            (() => {{
                // 策略1: 查找 div.creator-tab（过滤隐藏元素）
                let tabs = document.querySelectorAll({json.dumps(CREATOR_TAB)});
                for (const tab of tabs) {{
                    const titleSpan = tab.querySelector('span.title');
                    const tabText = titleSpan ? titleSpan.textContent.trim() : tab.textContent.trim();
                    if (tabText === {json.dumps(tab_name)}) {{
                        const rect = tab.getBoundingClientRect();
                        const style = window.getComputedStyle(tab);
                        // 跳过隐藏或被移出视口的元素
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.left < 0 || rect.top < 0) continue;
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        const x = rect.left + rect.width / 2;
                        const y = rect.top + rect.height / 2;
                        const target = document.elementFromPoint(x, y);
                        if (target === tab || tab.contains(target)) {{
                            tab.click();
                            return 'clicked';
                        }}
                        return 'blocked';
                    }}
                }}
                
                // 策略2: 查找任意包含目标文本的元素
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {{
                    if (el.children.length === 0 && el.textContent.trim() === {json.dumps(tab_name)}) {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.left < 0 || rect.top < 0) continue;
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        el.click();
                        return 'clicked';
                    }}
                }}
                
                return 'not_found';
            }})()
            """
        )

        if found == "clicked":
            return

        if found == "blocked":
            # 尝试移除弹窗
            _remove_pop_cover(page)

        time.sleep(0.2)

    # 调试：输出页面信息
    debug_info = page.evaluate("""
        (() => {
            const creatorTabs = document.querySelectorAll('div.creator-tab');
            const tabTexts = Array.from(creatorTabs).map(t => ({
                text: t.textContent.trim(),
                html: t.outerHTML.substring(0, 200)
            }));
            const url = window.location.href;
            return JSON.stringify({url, tabCount: creatorTabs.length, tabs: tabTexts});
        })()
    """)
    logger.error("调试信息: %s", debug_info)
    raise PublishError(f"没有找到发布 TAB - {tab_name}")


def _remove_pop_cover(page: Page) -> None:
    """移除弹窗遮挡。"""
    if page.has_element(POPOVER):
        page.remove_element(POPOVER)
    # 点击空位置
    x = 380 + random.randint(0, 100)
    y = 20 + random.randint(0, 60)
    page.mouse_click(float(x), float(y))


# ========== 图片上传 ==========


def _upload_images(page: Page, image_paths: list[str]) -> None:
    """逐张上传图片。"""
    import os

    valid_paths = [p for p in image_paths if os.path.exists(p)]
    if not valid_paths:
        raise PublishError("没有有效的图片文件")

    for i, path in enumerate(valid_paths):
        selector = UPLOAD_INPUT if i == 0 else FILE_INPUT
        logger.info("上传第 %d 张图片: %s", i + 1, path)

        page.set_file_input(selector, [path])
        _wait_for_upload_complete(page, i + 1)
        time.sleep(1)


def _wait_for_upload_complete(page: Page, expected_count: int) -> None:
    """等待图片上传完成。"""
    max_wait = 60.0
    start = time.monotonic()

    while time.monotonic() - start < max_wait:
        count = page.get_elements_count(IMAGE_PREVIEW)
        if count >= expected_count:
            logger.info("图片上传完成: %d", count)
            return
        time.sleep(0.5)

    raise UploadTimeoutError(f"第{expected_count}张图片上传超时(60s)")


# ========== 表单提交 ==========


def _sample_tags(tags: list[str]) -> list[str]:
    """从候选标签池中随机选取 3-6 个标签。

    - 不足 3 个时全部使用
    - 3-6 个时全部使用
    - 超过 6 个时随机选 3-6 个
    - 硬上限 10 个
    """
    if len(tags) <= 6:
        return tags[:10]
    count = random.randint(3, 6)
    selected = random.sample(tags, count)
    logger.info("从 %d 个候选标签中随机选取 %d 个: %s", len(tags), count, selected)
    return selected


def _extract_hashtags_from_content(content: str, tags: list[str]) -> tuple[str, list[str]]:
    """从正文末尾提取 hashtag 行，合并到 tags 列表。

    Returns:
        (cleaned_content, merged_tags)
    """
    lines = content.rstrip().split("\n")
    # 检查最后一行是否全是 #tag 格式
    if lines:
        last_line = lines[-1].strip()
        hashtag_pattern = re.compile(r"^(#\S+\s*)+$")
        if hashtag_pattern.match(last_line):
            # 提取 hashtag
            extracted = re.findall(r"#(\S+)", last_line)
            # 合并到 tags（去重）
            existing = {t.lstrip("#") for t in tags}
            merged = list(tags)
            for t in extracted:
                if t not in existing:
                    merged.append(t)
                    existing.add(t)
            # 去掉最后一行
            cleaned = "\n".join(lines[:-1]).rstrip()
            logger.info("从正文末尾提取 %d 个标签，合并后共 %d 个", len(extracted), len(merged))
            return cleaned, merged
    return content, list(tags)


def _fill_publish_form(
    page: Page,
    title: str,
    content: str,
    tags: list[str],
    schedule_time: str | None,
    is_original: bool,
    visibility: str,
    *,
    location: str = "",
    content_type: str = "",
    allow_duet: bool = True,
    allow_copy: bool = True,
    collection: str = "",
) -> None:
    """填写表单（不点击发布）。"""
    _fill_publish_form_common(
        page,
        title,
        content,
        tags,
        schedule_time,
        is_original,
        visibility,
        direct_content=False,
        location=location,
        content_type=content_type,
        allow_duet=allow_duet,
        allow_copy=allow_copy,
        collection=collection,
    )


def _fill_text2image_publish_form(
    page: Page,
    title: str,
    content: str,
    tags: list[str],
    schedule_time: str | None,
    is_original: bool,
    visibility: str,
    *,
    location: str = "",
    content_type: str = "",
    allow_duet: bool = True,
    allow_copy: bool = True,
    collection: str = "",
) -> None:
    """文字配图进入最终发布页后，直接覆盖标题/正文，避免残留提示词。"""
    _fill_publish_form_common(
        page,
        title,
        content,
        tags,
        schedule_time,
        is_original,
        visibility,
        direct_content=True,
        location=location,
        content_type=content_type,
        allow_duet=allow_duet,
        allow_copy=allow_copy,
        collection=collection,
    )


def _fill_publish_form_common(
    page: Page,
    title: str,
    content: str,
    tags: list[str],
    schedule_time: str | None,
    is_original: bool,
    visibility: str,
    *,
    direct_content: bool,
    location: str = "",
    content_type: str = "",
    allow_duet: bool = True,
    allow_copy: bool = True,
    collection: str = "",
) -> None:
    """填写发布表单公共逻辑。"""
    # 从正文末尾提取 hashtag 并合并到 tags
    content, tags = _extract_hashtags_from_content(content, tags)
    # 随机选取 3-6 个标签（传入的视为候选池），最多不超过 10
    tags = _sample_tags(tags)

    # 标题——填写前先校验长度，超限直接报错（由 AI 重新生成标题）
    from title_utils import calc_title_length

    title_len = calc_title_length(title)
    if title_len > 20:
        raise TitleTooLongError(str(title_len), "20")

    page.input_text(TITLE_INPUT, title)
    time.sleep(0.5)
    _check_title_max_length(page)
    logger.info("标题长度检查通过")
    time.sleep(1)

    # 正文
    content_selector = _find_content_element(page)
    if direct_content:
        _set_content_editable_direct(page, content_selector, content)
    else:
        page.input_content_editable(content_selector, content)

    # 回点标题（增强稳定性）
    time.sleep(1)
    page.click_element(TITLE_INPUT)
    logger.info("已回点标题输入框")

    # 标签
    if tags:
        _input_tags(page, content_selector, tags)
    time.sleep(1)
    _check_content_max_length(page)
    logger.info("正文长度检查通过")

    # 定时发布
    if schedule_time:
        _set_schedule_publish(page, schedule_time)

    # 可见范围
    _set_visibility(page, visibility)

    # 原创声明
    if is_original:
        try:
            _set_original(page)
            logger.info("已声明原创")
        except Exception as e:
            logger.warning("设置原创声明失败: %s", e)

    # 添加地点
    if location:
        try:
            _set_location(page, location)
        except Exception as e:
            logger.warning("设置地点失败: %s", e)

    # 内容类型声明
    if content_type:
        try:
            _set_content_type(page, content_type, location=location)
        except Exception as e:
            logger.warning("设置内容类型失败: %s", e)

    # 允许合拍
    if not allow_duet:
        try:
            _set_allow_duet(page, False)
        except Exception as e:
            logger.warning("设置允许合拍失败: %s", e)

    # 允许正文复制
    if not allow_copy:
        try:
            _set_allow_copy(page, False)
        except Exception as e:
            logger.warning("设置允许复制失败: %s", e)

    # 加入合集
    if collection:
        try:
            _set_collection(page, collection)
        except Exception as e:
            logger.warning("加入合集失败: %s", e)

    logger.info("表单填写完成，等待确认发布")


def _set_content_editable_direct(page: Page, selector: str, text: str) -> None:
    """直接覆盖 contentEditable 内容，适合文字配图发布页，避免残留生成提示词。"""
    lines = [line for line in text.splitlines()]
    ok = page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            const lines = {json.dumps(lines)};
            el.focus();
            el.innerHTML = '';
            if (!lines.length) {{
                const p = document.createElement('p');
                p.innerHTML = '<br>';
                el.appendChild(p);
            }} else {{
                for (const raw of lines) {{
                    const p = document.createElement('p');
                    if (raw) p.textContent = raw;
                    else p.innerHTML = '<br>';
                    el.appendChild(p);
                }}
            }}
            el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: null }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
    )
    if not ok:
        raise PublishError("未找到正文输入框")
    logger.info("已直接覆盖发布页正文（清除旧提示词）")


def _find_content_element(page: Page) -> str:
    """查找内容输入框（兼容两种 UI）。"""
    if page.has_element(CONTENT_EDITOR):
        return CONTENT_EDITOR

    # 查找带 placeholder 的 p 元素的 textbox 父元素
    found = page.evaluate(
        """
        (() => {
            const ps = document.querySelectorAll('p');
            for (const p of ps) {
                const placeholder = p.getAttribute('data-placeholder');
                if (placeholder && placeholder.includes('输入正文描述')) {
                    let current = p;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        if (current.getAttribute('role') === 'textbox') {
                            return 'found';
                        }
                    }
                }
            }
            return '';
        })()
        """
    )
    if found == "found":
        return "[role='textbox']"

    raise PublishError("没有找到内容输入框")


def _check_title_max_length(page: Page) -> None:
    """检查标题长度是否超限。"""
    text = page.get_element_text(TITLE_MAX_SUFFIX)
    if text:
        parts = text.split("/")
        if len(parts) == 2:
            raise TitleTooLongError(parts[0], parts[1])
        raise TitleTooLongError(text, "?")


def _check_content_max_length(page: Page) -> None:
    """检查正文长度是否超限。"""
    text = page.get_element_text(CONTENT_LENGTH_ERROR)
    if text:
        parts = text.split("/")
        if len(parts) == 2:
            raise ContentTooLongError(parts[0], parts[1])
        raise ContentTooLongError(text, "?")


# ========== 标签输入 ==========


def _input_tags(page: Page, content_selector: str, tags: list[str]) -> None:
    """输入标签。"""
    time.sleep(1)

    # 先点击正文编辑器，确保焦点在正文而非标题
    page.click_element(content_selector)
    time.sleep(0.3)

    # 移动光标到正文末尾（20次 ArrowDown）
    for _ in range(20):
        page.press_key("ArrowDown")
        time.sleep(0.01)

    # 按两次回车换行
    page.press_key("Enter")
    page.press_key("Enter")
    time.sleep(1)

    for tag in tags:
        tag = tag.lstrip("#")
        _input_single_tag(page, content_selector, tag)


def _input_single_tag(page: Page, content_selector: str, tag: str) -> None:
    """输入单个标签，优先匹配文本再点击（避免盲点第一个联想项）。"""
    # 输入 #
    page.type_text("#", delay_ms=0)
    time.sleep(0.3)

    # 逐字输入标签（随机间隔模拟真实输入）
    for char in tag:
        page.type_text(char, delay_ms=0)
        time.sleep(random.uniform(0.05, 0.12))

    # 等待标签联想并匹配文本（最多 4 秒）
    tag_lower = tag.lower()
    deadline = time.monotonic() + 4.0
    clicked = False
    while time.monotonic() < deadline:
        time.sleep(0.3)
        if not page.has_element(TAG_TOPIC_CONTAINER):
            continue

        clicked_tag = page.evaluate(
            f"""
            (() => {{
                const container = document.querySelector({json.dumps(TAG_TOPIC_CONTAINER)});
                if (!container) return null;
                const items = container.querySelectorAll('.item');
                if (!items.length) return null;

                const target = {json.dumps(tag_lower)};
                let bestMatch = null;

                for (const item of items) {{
                    const text = (item.textContent || '').trim().replace(/^#/, '').toLowerCase();
                    if (text === target) {{
                        item.click();
                        return text;
                    }}
                    if (!bestMatch && text.includes(target)) {{
                        bestMatch = item;
                    }}
                }}

                if (bestMatch) {{
                    bestMatch.click();
                    return (bestMatch.textContent || '').trim().replace(/^#/, '');
                }}

                items[0].click();
                return (items[0].textContent || '').trim().replace(/^#/, '');
            }})()
            """
        )
        if clicked_tag is not None:
            if clicked_tag.lower() == tag_lower:
                logger.info("点击标签联想: %s", tag)
            else:
                logger.warning("标签联想不精确: 期望 '%s', 实际 '%s'", tag, clicked_tag)
            clicked = True
            break

    if not clicked:
        logger.warning("未找到标签联想，直接输入空格: %s", tag)
        page.type_text(" ", delay_ms=0)

    time.sleep(0.8)


# ========== 定时发布 ==========


def _set_schedule_publish(page: Page, schedule_time: str) -> None:
    """设置定时发布。"""
    from datetime import datetime

    # 解析 ISO8601 时间
    try:
        dt = datetime.fromisoformat(schedule_time)
    except ValueError as e:
        raise PublishError(f"定时发布时间格式错误: {e}") from e

    # 点击定时发布开关
    page.click_element(SCHEDULE_SWITCH)
    time.sleep(0.8)

    # 设置日期时间
    datetime_str = dt.strftime("%Y-%m-%d %H:%M")
    page.select_all_text(DATETIME_INPUT)
    page.input_text(DATETIME_INPUT, datetime_str)
    time.sleep(0.5)

    logger.info("已设置定时发布: %s", datetime_str)


# ========== 可见范围 ==========


def _set_visibility(page: Page, visibility: str) -> None:
    """设置可见范围。"""
    if not visibility or visibility == "公开可见":
        logger.info("可见范围: 公开可见（默认）")
        return

    supported = {"仅自己可见", "仅互关好友可见"}
    if visibility not in supported:
        raise PublishError(
            f"不支持的可见范围: {visibility}，支持: 公开可见、仅自己可见、仅互关好友可见"
        )

    # 点击下拉框
    page.click_element(VISIBILITY_DROPDOWN)
    time.sleep(0.5)

    # 查找并点击目标选项
    clicked = page.evaluate(
        f"""
        (() => {{
            const opts = document.querySelectorAll({json.dumps(VISIBILITY_OPTIONS)});
            for (const opt of opts) {{
                if (opt.textContent.includes({json.dumps(visibility)})) {{
                    opt.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        raise PublishError(f"未找到可见范围选项: {visibility}")

    logger.info("已设置可见范围: %s", visibility)
    time.sleep(0.2)


# ========== 原创声明 ==========


def _set_original(page: Page) -> None:
    """设置原创声明。"""
    # 查找原创声明卡片并点击开关
    result = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(ORIGINAL_SWITCH_CARD)});
            for (const card of cards) {{
                if (!card.textContent.includes('原创声明')) continue;
                const sw = card.querySelector({json.dumps(ORIGINAL_SWITCH)});
                if (!sw) continue;
                const input = sw.querySelector('input[type="checkbox"]');
                if (input && input.checked) return 'already_on';
                sw.click();
                return 'clicked';
            }}
            return 'not_found';
        }})()
        """
    )

    if result == "already_on":
        logger.info("原创声明已开启")
        return

    if result == "not_found":
        raise PublishError("未找到原创声明选项")

    time.sleep(0.5)

    # 处理确认弹窗
    _confirm_original_declaration(page)


def _confirm_original_declaration(page: Page) -> None:
    """处理原创声明确认弹窗。"""
    time.sleep(0.8)

    # 勾选 checkbox
    page.evaluate(
        """
        (() => {
            const footers = document.querySelectorAll('div.footer');
            for (const footer of footers) {
                if (!footer.textContent.includes('原创声明须知')) continue;
                const cb = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                if (cb && !cb.checked) cb.click();
                return;
            }
        })()
        """
    )
    time.sleep(0.5)

    # 点击声明原创按钮
    result = page.evaluate(
        """
        (() => {
            const footers = document.querySelectorAll('div.footer');
            for (const footer of footers) {
                if (!footer.textContent.includes('声明原创')) continue;
                const btn = footer.querySelector('button.custom-button');
                if (btn) {
                    if (btn.classList.contains('disabled') || btn.disabled) {
                        const cb = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                        return 'button_disabled';
                    }
                    btn.click();
                    return 'clicked';
                }
            }
            return 'button_not_found';
        })()
        """
    )

    if result == "button_not_found":
        raise PublishError("未找到声明原创按钮")
    if result == "button_disabled":
        raise PublishError("声明原创按钮仍处于禁用状态")

    logger.info("已成功点击声明原创按钮")
    time.sleep(0.3)


# ========== 添加地点 ==========


def _set_location(page: Page, location: str) -> None:
    """搜索并选择地点。

    小红书的下拉选项通过 Vue teleport 渲染到 body 底部的 .d-popover 中，
    不在 .address-card-select 内部，因此需要在全局 popover 中查找。
    """
    if not location:
        return

    # 点击地点下拉框
    if not page.has_element(LOCATION_DROPDOWN):
        logger.warning("未找到地点选择器，跳过")
        return

    page.click_element(LOCATION_DROPDOWN)
    time.sleep(0.5)

    # 聚焦 input 并逐字输入（Vue 响应式需要真实键盘事件）
    if page.has_element(LOCATION_INPUT):
        page.evaluate(
            f"""
            (() => {{
                const input = document.querySelector({json.dumps(LOCATION_INPUT)});
                if (input) {{ input.focus(); input.value = ''; }}
            }})()
            """
        )
        time.sleep(0.2)
        page.type_text(location, delay_ms=100)
        time.sleep(2)  # 等待搜索结果加载

    # 在全局 popover 中查找地点选项（.option-name 精确匹配优先）
    clicked = page.evaluate(
        f"""
        (() => {{
            const popovers = document.querySelectorAll('body > .d-popover');
            for (const p of popovers) {{
                const items = p.querySelectorAll('.d-grid-item');
                if (items.length === 0) continue;
                // 检查是否是地点 popover（含 .option-name）
                if (!p.querySelector('.option-name')) continue;
                // 优先精确匹配 option-name
                for (const item of items) {{
                    const name = item.querySelector('.option-name');
                    if (name && name.textContent.trim() === {json.dumps(location)}) {{
                        item.click();
                        return true;
                    }}
                }}
                // 模糊匹配
                for (const item of items) {{
                    if (item.textContent.includes({json.dumps(location)})) {{
                        item.click();
                        return true;
                    }}
                }}
                // 选第一个
                if (items.length > 0) {{
                    items[0].click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if clicked:
        logger.info("已设置地点: %s", location)
    else:
        logger.warning("未找到地点选项: %s", location)
    time.sleep(0.3)


# ========== 内容类型声明 ==========


def _set_content_type(page: Page, content_type: str, location: str = "") -> None:
    """设置内容类型声明。

    选项通过 Vue teleport 渲染到 body 底部的 .d-popover 中。
    选择"自主拍摄"后会弹出对话框要求填写拍摄地点和日期。
    """
    if not content_type:
        return

    if not page.has_element(CONTENT_TYPE_DROPDOWN):
        logger.warning("未找到内容类型选择器，跳过")
        return

    page.click_element(CONTENT_TYPE_DROPDOWN)
    time.sleep(0.5)

    # 在全局 popover 中查找内容类型选项
    clicked = page.evaluate(
        f"""
        (() => {{
            const popovers = document.querySelectorAll('body > .d-popover');
            for (const p of popovers) {{
                const items = p.querySelectorAll('.d-grid-item');
                if (items.length === 0) continue;
                // 跳过地点 popover（含 .option-name）和可见范围 popover
                if (p.querySelector('.option-name')) continue;
                for (const item of items) {{
                    if (item.textContent.trim().includes({json.dumps(content_type)})) {{
                        item.click();
                        return true;
                    }}
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        logger.warning("未找到内容类型选项: %s", content_type)
        return

    logger.info("已点击内容类型: %s", content_type)
    time.sleep(0.8)

    # 处理"自主拍摄"弹窗（拍摄地点 + 拍摄日期）
    _handle_self_shooting_dialog(page, location)


def _handle_self_shooting_dialog(page: Page, location: str = "") -> None:
    """处理"自主拍摄"选项的确认弹窗。

    弹窗包含拍摄地点（el-autocomplete）和拍摄日期。
    如果没有弹窗则直接返回。
    """
    dialog_sel = ".d-modal-mask .self-shooting-contain"
    if not page.has_element(dialog_sel):
        return

    logger.info("检测到自主拍摄确认弹窗")

    if location:
        # 聚焦地点输入框并输入
        page.evaluate(
            """
            (() => {
                const input = document.querySelector('.self-shooting-contain input[placeholder="下拉选择地点"]');
                if (input) { input.focus(); input.value = ''; }
            })()
            """
        )
        time.sleep(0.3)
        page.type_text(location, delay_ms=100)
        time.sleep(1.5)

        # 选择第一个自动补全建议
        page.evaluate(
            """
            (() => {
                // el-autocomplete 的建议列表
                const suggestions = document.querySelectorAll('.el-autocomplete-suggestion li, .el-scrollbar .el-autocomplete-suggestion__list li');
                if (suggestions.length > 0) {
                    suggestions[0].click();
                    return;
                }
                // 备选：直接 popover 里找
                const popovers = document.querySelectorAll('.el-popper');
                for (const p of popovers) {
                    const items = p.querySelectorAll('li');
                    if (items.length > 0) { items[0].click(); return; }
                }
            })()
            """
        )
        time.sleep(0.5)

        # 拍摄日期——选今天
        page.evaluate(
            """
            (() => {
                const dateInput = document.querySelector('.self-shooting-contain input[placeholder="下拉选择日期"]');
                if (dateInput) dateInput.click();
            })()
            """
        )
        time.sleep(0.5)
        # 点击日期选择器中的"今天"或当前日期
        page.evaluate(
            """
            (() => {
                // 查找日期面板中的今天
                const today = document.querySelector('.d-date-panel .d-date-cell.is-today, .d-calendar-date.is-today');
                if (today) { today.click(); return; }
                // 或者点击高亮的当前日期
                const current = document.querySelector('.d-date-panel .d-date-cell.current, .d-calendar-date.current');
                if (current) { current.click(); return; }
            })()
            """
        )
        time.sleep(0.5)

        # 点击确认
        clicked = page.evaluate(
            """
            (() => {
                const mask = document.querySelector('.d-modal-mask');
                if (!mask) return false;
                const btns = mask.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.trim() === '确认' && !btn.disabled && !btn.classList.contains('disabled')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            })()
            """
        )

        if clicked:
            logger.info("已确认自主拍摄信息")
        else:
            logger.warning("确认按钮仍禁用，可能地点未选中，点击取消")
            _cancel_self_shooting_dialog(page)
    else:
        # 没有地点信息，直接取消弹窗
        logger.info("未提供拍摄地点，取消自主拍摄弹窗")
        _cancel_self_shooting_dialog(page)

    time.sleep(0.3)


def _cancel_self_shooting_dialog(page: Page) -> None:
    """关闭自主拍摄弹窗。"""
    page.evaluate(
        """
        (() => {
            const mask = document.querySelector('.d-modal-mask');
            if (!mask) return;
            const btns = mask.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.trim() === '取消') { btn.click(); return; }
            }
            // 备选：点关闭按钮
            const close = mask.querySelector('.d-modal-close');
            if (close) close.click();
        })()
        """
    )


# ========== 允许合拍 / 允许复制 ==========


def _set_switch_by_label(page: Page, label_text: str, enabled: bool) -> None:
    """通过标签文本查找 switch 并设置状态。

    Args:
        page: CDP 页面对象。
        label_text: switch 旁的标签文本，如 "允许他人合拍" 或 "允许正文复制"。
        enabled: True=开启, False=关闭。
    """
    result = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll('div.custom-switch-card, div.switch-card, div[class*="switch"]');
            for (const card of cards) {{
                if (!card.textContent.includes({json.dumps(label_text)})) continue;
                const sw = card.querySelector('div.d-switch');
                if (!sw) continue;
                const input = sw.querySelector('input[type="checkbox"]');
                if (!input) continue;
                const isOn = input.checked;
                if (isOn === {json.dumps(enabled)}) return 'already_set';
                sw.click();
                return 'clicked';
            }}
            return 'not_found';
        }})()
        """
    )

    if result == "already_set":
        logger.info("%s 已处于目标状态(%s)", label_text, "开" if enabled else "关")
    elif result == "clicked":
        logger.info("已设置 %s: %s", label_text, "开" if enabled else "关")
        time.sleep(0.3)
    else:
        logger.warning("未找到 %s 开关", label_text)


def _set_allow_duet(page: Page, allow: bool) -> None:
    """设置允许合拍。"""
    if allow:
        return  # 默认开启，无需操作
    _set_switch_by_label(page, "允许他人合拍", False)


def _set_allow_copy(page: Page, allow: bool) -> None:
    """设置允许正文复制。"""
    if allow:
        return  # 默认开启，无需操作
    _set_switch_by_label(page, "允许正文复制", False)


# ========== 加入合集 ==========


def _set_collection(page: Page, collection: str) -> None:
    """加入合集。"""
    if not collection:
        return

    if not page.has_element(COLLECTION_TRIGGER):
        logger.warning("未找到合集入口，跳过")
        return

    # 点击合集区域展开
    page.click_element(COLLECTION_TRIGGER)
    time.sleep(1)

    # 查找并选择已有合集，或提示创建
    clicked = page.evaluate(
        f"""
        (() => {{
            // 查找合集列表中的匹配项
            const items = document.querySelectorAll('.collection-plugin-content .collection-item, .collection-list .item');
            for (const item of items) {{
                if (item.textContent.trim().includes({json.dumps(collection)})) {{
                    item.click();
                    return 'selected';
                }}
            }}
            return 'not_found';
        }})()
        """
    )

    if clicked == "selected":
        logger.info("已加入合集: %s", collection)
    else:
        logger.warning("未找到合集: %s，请先在小红书创建该合集", collection)
    time.sleep(0.3)
