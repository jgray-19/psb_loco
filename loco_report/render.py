"""PageSpec -> markdown. One figure emitter, one tab emitter, one table emitter."""

from __future__ import annotations

import os
from pathlib import Path


def figure(path: str, alt: str, caption: str, prefix: str) -> str:
    """A figure block. Alt text identifies; the caption labels. Never the same."""
    if alt.strip() == caption.strip():
        raise ValueError(f"alt text repeats the caption: {caption!r}")
    return (
        "<figure markdown>\n"
        f"![{alt}]({prefix}/{path})\n"
        f"<figcaption>{caption}</figcaption>\n"
        "</figure>"
    )


def prefix(figures: Path, page: Path) -> str:
    """Where *figures* sits from a page written at *page*, computed not hardcoded."""
    directory = page if page.suffix == "" else page.parent
    return os.path.relpath(figures, directory)


def indent(text: str, spaces: int = 4) -> str:
    """Indent a block for a content tab, leaving blank lines blank."""
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else "" for line in text.split("\n"))


def tabbed(blocks: dict[str, str]) -> str:
    """One content-tab group, {label: markdown}, in the order given."""
    parts: list[str] = []
    for label, body in blocks.items():
        if not body.strip():
            continue
        parts += [f'=== "{label}"', "", indent(body), ""]
    return "\n".join(parts)


def table(headings: list[str], rows: list[list[str]]) -> str:
    """A markdown table. Empty rows render as nothing rather than a bare header."""
    if not rows:
        return ""
    lines = [
        "| " + " | ".join(headings) + " |",
        "|" + "|".join("---" for _ in headings) + "|",
    ]
    lines += ["| " + " | ".join(cells) + " |" for cells in rows]
    return "\n".join(lines)


def heading(text: str, level: int = 2) -> str:
    return f"{'#' * level} {text}"


def page(title: str, statement: str, blocks: list[str]) -> str:
    """A whole page: title, one factual statement, then the blocks."""
    parts = [f"# {title}", statement.strip()]
    parts += [block.strip() for block in blocks if block.strip()]
    return "\n\n".join(parts).rstrip() + "\n"


def knob_table(results, page) -> str:
    """One row per case and family: knob count, rms, max, sigma, significance."""
    from loco_report.data import knob_statistics
    from loco_report.style import FAMILIES

    def number(value: float, digits: int = 2) -> str:
        return "—" if value != value else f"{value:.{digits}f}"

    rows: list[list[str]] = []
    for slug in results.valid(page.cases):
        frame = results.knobs(slug)
        label = page.label(slug)
        for suffix, family in FAMILIES.items():
            statistics = knob_statistics(frame, suffix)
            if statistics is None:
                continue
            determined = statistics["determined"]
            rows.append([
                label,
                # Escaped: an unescaped "[mm]" in a cell is a shortcut link.
                f"{family.word} \\[{family.unit}]",
                f"{statistics['knobs']:.0f} of {statistics['magnets']:.0f}",
                number(family.scale * statistics["rms"]),
                number(family.scale * statistics["max"]),
                number(family.scale * statistics["sigma"]),
                number(statistics["median_significance"]),
                "—" if determined != determined
                else f"{determined:.0f} of {statistics['magnets']:.0f}",
            ])
            label = ""
    return table(
        ["case", "family", "knobs", "rms", "max", "median $\\sigma$",
         "median $\\lvert v\\rvert/\\sigma$", "above 1"],
        rows,
    )
