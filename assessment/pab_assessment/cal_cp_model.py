"""CAL-CP (ICD-11 Chronic Pain Classification Algorithm) graph model.

Pure data/logic layer, no Textual imports, no UI concerns — mirrors logic.py's
convention. Ported from the standalone prototype at cal_cp/cal-cp-tui/app.py
(see cal_cp/cal-cp-history.md for the full build history of the graph itself).

Source: Korwisi et al. 2021, PAIN — Supplementary Digital Content 1
(ICD-11 Chronic Pain Classification Algorithm).

The canonical graph data now lives at data/cal-cp-trunk.json (copied from
cal_cp/cal-cp-trunk.json — that original stays the prototype/editing source;
future graph edits must be synced across both copies by hand).

Workup is the section's source of truth: unlike widget-backed sections,
DiagnosisSection.collect()/load() serialize/deserialize Workup objects
directly via to_dict()/from_dict(), since the walk state (path, current node,
intro answers) has no natural home in any single widget.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).parent / "data" / "cal-cp-trunk.json"


def _load_graph() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


GRAPH = _load_graph()
TRUNK = GRAPH["trunk"]
INTRO_FORM = GRAPH.get("intro_form", {})
APPENDIX = GRAPH.get("appendix", {})
NODES_BY_ID: dict[str, dict] = {n["id"]: n for n in TRUNK["nodes"]}
SHARED_NOTES: dict = TRUNK.get("shared_notes", {})
START_NODE = TRUNK["start_node"]
APPENDIX_BY_CODE: dict[str, dict] = {
    code: entry for entry in APPENDIX.get("entries", []) for code in entry.get("codes", [])
}
TEMPORAL_PATTERN_OPTIONS: list[dict] = next(
    (f["options"] for f in INTRO_FORM.get("chronic_pain_specifier", {}).get("fields", [])
     if f.get("id") == "temporal_pattern"),
    [],
)


def short(text: str, limit: int = 60) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_example_list(items: list, indent: int = 0) -> list[str]:
    """Flatten the appendix's nested example lists (e.g. "Entrapment" ->
    carpal tunnel/Morton's neuroma/pudendal syndrome) into indented bullet lines."""
    lines: list[str] = []
    for it in items or []:
        prefix = "  " * indent + "• "
        if isinstance(it, str):
            lines.append(prefix + it)
        else:
            lines.append(prefix + it["item"])
            lines.extend(render_example_list(it.get("sub_items"), indent + 1))
    return lines


def render_appendix_block(node: dict) -> str:
    """Contextual 'See examples (Appendix, page 41)' disclosure — pushed into
    the shared KB panel alongside notes/footnote text (Phase 3)."""
    refs = node.get("appendix_ref") or []
    if not refs:
        return ""
    seen: set[str] = set()
    blocks: list[str] = []
    for code in refs:
        entry = APPENDIX_BY_CODE.get(code)
        if not entry or entry["title"] in seen:
            continue
        seen.add(entry["title"])
        lines = [f"[b]{entry['title']}[/b] [dim](Appendix, p.41)[/dim]"]
        if entry.get("note"):
            lines.append(entry["note"])
        lines.extend(render_example_list(entry.get("examples")))
        for note_key, list_key in (
            ("other_factors_note", "other_factors"),
            ("crystal_depositions_note", "crystal_depositions"),
            ("autoimmune_autoinflammatory_note", "autoimmune_autoinflammatory"),
        ):
            if entry.get(note_key):
                lines.append(entry[note_key])
                lines.extend(render_example_list(entry.get(list_key)))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Workup model — one independent walk through the graph. Multiple can exist
# at once (one per pain site/area).
# ---------------------------------------------------------------------------


@dataclass
class PathStep:
    node_id: str
    answer: Optional[str]  # "yes" / "no" / None (action-half of a merged pair, or a plain continue step)
    merged: bool = False

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "answer": self.answer, "merged": self.merged}

    @classmethod
    def from_dict(cls, d: dict) -> "PathStep":
        return cls(node_id=d["node_id"], answer=d.get("answer"), merged=bool(d.get("merged", False)))


