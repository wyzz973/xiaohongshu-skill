"""发布质检模块：在发布前校验标题、正文、敏感词、Markdown 兼容性、重复。"""

from __future__ import annotations

import glob
import json
import os
import re

# ---------------------------------------------------------------------------
# 敏感词库
# ---------------------------------------------------------------------------
SENSITIVE_PATTERNS = [
    # 绝对化用语 (advertising law violations)
    "最好的", "第一", "唯一", "100%", "绝对", "完美无缺",
    # 引流敏感词
    "微信", "wx", "加我", "私聊", "v信", "威信",
    # 竞品引流
    "淘宝", "京东", "拼多多", "抖音",
]


# ---------------------------------------------------------------------------
# 单项检查
# ---------------------------------------------------------------------------
def check_title(title: str) -> list[str]:
    """检查标题质量。返回问题列表（空 = 通过）。"""
    issues: list[str] = []
    if not title or not title.strip():
        issues.append("标题为空")
        return issues

    # 小红书采用 UTF-16 加权：中文 2、ASCII 1
    weighted_len = sum(2 if ord(c) > 127 else 1 for c in title)
    if weighted_len > 40:  # ~20 个显示字符
        issues.append(f"标题过长 ({weighted_len}/40 加权字符)")

    if len(title) < 4:
        issues.append("标题过短（建议至少4个字）")

    return issues


def check_content(content: str) -> list[str]:
    """检查正文质量。"""
    issues: list[str] = []
    if not content or not content.strip():
        issues.append("正文为空")
        return issues

    if len(content) < 50:
        issues.append(f"正文过短 ({len(content)} 字，建议至少50字)")

    return issues


def check_sensitive(title: str, content: str) -> list[str]:
    """检查敏感词。返回命中列表。"""
    issues: list[str] = []
    text = (title + " " + content).lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.lower() in text:
            issues.append(f"敏感词: '{pattern}'")
    return issues


def check_markdown_compat(content: str, note_type: str) -> list[str]:
    """检查内容中的 Markdown 在目标类型是否能正常渲染。"""
    issues: list[str] = []
    if note_type in ("image", "text2image", "video"):
        if re.search(r"^#{1,3}\s", content, re.MULTILINE):
            issues.append(
                "非长文类型使用了 Markdown 标题（## ），建议改为纯文本或切换为长文"
            )
        if "**" in content:
            issues.append(
                "注意：小红书不支持 **加粗** 语法（长文也不支持），会原样显示"
            )
        if re.search(r"^>\s", content, re.MULTILINE):
            issues.append(
                "非长文类型使用了引用块（> ），建议改为纯文本或切换为长文"
            )

    if note_type == "long_article" and "**" in content:
        issues.append(
            "长文也不支持 **加粗** 语法，会原样显示。用 ## 标题替代强调"
        )

    return issues


def check_duplicate(title: str) -> list[str]:
    """检查近期是否有相似标题的已发布笔记。"""
    issues: list[str] = []
    pub_dir = os.path.join(
        os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
        "published",
    )
    if not os.path.isdir(pub_dir):
        return issues

    for f in sorted(glob.glob(os.path.join(pub_dir, "*.json")))[-20:]:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            pub_title = data.get("title", "")
            if pub_title and (
                pub_title == title or pub_title in title or title in pub_title
            ):
                issues.append(
                    f"与已发布笔记标题相似: '{pub_title}' ({os.path.basename(f)})"
                )
        except (json.JSONDecodeError, OSError):
            continue

    return issues


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def validate_publish(
    title: str, content: str, note_type: str = "long_article"
) -> dict:
    """执行全部质检。返回 {"pass": bool, "errors": [...], "warnings": [...]}。"""
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_title(title))
    errors.extend(check_content(content))

    sensitive = check_sensitive(title, content)
    if sensitive:
        warnings.extend(sensitive)

    compat = check_markdown_compat(content, note_type)
    if compat:
        warnings.extend(compat)

    dup = check_duplicate(title)
    if dup:
        warnings.extend(dup)

    return {
        "pass": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
