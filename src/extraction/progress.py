from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import TextIO

TABLE_WIDTH = 34


def format_count(value: int, width: int = 0) -> str:
    return f"{value:>{width},}".replace(",", " ")


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ProgressDisplay:
    """Une ligne alignée, rafraîchie sur place pendant une extraction."""

    def __init__(
        self,
        table_name: str,
        *,
        stream: TextIO = sys.stderr,
        clock: Callable[[], float] = time.monotonic,
        refresh_interval: float = 0.2,
    ) -> None:
        self.table_name = table_name
        self.stream = stream
        self.clock = clock
        self.refresh_interval = refresh_interval
        self.started_at = clock()
        self.last_refresh = self.started_at - refresh_interval
        self.rows = 0

    def _line(self, now: float) -> str:
        return (
            f"{self.table_name:<{TABLE_WIDTH}} | "
            f"{format_count(self.rows, 10)} lignes | "
            f"{format_duration(now - self.started_at)}"
        )

    def update(self, page_rows: int, child_rows: int = 0) -> None:
        del child_rows
        self.rows += page_rows
        now = self.clock()
        if now - self.last_refresh < self.refresh_interval:
            return
        print(f"\r{self._line(now)}", end="", file=self.stream, flush=True)
        self.last_refresh = now

    def finish(self) -> float:
        now = self.clock()
        elapsed = now - self.started_at
        print(f"\r{self._line(now)}", file=self.stream, flush=True)
        return elapsed

    def abort(self) -> None:
        print(file=self.stream, flush=True)
