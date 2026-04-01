"""Transcript compaction helpers for long negotiation sessions."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TranscriptCompactor:
    """Summarize old transcript entries while preserving recent verbatim context."""

    compaction_threshold: int = 40
    keep_recent: int = 15

    def __post_init__(self) -> None:
        if self.keep_recent <= 0:
            raise ValueError("keep_recent must be greater than zero")
        if self.compaction_threshold <= self.keep_recent:
            raise ValueError("compaction_threshold must be greater than keep_recent")

    def compact(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return a compacted transcript when the threshold is exceeded."""

        if len(entries) <= self.compaction_threshold:
            return list(entries)

        recent_entries = [dict(entry) for entry in entries[-self.keep_recent :]]
        summary = self._build_summary(entries[:-self.keep_recent], recent_entries)
        return [summary, *recent_entries]

    def _build_summary(
        self,
        entries_to_compact: list[dict[str, Any]],
        recent_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        compacted_count = 0
        phase_counts: OrderedDict[str, int] = OrderedDict()
        phase_highlights: OrderedDict[str, str] = OrderedDict()

        for entry in entries_to_compact:
            if entry.get("kind") == "compaction_summary":
                data = entry.get("data") or {}
                compacted_count += int(data.get("compacted_count", 0))
                for phase, count in (data.get("phase_counts") or {}).items():
                    phase_counts[phase] = phase_counts.get(phase, 0) + int(count)
                for phase, highlight in (data.get("phase_highlights") or {}).items():
                    if highlight:
                        phase_highlights[phase] = str(highlight)
                continue

            compacted_count += 1
            phase = str(entry.get("phase") or "unknown")
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

            content = str(entry.get("content") or "").strip()
            if content:
                phase_highlights[phase] = self._truncate(content, 80)

        phases = list(phase_counts.keys())
        content = self._render_summary(compacted_count, phase_counts, phase_highlights)
        timestamp = (
            entries_to_compact[-1].get("timestamp")
            if entries_to_compact
            else (recent_entries[0].get("timestamp") if recent_entries else "")
        )

        return {
            "phase": "summary",
            "role": "system",
            "kind": "compaction_summary",
            "content": content,
            "timestamp": timestamp,
            "data": {
                "compacted_count": compacted_count,
                "phases": phases,
                "phase_counts": dict(phase_counts),
                "phase_highlights": dict(phase_highlights),
            },
        }

    def _render_summary(
        self,
        compacted_count: int,
        phase_counts: OrderedDict[str, int],
        phase_highlights: OrderedDict[str, str],
    ) -> str:
        sections = [
            f"Compacted {compacted_count} negotiation log entries.",
        ]
        for phase, count in phase_counts.items():
            highlight = phase_highlights.get(phase)
            line = f"{phase}: {count} entr"
            line += "y" if count == 1 else "ies"
            if highlight:
                line += f"; latest='{highlight}'"
            sections.append(line)
        return self._truncate(" ".join(sections), 480)

    # ------------------------------------------------------------------
    # History compaction (P3.3)
    # ------------------------------------------------------------------

    def compact_history(
        self,
        entries: list[dict[str, Any]],
        threshold: int = 60,
        keep_recent: int = 20,
    ) -> list[dict[str, Any]]:
        """Compact history entries by merging consecutive same-title runs.

        Only *consecutive* entries with the same ``title`` are merged.
        Non-consecutive duplicates are preserved as separate entries.
        The most recent ``keep_recent`` entries are always preserved verbatim.
        """
        if len(entries) <= threshold:
            return list(entries)

        if keep_recent > 0:
            to_compact = entries[:-keep_recent]
            recent = [dict(e) for e in entries[-keep_recent:]]
        else:
            to_compact = list(entries)
            recent = []

        merged = self._merge_consecutive(to_compact)
        return merged + recent

    @staticmethod
    def _merge_consecutive(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge consecutive runs of same-title history entries."""
        if not entries:
            return []

        result: list[dict[str, Any]] = []
        run_start = entries[0]
        run_count = 1
        run_last = entries[0]

        for entry in entries[1:]:
            if entry.get("title") == run_start.get("title"):
                run_count += 1
                run_last = entry
            else:
                result.append(
                    _build_merged(run_start, run_last, run_count)
                    if run_count >= 2
                    else dict(run_start)
                )
                run_start = entry
                run_last = entry
                run_count = 1

        result.append(
            _build_merged(run_start, run_last, run_count)
            if run_count >= 2
            else dict(run_start)
        )
        return result

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."


def _build_merged(
    first: dict[str, Any], last: dict[str, Any], count: int
) -> dict[str, Any]:
    """Create a merged history entry from a run of consecutive same-title entries."""
    return {
        "timestamp": last.get("timestamp", ""),
        "first_timestamp": first.get("timestamp", ""),
        "last_timestamp": last.get("timestamp", ""),
        "title": first.get("title", ""),
        "detail": last.get("detail", ""),
        "count": count,
    }