@dataclass
class Workup:
    id: str
    label: str
    intro_done: bool = False
    intro: dict = field(default_factory=dict)
    current_node_id: str = START_NODE
    path: list[PathStep] = field(default_factory=list)
    finished: bool = False
    result_summary: str = ""

    def current_node(self) -> dict:
        return NODES_BY_ID[self.current_node_id]

    def breadcrumb(self, markup: bool = True) -> str:
        """The full Yes/No decision path walked so far. markup=True (the
        Textual UI default) wraps answers in Rich colour tags; markup=False
        renders plain "(Yes)"/"(No)" suffixes instead, for plain-text/
        Markdown report output where Rich tags would show up literally."""
        if not self.path:
            return ""
        parts = []
        for step in self.path:
            node = NODES_BY_ID[step.node_id]
            label = short(node.get("text") or node.get("name") or "")
            if step.answer == "yes":
                parts.append(f"{label} [green]✔[/green]" if markup else f"{label} (Yes)")
            elif step.answer == "no":
                parts.append(f"{label} [red]✘[/red]" if markup else f"{label} (No)")
            elif label:
                parts.append(label)
        return "  →  ".join(p for p in parts if p)

    def result_or_progress_text(self) -> str:
        """One-line summary for reports: the finished result, or a
        description of the last node reached if the walk is incomplete."""
        if self.finished:
            return self.result_summary or "(finished, no result recorded)"
        if not self.intro_done:
            return "Not started"
        node = NODES_BY_ID.get(self.current_node_id)
        text = short((node.get("text") or node.get("name") or "")) if node else ""
        if not self.path:
            return f"Incomplete — at: {text}" if text else "Incomplete"
        return f"Incomplete — last reached: {text}" if text else "Incomplete"

    def answer(self, ans: str) -> None:
        node = self.current_node()
        nxt = merged_next_node(node)
        if nxt is not None:
            self.path.append(PathStep(node["id"], None, merged=True))
            self.path.append(PathStep(nxt["id"], ans, merged=True))
            self.current_node_id = nxt[ans]
        elif node["type"] == "decision":
            self.path.append(PathStep(node["id"], ans))
            self.current_node_id = node[ans]

    def can_continue(self) -> bool:
        """True if the current node has a single 'Continue' action onward — an
        unmerged action/goto step, or a non-leaf diagnosis that continues into a
        further grading/sub-typing level (e.g. the Finnerup grading chains)."""
        node = self.current_node()
        if is_answerable(node):
            return False
        if node["type"] in ("action", "goto", "diagnosis"):
            return bool(node.get("next"))
        return False

    def can_finish(self) -> bool:
        """True if the current node can end this workup — a leaf diagnosis, a
        diagnosis with `optional_continue` (can stop and code at this level even
        though it could continue further), or a terminal node."""
        node = self.current_node()
        if is_answerable(node):
            return False
        if node["type"] == "diagnosis":
            return bool(node.get("leaf")) or bool(node.get("optional_continue")) or not node.get("next")
        if node["type"] in ("terminal_no_diagnosis", "terminal_end"):
            return True
        return False

    def continue_step(self) -> None:
        node = self.current_node()
        self.path.append(PathStep(node["id"], None))
        self.current_node_id = node["next"]

    def go_back(self) -> None:
        if not self.path:
            return
        self.finished = False
        last = self.path.pop()
        if last.merged and self.path and self.path[-1].merged:
            pair = self.path.pop()
            self.current_node_id = pair.node_id
        else:
            self.current_node_id = last.node_id

    def restart(self) -> None:
        self.path.clear()
        self.current_node_id = START_NODE
        self.finished = False
        self.result_summary = ""

    def finish(self) -> None:
        node = self.current_node()
        if node["type"] == "diagnosis":
            summary = f'{node["code"]} — {node["name"]}'
        elif node["type"] == "terminal_no_diagnosis":
            summary = "No chronic pain"
        elif node["type"] == "terminal_end":
            summary = "END — all chronic pain already explained"
        else:
            return
        self.result_summary = summary
        self.finished = True

    # ------------------------------------------------------------------
    # Serialization — Workup is this section's source of truth, so collect()/
    # load() round-trip through these rather than reading/writing widgets.
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "intro_done": self.intro_done,
            "intro": dict(self.intro),
            "current_node_id": self.current_node_id,
            "path": [s.to_dict() for s in self.path],
            "finished": self.finished,
            "result_summary": self.result_summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Workup":
        return cls(
            id=d["id"],
            label=d.get("label", d["id"]),
            intro_done=bool(d.get("intro_done", False)),
            intro=dict(d.get("intro") or {}),
            current_node_id=d.get("current_node_id", START_NODE),
            path=[PathStep.from_dict(s) for s in d.get("path") or []],
            finished=bool(d.get("finished", False)),
            result_summary=d.get("result_summary", ""),
        )


