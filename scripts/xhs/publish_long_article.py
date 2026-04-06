"""长文发布模式，参考 cdp_publish.py 的长文工作流。"""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

from .cdp import Page
from .errors import PublishError
from .publish import _click_publish_tab, _find_content_element, _navigate_to_publish_page
from .selectors import (
    AUTO_FORMAT_BUTTON_TEXT,
    CONTENT_EDITOR,
    LONG_ARTICLE_TITLE,
    NEW_CREATION_BUTTON_TEXT,
    NEXT_STEP_BUTTON_TEXT,
    TEMPLATE_CARD,
    TEMPLATE_TITLE,
)

logger = logging.getLogger(__name__)

# 等待常量
_AUTO_FORMAT_WAIT = 3.0
_TEMPLATE_WAIT_ROUNDS = 15
_PAGE_LOAD_WAIT = 3.0


def publish_long_article(
    page: Page,
    title: str,
    content: str,
    image_paths: list[str] | None = None,
    *,
    markdown: bool = False,
) -> list[str]:
    """长文发布：导航 → 点击写长文 → 新的创作 → 填写标题正文 → 一键排版。

    返回可用模板名称列表。

    Args:
        page: CDP 页面对象。
        title: 长文标题。
        content: 长文正文（段落用换行分隔）。
        image_paths: 可选的图片路径列表（插入编辑器）。

    Returns:
        可用模板名称列表。

    Raises:
        PublishError: 操作失败。
    """
    # 1. 导航到发布页
    _navigate_to_publish_page(page)

    # 2. 点击"写长文"TAB
    _click_publish_tab(page, "写长文")
    time.sleep(1)

    # 3. 点击"新的创作"
    _click_new_creation(page)

    # 4. 填写标题（textarea）
    _fill_long_title(page, title)

    # 5. 填写正文（TipTap 编辑器）
    #    如果是 markdown 模式，只填占位文本（避免模板提前分页），
    #    真正的格式化内容在 select_template 之后通过 upgrade_content_format() 注入
    if markdown:
        _fill_long_content(page, "占位内容，等待格式化注入")
    else:
        _fill_long_content(page, content)

    # 6. 可选：插入图片到编辑器
    if image_paths:
        _insert_images_to_editor(page, image_paths)

    # 7. 点击"一键排版"
    _click_auto_format(page)

    # 8. 等待模板加载并返回名称列表
    _wait_for_templates(page)
    template_names = get_template_names(page)
    logger.info("模板加载完成: %s", template_names)
    return template_names


