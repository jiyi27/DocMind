"""Sync planner — compares remote Confluence pages against local documents.

Produces a plan of create / update / delete operations without
performing any side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from docmind.integrations.confluence.client import PageSummary


class SyncJobSummary(BaseModel):
    """Persisted scan summary for a completed sync job.

    Stored as JSON in ``kb_sync_jobs.summary`` so the frontend can explain
    an empty records list (e.g. "42 pages scanned, all up to date").
    """

    scanned: int = 0
    unchanged: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0


@dataclass
class SyncPlan:
    """Result of comparing remote pages to local Confluence documents."""

    to_create: list[PageSummary] = field(default_factory=list)
    to_update: list[tuple[PageSummary, dict[str, Any]]] = field(default_factory=list)
    to_delete: list[dict[str, Any]] = field(default_factory=list)
    unchanged: list[PageSummary] = field(default_factory=list)

    @property
    def total_operations(self) -> int:
        return len(self.to_create) + len(self.to_update) + len(self.to_delete)

    def to_summary(self) -> SyncJobSummary:
        return SyncJobSummary(
            scanned=len(self.to_create)
            + len(self.to_update)
            + len(self.to_delete)
            + len(self.unchanged),
            unchanged=len(self.unchanged),
            created=len(self.to_create),
            updated=len(self.to_update),
            deleted=len(self.to_delete),
        )


def build_sync_plan(
    remote_pages: list[PageSummary],
    local_docs: list[dict[str, Any]],
) -> SyncPlan:
    """Compare remote Confluence pages against local docs to determine sync actions.

    Args:
        remote_pages: Flat list of page summaries from ``walk_page_tree``.
        local_docs: Local documents with ``source_type='confluence'`` from the DB.

    Returns:
        A ``SyncPlan`` with categorised operations.
    """
    plan = SyncPlan()

    # Index local docs by external_doc_id for O(1) lookup
    local_by_page_id: dict[str, dict[str, Any]] = {
        doc["external_doc_id"]: doc for doc in local_docs if doc.get("external_doc_id")
    }

    # Track which local docs are still present in the remote tree
    seen_local_ids: set[str] = set()

    for page in remote_pages:
        local_doc = local_by_page_id.get(page.page_id)
        if local_doc is None:
            plan.to_create.append(page)
        elif page.version > int(local_doc.get("source_version", 0)):
            plan.to_update.append((page, local_doc))
            seen_local_ids.add(page.page_id)
        else:
            plan.unchanged.append(page)
            seen_local_ids.add(page.page_id)

    # Pages that exist locally but are no longer in the remote subtree
    for page_id, doc in local_by_page_id.items():
        if page_id not in seen_local_ids:
            plan.to_delete.append(doc)

    return plan
