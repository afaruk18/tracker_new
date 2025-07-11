from __future__ import annotations

from typing import List, Sequence

from sqlalchemy import text
from sqlmodel import select

from tracker.db.connect import get_session
from tracker.tables.adk_query_table import AdkQuery


class QueryStore:
    """High-level helper for persisting and re-using *AdkQuery* records.

    Provides convenience methods for:
    1. Saving or updating queries with an optional set of tags.
    2. Searching previously saved queries by *name* and/or *tags*.
    3. Loading a query and executing it directly against the database.
    """

    # ---------------------------------------------------------------------
    # Save / update helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def save_query(name: str, query: str, tags: str | Sequence[str] | None = None) -> AdkQuery:
        """Create or update a saved ADK query.

        If a query with the same *name* already exists it will be **updated** –
        the SQL text and tags are overwritten with the supplied values.  This
        makes *name* behave like an *upsert* key that callers can rely on.

        Args:
            name: Unique, human-readable identifier for the query.
            query: Raw ADK/SQL string.
            tags: Either a comma-separated string ("foo,bar") **or** an
                  iterable of strings ("foo", "bar").
        Returns:
            The *AdkQuery* instance that was written to the database.
        """
        # Normalise *tags* to a comma-separated string for storage
        if tags is None:
            tag_str: str | None = None
        elif isinstance(tags, str):
            # Clean up whitespace and duplicate commas
            tag_str = ",".join(filter(None, (t.strip() for t in tags.split(","))))
        else:
            tag_str = ",".join(str(t).strip() for t in tags)

        with get_session() as session:
            existing = session.exec(select(AdkQuery).where(AdkQuery.name == name)).first()

            if existing:
                existing.query = query
                existing.tags = tag_str
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                new_row = AdkQuery(name=name, query=query, tags=tag_str)
                session.add(new_row)
                session.commit()
                session.refresh(new_row)
                return new_row

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _tags_filter(tag_list: Sequence[str]):
        """Build a *where* clause that matches any of *tag_list* (case-insensitive)."""
        # Use ILIKE with wildcards – this keeps it simple without requiring FTS.
        from sqlalchemy import or_, func

        filters = [func.lower(AdkQuery.tags).ilike(f"%{t.lower()}%") for t in tag_list]
        return or_(*filters)

    @staticmethod
    def find_queries(name: str | None = None, tags: Sequence[str] | None = None) -> List[AdkQuery]:
        """Search saved queries by *name* and/or *tags*.

        The search is *case-insensitive* and matches partial names ("report" will
        match "Weekly Report").  Tag filters are applied with **OR** semantics –
        a query is returned if *any* of the supplied tags match.
        """
        stmt = select(AdkQuery)

        # Apply name filter
        if name:
            from sqlalchemy import func

            stmt = stmt.where(func.lower(AdkQuery.name).ilike(f"%{name.lower()}%"))

        # Apply tags filter
        if tags:
            stmt = stmt.where(QueryStore._tags_filter(tags))

        with get_session() as session:
            return list(session.exec(stmt))

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------
    @staticmethod
    def run_query(name: str) -> List[dict]:
        """Load a saved query by *name* and execute it.

        Args:
            name: The unique *name* of the previously saved query.
        Returns:
            A list of dictionaries representing the result set rows.
        Raises:
            ValueError: If no query with the specified *name* exists.
        """
        with get_session() as session:
            row = session.exec(select(AdkQuery).where(AdkQuery.name == name)).first()
            if row is None:
                raise ValueError(f"No saved query found with name '{name}'.")

            result = session.exec(text(row.query)).mappings().all()
            return [dict(r) for r in result]