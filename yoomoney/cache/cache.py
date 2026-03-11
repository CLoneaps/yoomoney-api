"""History cache — store operation history locally to reduce API calls.

Two backends are available:

* :class:`SQLiteCache` — persistent SQLite database (recommended for production).
* :class:`JSONCache` — simple JSON file (handy for scripts / debugging).

Both implement the same :class:`BaseCache` interface.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from yoomoney.operation.operation import Operation

logger = logging.getLogger(__name__)

_DT_FMT = "%Y-%m-%dT%H:%M:%S"


def _op_to_dict(op: Operation) -> dict[str, Any]:
    return op.model_dump(mode="json")


def _dict_to_op(data: dict[str, Any]) -> Operation:
    return Operation.model_validate(data)





class BaseCache(ABC):
    """Common interface for all cache backends."""

    @abstractmethod
    def save(self, operations: list[Operation]) -> None:
        """Persist *operations* to the cache (upsert by operation_id)."""

    @abstractmethod
    def load(
        self,
        label: str | None = None,
        from_date: datetime | None = None,
        till_date: datetime | None = None,
    ) -> list[Operation]:
        """Load operations from the cache, optionally filtered."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all cached data."""

    def is_fresh(self, max_age: timedelta) -> bool:
        """Return ``True`` if the cache was updated within *max_age*.

        Sub-classes may override this for more precise tracking.
        Default implementation always returns ``False`` (forces a refresh).
        """
        return False





class SQLiteCache(BaseCache):
    """Persistent cache backed by a local SQLite database."""
    
    def __init__(self, path: str | Path = "yoomoney_cache.db") -> None:
        self.path = Path(path)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    status       TEXT,
                    datetime     TEXT,
                    title        TEXT,
                    pattern_id   TEXT,
                    direction    TEXT,
                    amount       REAL,
                    label        TEXT,
                    type         TEXT,
                    cached_at    TEXT NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_label    ON operations (label)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_datetime ON operations (datetime)")


    def save(self, operations: list[Operation]) -> None:
        now = datetime.now(tz=timezone.utc).strftime(_DT_FMT)
        with self._conn:
            for op in operations:
                d = _op_to_dict(op)
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO operations
                        (operation_id, status, datetime, title, pattern_id,
                         direction, amount, label, type, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.get("operation_id"),
                        d.get("status"),
                        d.get("datetime"),
                        d.get("title"),
                        d.get("pattern_id"),
                        d.get("direction"),
                        d.get("amount"),
                        d.get("label"),
                        d.get("type"),
                        now,
                    ),
                )
        logger.debug("Saved %d operations to SQLite cache", len(operations))

    def load(
        self,
        label: str | None = None,
        from_date: datetime | None = None,
        till_date: datetime | None = None,
    ) -> list[Operation]:
        query = "SELECT operation_id, status, datetime, title, pattern_id, direction, amount, label, type FROM operations WHERE 1=1"
        params: list[Any] = []

        if label is not None:
            query += " AND label = ?"
            params.append(label)
        if from_date is not None:
            query += " AND datetime >= ?"
            params.append(from_date.strftime(_DT_FMT))
        if till_date is not None:
            query += " AND datetime <= ?"
            params.append(till_date.strftime(_DT_FMT))

        query += " ORDER BY datetime DESC"

        cursor = self._conn.execute(query, params)
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        return [_dict_to_op(dict(zip(cols, row, strict=False))) for row in rows]

    def clear(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM operations")
        logger.info("SQLite cache cleared")

    def is_fresh(self, max_age: timedelta) -> bool:
        row = self._conn.execute("SELECT MAX(cached_at) FROM operations").fetchone()
        if row is None or row[0] is None:
            return False
        last = datetime.strptime(row[0], _DT_FMT).replace(tzinfo=timezone.utc)
        return (datetime.now(tz=timezone.utc) - last) <= max_age

    def close(self) -> None:
        self._conn.close()





class JSONCache(BaseCache):
    """Lightweight cache backed by a JSON file.

    Good for quick scripts. Not recommended for concurrent access.

    Parameters
    ----------
    path:
        Path to the ``.json`` file. Defaults to ``yoomoney_cache.json``.
    """

    def __init__(self, path: str | Path = "yoomoney_cache.json") -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = self._load_file()

    def _load_file(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("JSON cache corrupted, starting fresh: %s", self.path)
        return {"operations": {}, "updated_at": None}

    def _dump_file(self) -> None:
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


    def save(self, operations: list[Operation]) -> None:
        store: dict[str, Any] = self._data.setdefault("operations", {})
        for op in operations:
            d = _op_to_dict(op)
            key = d.get("operation_id") or str(id(op))
            store[key] = d
        self._data["updated_at"] = datetime.now(tz=timezone.utc).strftime(_DT_FMT)
        self._dump_file()
        logger.debug("Saved %d operations to JSON cache", len(operations))

    def load(
        self,
        label: str | None = None,
        from_date: datetime | None = None,
        till_date: datetime | None = None,
    ) -> list[Operation]:
        ops = [_dict_to_op(v) for v in self._data.get("operations", {}).values()]

        if label is not None:
            ops = [o for o in ops if o.label == label]
        if from_date is not None:
            ops = [o for o in ops if o.datetime is not None and o.datetime >= from_date]
        if till_date is not None:
            ops = [o for o in ops if o.datetime is not None and o.datetime <= till_date]

        ops.sort(key=lambda o: o.datetime or datetime.min, reverse=True)
        return ops

    def clear(self) -> None:
        self._data = {"operations": {}, "updated_at": None}
        self._dump_file()
        logger.info("JSON cache cleared")

    def is_fresh(self, max_age: timedelta) -> bool:
        updated_at = self._data.get("updated_at")
        if updated_at is None:
            return False
        last = datetime.strptime(updated_at, _DT_FMT).replace(tzinfo=timezone.utc)
        return (datetime.now(tz=timezone.utc) - last) <= max_age