def merged_next_node(node: dict) -> dict | None:
    if not node.get("merge_with_next"):
        return None
    nxt = NODES_BY_ID.get(node.get("next"))
    if nxt and nxt.get("type") == "decision":
        return nxt
    return None


def is_answerable(node: dict) -> bool:
    """True if this node accepts a Yes/No answer directly (a plain decision node,
    or an action node merged with the decision that immediately follows it —
    see n4+n5 / n28+n29)."""
    if node["type"] == "decision":
        return True
    return merged_next_node(node) is not None


# ---------------------------------------------------------------------------
# effective_view — resolves ANY node id (root, daughter, or grandchild) into a
# uniform description used by every box in the lookahead tree. This is what
# collapses a merged action+decision pair (e.g. n4+n5) into a single box with
# two lines of text, regardless of where in the tree it appears.
# ---------------------------------------------------------------------------


def effective_view(node_id: str) -> dict:
    node = NODES_BY_ID[node_id]
    nxt = merged_next_node(node)
    if nxt is not None:
        return {
            "raw_ids": [node_id, nxt["id"]],
            "texts": [node["text"], nxt["text"]],
            "criteria": nxt.get("criteria") or node.get("criteria"),
            "kind": "decision",
            "yes": nxt["yes"],
            "no": nxt["no"],
        }
    if node["type"] == "decision":
        return {
            "raw_ids": [node_id],
            "texts": [node["text"]],
            "criteria": node.get("criteria"),
            "kind": "decision",
            "yes": node["yes"],
            "no": node["no"],
        }
    if node["type"] == "diagnosis":
        return {
            "raw_ids": [node_id],
            "texts": [f'{node["code"]} — {node["name"]}'],
            "criteria": None,
            "kind": "diagnosis",
            "yes": None,
            "no": None,
            "next": node.get("next"),
        }
    if node["type"] in ("terminal_no_diagnosis", "terminal_end"):
        return {
            "raw_ids": [node_id],
            "texts": [node["text"]],
            "criteria": None,
            "kind": "terminal",
            "yes": None,
            "no": None,
        }
    return {
        "raw_ids": [node_id],
        "texts": [node.get("text", "")],
        "criteria": None,
        "kind": node["type"],
        "yes": None,
        "no": None,
        "next": node.get("next"),
    }


def render_notes_panel(workup: Workup) -> str:
    """Combined notes/appendix/footnote text for the current node — pushed into
    the shared KB panel (Ctrl+K) rather than a separate footnote-bar widget."""
    if not workup.intro_done:
        return "[dim](complete the intro form to begin)[/dim]"

    node = workup.current_node()
    nxt = merged_next_node(node)
    lines: list[str] = []

    for n in (node, nxt):
        if not n:
            continue
        ref = n.get("shared_note_ref")
        if ref and ref in SHARED_NOTES:
            lines.append(f"[b]Note[/b] ({n['id']}): {SHARED_NOTES[ref]['text']}")

    if node["type"] == "diagnosis":
        kp = node.get("known_parents")
        if kp:
            lines.append("[b]Known parents:[/b] " + "; ".join(kp))

    for n in (node, nxt):
        if not n:
            continue
        block = render_appendix_block(n)
        if block:
            lines.append(block)

    for n in (node, nxt):
        if n and n.get("footnote"):
            lines.append(f"[dim]note {n.get('footnote_ref', '')}:[/dim] {n['footnote']}")

    if not lines:
        lines.append("[dim](no additional notes for this step)[/dim]")

    return "\n\n".join(lines)


def render_hint(workup: Workup) -> str:
    if not workup.intro_done:
        return "[dim]Fill in the specifier, then press [/dim][b]Start decision trunk[/b]"
    if workup.finished:
        return "[b]Backspace[/b] revise last answer"
    node = workup.current_node()
    if is_answerable(node):
        return "[b]Y[/b] Yes   ·   [b]N[/b] No   ·   [b]Backspace[/b] back"
    can_c = workup.can_continue()
    can_f = workup.can_finish()
    if can_c and can_f:
        return "[b]Enter[/b] continue to next level   ·   [b]F[/b] stop, code as this level   ·   [b]Backspace[/b] back"
    if can_c:
        return "[b]Enter[/b] continue   ·   [b]Backspace[/b] back"
    return "[b]Enter[/b] finish this workup   ·   [b]Backspace[/b] back"
