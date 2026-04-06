"""创作服务平台数据采集命令：笔记列表、仪表盘、粉丝画像。"""

from __future__ import annotations

import argparse

from common import connect, output


def cmd_list_my_notes(args: argparse.Namespace) -> None:
    """获取我的全部笔记及深度分析数据。"""
    from xhs.creator import list_my_notes

    browser, page = connect(args)
    try:
        data = list_my_notes(page)
        output(data)
    finally:
        browser.close()


def cmd_get_dashboard(args: argparse.Namespace) -> None:
    """获取账号总览仪表盘数据。"""
    from xhs.creator import get_dashboard

    browser, page = connect(args)
    try:
        data = get_dashboard(page)
        output(data)
    finally:
        browser.close()


def cmd_get_fans_profile(args: argparse.Namespace) -> None:
    """获取粉丝画像数据。"""
    from xhs.creator import get_fans_profile

    browser, page = connect(args)
    try:
        data = get_fans_profile(page)
        output(data)
    finally:
        browser.close()


def register_analytics_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册数据采集相关子命令。"""

    sub = subparsers.add_parser(
        "list-my-notes",
        help="获取我的全部笔记列表及深度分析数据（曝光/CTR/观看时长/涨粉）",
    )
    sub.set_defaults(func=cmd_list_my_notes)

    sub = subparsers.add_parser(
        "get-dashboard",
        help="获取账号总览（粉丝/曝光/涨粉趋势/账号诊断）",
    )
    sub.set_defaults(func=cmd_get_dashboard)

    sub = subparsers.add_parser(
        "get-fans-profile",
        help="获取粉丝画像（性别/年龄/兴趣/地域）",
    )
    sub.set_defaults(func=cmd_get_fans_profile)