def get_template_names(page: Page) -> list[str]:
    """获取当前可用的排版模板名称列表。

    Args:
        page: CDP 页面对象。

    Returns:
        模板名称列表。
    """
    names = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(TEMPLATE_CARD)});
            const names = [];
            for (const card of cards) {{
                const title = card.querySelector({json.dumps(TEMPLATE_TITLE)});
                names.push(title ? title.textContent.trim() : 'Template ' + names.length);
            }}
            return names;
        }})()
        """
    )
    return names or []


def upgrade_content_format(page: Page, markdown_content: str) -> bool:
    """在选模板后，将 Markdown 内容转为格式化 HTML 注入 TipTap 编辑器。

    必须在 select_template() 之后调用，此时 __editors 已初始化。

    Args:
        page: CDP 页面对象。
        markdown_content: Markdown 格式的原始内容。

    Returns:
        是否成功注入。
    """
    from .markdown_to_html import markdown_to_xhs_html

    html = markdown_to_xhs_html(markdown_content)
    ok = _fill_long_content_via_tiptap(page, html)
    if ok:
        logger.info("已升级内容格式 (Markdown→TipTap HTML)")
    else:
        logger.warning("格式升级失败，保持纯文本")
    return ok


def select_template(page: Page, template_name: str) -> bool:
    """选择指定名称的排版模板。

    Args:
        page: CDP 页面对象。
        template_name: 模板名称。

    Returns:
        是否成功选择。
    """
    clicked = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(TEMPLATE_CARD)});
            for (const card of cards) {{
                const title = card.querySelector({json.dumps(TEMPLATE_TITLE)});
                if (title && title.textContent.trim() === {json.dumps(template_name)}) {{
                    card.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if clicked:
        logger.info("已选择模板: %s", template_name)
        time.sleep(1)
    else:
        logger.warning("未找到模板: %s", template_name)

    return bool(clicked)


def click_next_and_fill_description(page: Page, description: str, tags: list[str] | None = None) -> None:
    """点击下一步，进入发布页并填写正文描述。

    注意：新版页面在选择模板后可能已经自动进入发布页，
    这时不再存在"下一步"按钮，应直接填写发布页描述。
    如果 description 超过 1000 字，应压缩到 800 字左右。

    标签通过描述框内 #tag 联想添加，不以纯文本写入描述。
    如果描述文本末尾包含 #tag，会自动提取合并到 tags 并从描述中移除。
    """
    # 安全兜底：从描述末尾提取 hashtag 合并到 tags，避免重复
    from .publish import _extract_hashtags_from_content
    description, merged_tags = _extract_hashtags_from_content(
        description, list(tags or [])
    )
    tags = merged_tags or tags

    already_in_publish_page = page.has_element(
        '.publish-page-publish-btn button.bg-red'
    )

    if not already_in_publish_page:
        try:
            _click_button_by_text(page, NEXT_STEP_BUTTON_TEXT)
            time.sleep(_PAGE_LOAD_WAIT)
        except PublishError:
            # 模板选择后页面可能已自动跳转到发布设置页
            cur_url = page.evaluate("window.location.href") or ""
            if "publish" in cur_url:
                logger.info(
                    "未找到'下一步'按钮但已在发布页，继续"
                )
            else:
                raise
    else:
        logger.info("已处于发布页，跳过'下一步'")

    content_selector = _find_content_element(page)

    if description:
        if len(description) > 1000:
            description = description[:800]
            logger.warning("描述超过1000字，已截断到800字")

        page.input_content_editable(content_selector, description)
        logger.info("已填写发布页描述")

    if tags:
        _input_tags_via_topic_button(
            page, tags, content_selector=content_selector,
        )


# ========== 内部辅助函数 ==========


def _click_new_creation(page: Page) -> None:
    """点击"新的创作"按钮。优先点击真实 button，兼容新版页面。"""
    clicked = page.evaluate(
        f"""
        (() => {{
            const selectors = [
                'button.new-btn',
                'button[class*="new-btn"]',
                'button',
                '[role="button"]',
                'span',
                'div',
                'a'
            ];

            for (const sel of selectors) {{
                const elems = document.querySelectorAll(sel);
                for (const el of elems) {{
                    const txt = (el.textContent || '').trim();
                    if (txt !== {json.dumps(NEW_CREATION_BUTTON_TEXT)}) continue;
                    const target = el.closest('button, [role="button"]') || el;
                    const rect = target.getBoundingClientRect();
                    const style = window.getComputedStyle(target);
                    if (rect.width === 0 || rect.height === 0) continue;
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    target.scrollIntoView({{block: 'center'}});
                    target.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )
    if not clicked:
        raise PublishError(f"未找到'{NEW_CREATION_BUTTON_TEXT}'按钮，页面结构可能已变化")
    time.sleep(2)
    page.wait_dom_stable()
    logger.info("已点击'新的创作'")


def _fill_long_title(page: Page, title: str) -> None:
    """填写长文标题（textarea，需使用 native setter）。"""
    page.wait_for_element(LONG_ARTICLE_TITLE, timeout=10)

    page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({json.dumps(LONG_ARTICLE_TITLE)});
            if (!el) return false;
            const nativeSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            el.focus();
            nativeSetter.call(el, {json.dumps(title)});
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
    )
    logger.info("已填写长文标题: %s", title[:20])
    time.sleep(0.5)


def _fill_long_content(page: Page, content: str, *, markdown: bool = False) -> None:
    """填写长文正文（TipTap/ProseMirror 编辑器）。

    Args:
        page: CDP 页面对象。
        content: 长文正文。如果 markdown=True，会先转换为 HTML。
        markdown: 是否将 content 当作 Markdown 解析并注入格式化 HTML。
    """
    if markdown:
        from .markdown_to_html import markdown_to_xhs_html

        html_content = markdown_to_xhs_html(content)
        ok = _fill_long_content_via_tiptap(page, html_content)
        if ok:
            logger.info("已填写长文正文 (%d 字, Markdown→TipTap)", len(content))
            time.sleep(1)
            return
        logger.warning("TipTap API 注入失败，回退到纯文本模式")

    # 纯文本模式（原有逻辑）
    prose_selector = 'div.tiptap.ProseMirror, div.ProseMirror'
    if page.has_element(prose_selector):
        safe_selector = json.dumps(prose_selector)
        safe_content = json.dumps(content)
        ok = page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({safe_selector});
                if (!el) return false;
                const text = {safe_content};
                const lines = text.split('\\n');
                el.focus();
                el.innerHTML = '';
                for (const line of lines) {{
                    const p = document.createElement('p');
                    if (line) p.textContent = line;
                    else p.innerHTML = '<br class="ProseMirror-trailingBreak">';
                    el.appendChild(p);
                }}
                el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: null }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }})()
            """
        )
        if ok:
            logger.info("已填写长文正文 (%d 字, ProseMirror)", len(content))
            time.sleep(1)
            return

    content_selector = CONTENT_EDITOR
    if not page.has_element(CONTENT_EDITOR):
        content_selector = _find_content_element(page)

    page.input_content_editable(content_selector, content)
    logger.info("已填写长文正文 (%d 字)", len(content))
    time.sleep(1)


def _fill_long_content_via_tiptap(page: Page, html: str) -> bool:
    """通过 TipTap editor.commands.setContent() 注入格式化 HTML。

    会遍历所有编辑器实例，在每个实例上设置内容，确保分页后的所有页面都被更新。
    """
    safe_html = json.dumps(html)
    result = page.evaluate(
        f"""
        (() => {{
            try {{
                const editorsRef = window.__editors;
                if (!editorsRef) return {{success: false, reason: 'no __editors'}};
                const editors = editorsRef._value || editorsRef.value;
                if (!editors) return {{success: false, reason: 'no value'}};

                // 遍历所有编辑器实例
                const keys = Object.keys(editors);
                let setCount = 0;
                for (const key of keys) {{
                    const editor = editors[key];
                    if (editor && editor.commands && typeof editor.commands.setContent === 'function') {{
                        editor.commands.setContent({safe_html});
                        setCount++;
                    }}
                }}
                return {{success: setCount > 0, editorsUpdated: setCount, totalEditors: keys.length}};
            }} catch(e) {{
                return {{success: false, reason: e.message}};
            }}
        }})()
        """
    )
    if isinstance(result, dict):
        logger.info("TipTap setContent: %s", result)
        return result.get("success", False)
    return bool(result)


def _insert_images_to_editor(page: Page, image_paths: list[str]) -> None:
    """将图片插入到编辑器中。"""
    for img_path in image_paths:
        file_uri = Path(img_path).resolve().as_uri()
        page.evaluate(
            f"""
            (() => {{
                const editor = document.querySelector({json.dumps(CONTENT_EDITOR)});
                if (!editor) return false;
                const img = document.createElement('img');
                img.src = {json.dumps(file_uri)};
                editor.appendChild(img);
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }})()
            """
        )
    logger.info("已插入 %d 张图片到编辑器", len(image_paths))
    time.sleep(1)


def _click_auto_format(page: Page) -> None:
    """点击"一键排版"按钮。"""
    _click_button_by_text(page, AUTO_FORMAT_BUTTON_TEXT)
    logger.info("已点击'一键排版'，等待模板加载...")
    time.sleep(_AUTO_FORMAT_WAIT)


def _wait_for_templates(page: Page) -> bool:
    """等待模板卡片出现。"""
    for _ in range(_TEMPLATE_WAIT_ROUNDS):
        count = page.get_elements_count(TEMPLATE_CARD)
        if count and count > 0:
            logger.info("发现 %d 个模板卡片", count)
            return True
        time.sleep(1)

    logger.warning("等待模板卡片超时")
    return False


def _input_tags_via_topic_button(
    page: Page,
    tags: list[str],
    content_selector: str | None = None,
) -> None:
    """在描述框中输入 #tag 触发联想弹窗添加标签（长文发布页专用）。

    在描述框末尾慢速输入 #标签名 并等待联想弹窗，点击联想结果。
    关键：必须先明确聚焦描述框（非标题框），且每字间隔足够长。
    """
    from .publish import _sample_tags
    from .selectors import TAG_FIRST_ITEM, TAG_TOPIC_CONTAINER

    tags = _sample_tags(tags)
    if not tags:
        return

    # 过滤含空格的标签（XHS 话题不支持空格，输入会导致编辑器异常）
    clean_tags = []
    for t in tags:
        t = t.strip().lstrip("#")
        if " " in t:
            logger.warning("标签含空格已跳过: %s", t)
            continue
        if t:
            clean_tags.append(t)
    tags = clean_tags
    if not tags:
        return

    # 明确聚焦描述框（非标题框）
    if not content_selector:
        content_selector = _find_content_element(page)
    page.click_element(content_selector)
    time.sleep(0.5)

    # 光标移到描述末尾
    for _ in range(20):
        page.press_key("ArrowDown")
        time.sleep(0.01)
    page.press_key("End")
    time.sleep(0.3)

    # 首个标签前换行
    page.press_key("Enter")
    time.sleep(0.3)

    added = 0
    for tag in tags:
        tag = tag.lstrip("#")

        # 重新确保焦点在描述框（防止被联想弹窗切走）
        page.click_element(content_selector)
        time.sleep(0.3)
        for _ in range(20):
            page.press_key("ArrowDown")
            time.sleep(0.01)
        page.press_key("End")
        time.sleep(0.2)

        # 输入 # 触发联想
        page.type_text("#", delay_ms=0)
        time.sleep(1.0)

        # 慢速逐字输入标签名（每字 250-400ms）
        for char in tag:
            page.type_text(char, delay_ms=0)
            time.sleep(random.uniform(0.25, 0.40))

        # 等待联想弹窗出现（最多 5 秒）
        deadline = time.monotonic() + 5.0
        clicked = False
        while time.monotonic() < deadline:
            time.sleep(0.5)
            if page.has_element(TAG_TOPIC_CONTAINER):
                item_selector = f"{TAG_TOPIC_CONTAINER} {TAG_FIRST_ITEM}"
                if page.has_element(item_selector):
                    page.click_element(item_selector)
                    logger.info("点击标签联想: %s", tag)
                    clicked = True
                    added += 1
                    break

        if not clicked:
            logger.warning("未找到标签联想: %s", tag)
            page.type_text(" ", delay_ms=0)

        time.sleep(random.uniform(0.8, 1.2))

    logger.info("共添加 %d/%d 个标签", added, len(tags))


def _click_button_by_text(page: Page, text: str) -> None:
    """通过文本内容查找并点击按钮（通用方法）。"""
    clicked = page.evaluate(
        f"""
        (() => {{
            const elems = document.querySelectorAll(
                'button, [role="button"], span, div, a, [class*="btn"]'
            );
            for (const el of elems) {{
                if (el.textContent.trim() === {json.dumps(text)}) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    el.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        raise PublishError(f"未找到'{text}'按钮，页面结构可能已变化")
