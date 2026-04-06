"""Markdown → XHS 长文编辑器 HTML 转换器。

将 Markdown 格式的稿件转换为小红书长文编辑器（TipTap/ProseMirror）能识别的 HTML。

支持的 Markdown 语法：
- # 一级标题 / ## 二级标题
- 1. 有序列表 / - 无序列表
- > 引用块
- 空行分段
- 📌 等 emoji 直接保留

注意：XHS 长文编辑器的 schema 不支持 bold/italic/underline marks，
所以 **加粗** *斜体* __下划线__ 会被当作纯文本保留（星号/下划线不移除）。
需要强调的内容应使用 ## 标题 或 > 引用块。
"""

from __future__ import annotations

import re


def markdown_to_xhs_html(text: str) -> str:
    """将 Markdown 文本转换为 XHS 长文编辑器的 HTML。

    Args:
        text: Markdown 格式的文本。

    Returns:
        适合 TipTap editor.commands.setContent() 的 HTML 字符串。
    """
    lines = text.strip().split("\n")
    html_parts: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行跳过（段落间距由编辑器控制）
        if not stripped:
            i += 1
            continue

        # 一级标题
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = _escape(stripped[2:].strip())
            html_parts.append(f"<h1>{title}</h1>")
            i += 1
            continue

        # 二级标题
        if stripped.startswith("## "):
            title = _escape(stripped[3:].strip())
            html_parts.append(f"<h2>{title}</h2>")
            i += 1
            continue

        # 三级标题 → 当作二级处理（XHS 只支持 h1/h2）
        if stripped.startswith("### "):
            title = _escape(stripped[4:].strip())
            html_parts.append(f"<h2>{title}</h2>")
            i += 1
            continue

        # 引用块（连续 > 行合并）
        if stripped.startswith("> "):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(_escape(lines[i].strip()[2:].strip()))
                i += 1
            quote_text = "<br>".join(quote_lines)
            html_parts.append(f"<blockquote><p>{quote_text}</p></blockquote>")
            continue

        # 有序列表（连续 数字. 行）
        if re.match(r"^\d+\.\s", stripped):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s", "", lines[i].strip())
                items.append(f"<li><p>{_escape(item_text)}</p></li>")
                i += 1
            html_parts.append(f"<ol>{''.join(items)}</ol>")
            continue

        # 无序列表（连续 - 或 * 行）
        if re.match(r"^[-*]\s", stripped):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s", lines[i].strip()):
                item_text = re.sub(r"^[-*]\s", "", lines[i].strip())
                items.append(f"<li><p>{_escape(item_text)}</p></li>")
                i += 1
            html_parts.append(f"<ul>{''.join(items)}</ul>")
            continue

        # 分隔线 (---, ===, ___) → 忽略，不生成任何元素
        if re.match(r"^[-=_]{3,}\s*$", stripped):
            i += 1
            continue

        # 普通段落
        html_parts.append(f"<p>{_escape(stripped)}</p>")
        i += 1

    return "".join(html_parts)


def _escape(text: str) -> str:
    """HTML 转义，保留 emoji。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
