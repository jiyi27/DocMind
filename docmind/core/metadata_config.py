"""Metadata configuration for document ingestion.

Defines the allowed values for each metadata field.
To add new values, simply extend the lists below.
"""

from __future__ import annotations

BUSINESS_LINES: list[str] = [
    "india",
    "pakistan",
    "all",
]

DOC_TYPES: list[str] = [
    "requirement",   # 需求文档
    "postmortem",    # 线上问题复盘
    "pitfall",       # 踩坑记录
    "sharing",       # 个人分享
    "tech_spec",     # 技术规范
]

SERVICES: list[str] = [
    "collection",    # 催收系统
    "risk",          # 风控系统
    "admin",         # 管理后台
    "all",
]

DEPARTMENTS: list[str] = [
    "backend",
    "qa",
    "ios",
    "android",
    "web",
    "all",
]
