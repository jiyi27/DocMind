"""Metadata configuration for document ingestion.

Defines the allowed values for each metadata field.
To add new values, simply extend the lists below.
To make a field required, add its name to REQUIRED_FIELDS.

Note: BUSINESS_LINES has been removed — knowledge bases are now dynamic
entities managed via the /kb API and stored in the database.
"""

from __future__ import annotations

DOC_TYPES: list[str] = [
    "requirement",  # 需求文档
    "postmortem",  # 线上问题复盘
    "pitfall",  # 踩坑记录
    "sharing",  # 个人分享
    "tech_spec",  # 技术规范
    "all",
]

SERVICES: list[str] = [
    "collection",  # 催收系统
    "risk",  # 风控系统
    "admin",  # 管理后台
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

# -------------------------------------------------------
# 必填字段控制 — 在此集合中添加/删除字段名即可
# 可选值: "title", "url", "doc_type", "service", "department"
# Note: "business_line" has been removed — it is now derived from the user's JWT.
# -------------------------------------------------------
REQUIRED_FIELDS: set[str] = {
    "title",
    "url",
    "doc_type",
    "service",
    "department",
}
