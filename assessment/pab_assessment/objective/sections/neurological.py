"""Neurological — 04 Objective Examination."""

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import CheckButton, FlagButton, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_REFLEX  = [("0 Absnt", "error"),   ("1+ Redu", "warning"), ("2+ Norm", "success"),
            ("3+ Hypr", "warning"), ("4+Clons",  "error")]   # 5 × 8 = 40 cols

_PLANTAR = [("Flexr","success"), ("Extnr",  "error")]        # 2 × 6 = 12 cols

_MYOTOME = [("5/5", "success"), ("4/5", "warning"), ("3/5", "warning"),
            ("2/5", "error"),   ("1/5", "error"),   ("0/5", "error")]  # 6 × 6 = 36 cols

_DERM    = [("Absent", "error"), ("↓Hypo",  "warning"),
            ("Normal", "success"), ("↑Hyper", "error")]      # 4 × 6 = 24 cols


# ---------------------------------------------------------------------------
# Row definitions — Upper Limb
# ---------------------------------------------------------------------------

_UL_REFLEX_ROWS: list[tuple[str, str, list]] = [
    ("Biceps   C5/6",  "nr_biceps",  _REFLEX),
    ("Brachiorad  C6", "nr_brad",    _REFLEX),
    ("Triceps  C7",    "nr_triceps", _REFLEX),
]
_UL_MYOTOME_ROWS: list[tuple[str, str, list]] = [
    ("C5  Shldr abd",  "nr_c5", _MYOTOME),
    ("C6  Wrist ext",  "nr_c6", _MYOTOME),
    ("C7  Elbow ext",  "nr_c7", _MYOTOME),
    ("C8  Finger flx", "nr_c8", _MYOTOME),
    ("T1  Finger abd", "nr_t1", _MYOTOME),
]
_UL_DERM_ROWS: list[tuple[str, str]] = [
    ("C5  Lat arm/delt",  "sn_c5"),
    ("C6  Thumb & index", "sn_c6"),
    ("C7  Middle finger", "sn_c7"),
    ("C8  Little/ulnar",  "sn_c8"),
    ("T1  Med forearm",   "sn_t1"),
]
_UL_ND_ROWS: list[tuple[str, str, bool]] = [
    ("ULNT1",  "nr_ulnt1",  False),
    ("ULNT2a", "nr_ulnt2a", False),
    ("ULNT3",  "nr_ulnt3",  False),
]

# ---------------------------------------------------------------------------
# Row definitions — Lower Limb
# ---------------------------------------------------------------------------

_REFLEX_ROWS: list[tuple[str, str, list]] = [
    ("Knee jerk  L3/4", "nr_knee",  _REFLEX),
    ("Ankle jerk  S1",  "nr_ankle", _REFLEX),
]
_MYOTOME_ROWS: list[tuple[str, str, list]] = [
    ("L2  Hip flex",   "nr_l2", _MYOTOME),
    ("L3  Knee ext",   "nr_l3", _MYOTOME),
    ("L4  Ankle DF",   "nr_l4", _MYOTOME),
    ("L5  GT ext/EHL", "nr_l5", _MYOTOME),
    ("S1  PF / evert", "nr_s1", _MYOTOME),
    ("S2  Ham / KF",   "nr_s2", _MYOTOME),
]
_DERM_ROWS: list[tuple[str, str]] = [
    ("L2  Ant thigh",    "sn_l2"),
    ("L3  Med knee",     "sn_l3"),
    ("L4  Med foot",     "sn_l4"),
    ("L5  Dorsum foot",  "sn_l5"),
    ("S1  Lat foot",     "sn_s1"),
    ("S2  Post thigh",   "sn_s2"),
]
_ND_ROWS: list[tuple[str, str, bool]] = [
    ("SLR",   "nr_slr",   True),
    ("Slump", "nr_slump", False),
    ("PKF",   "nr_pkf",   True),
]
_UMN_ITEMS: list[tuple[str, str]] = [
    ("Hyperreflexia",  "nr_umn_hyper"),
    ("Babinski +",     "nr_umn_bab"),
    ("Clonus",         "nr_umn_clonus"),
    ("Romberg +",      "nr_umn_romberg"),
    ("Coord impaired", "nr_umn_coord"),
    ("Hoffman's",      "nr_umn_hoffman"),
    ("Tromner",        "nr_umn_tromner"),
]

_GAP = 2   # char gap between adjacent gangs


# ---------------------------------------------------------------------------
# NeurologicalSection
# ---------------------------------------------------------------------------

class NeurologicalSection(BaseSection):
    """04 Neurological — reflexes, myotomes, dermatomes, neurodynamics, UMN signs."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    NeurologicalSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    NeurologicalSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* Reflex / myotome / dermatome L|R grid
       label=18  L-gang(auto)  gap=2  R-gang(auto)                          */
    NeurologicalSection .rm_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .rm_hdr_lbl { width: 18; }
    NeurologicalSection .rm_hdr_col { width: 1fr; text-align: center; }
    NeurologicalSection .rm_hdr_gap { width: 2; }
    NeurologicalSection .rm_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    NeurologicalSection .rm_lbl     { width: 18; height: 3; content-align: left middle; }
    NeurologicalSection .rm_gap     { width: 2;  height: 3; }

    /* Neurodynamics
       label=8  L-deg=6  gap=2  L-resp=30  gap=2  R-deg=6  gap=2  R-resp=30 */
    NeurologicalSection .nd_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .nd_hdr_lbl  { width: 8; }
    NeurologicalSection .nd_hdr_grp  { width: 38; text-align: center; text-style: bold; }
    NeurologicalSection .nd_hdr_gap  { width: 2; }
    NeurologicalSection .nd_sub      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .nd_sub_lbl  { width: 8; }
    NeurologicalSection .nd_sub_deg  { width: 6;  text-align: center; }
    NeurologicalSection .nd_sub_gap  { width: 2; }
    NeurologicalSection .nd_sub_resp { width: 30; text-align: center; }
    NeurologicalSection .nd_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    NeurologicalSection .nd_lbl      { width: 8;  height: 3; content-align: left middle; }
    NeurologicalSection .nd_deg      { width: 8;  height: 3; padding: 0 1; }
    NeurologicalSection .nd_gap      { width: 2;  height: 3; }
    NeurologicalSection .nd_resp     { width: 1fr; height: 3; padding: 0 1; }
    NeurologicalSection .nd_hdr_col  { width: 1fr; text-align: center; }

    /* Width-8 buttons for reflex gangs */
    NeurologicalSection .rg-w8 _RadioButton { width: 8; min-width: 8; max-width: 8; }

    /* UMN — FlagButtons fill equally across the row (CheckButton selector matches subclass) */
    NeurologicalSection .umn_row { layout: horizontal; height: 3; width: 100%; }
    NeurologicalSection .umn_row CheckButton {
        width: 1fr; height: 3; min-width: 0; margin: 0 1 0 0;
    }
    NeurologicalSection .umn_row CheckButton:last-of-type { margin: 0; }

    NeurologicalSection TextArea { height: auto; min-height: 2; max-height: 12; padding: 0 1; }
    NeurologicalSection Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("04 Neurological", classes="section_title")

        # ── Upper Limb — Reflexes ─────────────────────────────────────────────
        yield Label("Upper Limb — Reflexes", classes="subsection_header", id="nr_ul_reflexes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _UL_REFLEX_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l", classes="rg-w8")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r", classes="rg-w8")
        yield TextArea(id="nr_ul_reflex_notes", language="plain")

        # ── Upper Limb — Myotomes ─────────────────────────────────────────────
        yield Label("Upper Limb — Myotomes", classes="subsection_header", id="nr_ul_myotomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _UL_MYOTOME_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r")
        yield TextArea(id="nr_ul_myotome_notes", language="plain")

        # ── Upper Limb — Dermatomes ───────────────────────────────────────────
        yield Label("Upper Limb — Dermatomes", classes="subsection_header", id="nr_ul_dermatomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix in _UL_DERM_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(_DERM, id=f"{prefix}_l")
                yield Static("",       classes="rm_gap")
                yield RadioGroup(_DERM, id=f"{prefix}_r")
        yield TextArea(id="nr_ul_derm_notes", language="plain")

        # ── Upper Limb — Neurodynamics ────────────────────────────────────────
        yield Label("Upper Limb — Neurodynamics", classes="subsection_header", id="nr_ul_neurodynamics")
        with Horizontal(classes="nd_hdr"):
            yield Static("",      classes="nd_hdr_lbl")
            yield Static("Left",  classes="nd_hdr_col")
            yield Static("",      classes="nd_hdr_gap")
            yield Static("Right", classes="nd_hdr_col")
        for label, prefix, has_deg in _UL_ND_ROWS:
            with Horizontal(classes="nd_row"):
                yield Static(label, classes="nd_lbl")
                if has_deg:
                    yield Input(placeholder="°", id=f"{prefix}_l_deg", classes="nd_deg")
                    yield Static("", classes="nd_gap")
                yield Input(placeholder="Response", id=f"{prefix}_l_resp", classes="nd_resp")
                yield Static("", classes="nd_gap")
                if has_deg:
                    yield Input(placeholder="°", id=f"{prefix}_r_deg", classes="nd_deg")
                    yield Static("", classes="nd_gap")
                yield Input(placeholder="Response", id=f"{prefix}_r_resp", classes="nd_resp")
        yield TextArea(id="nr_ul_nd_notes", language="plain")

        # ── Lower Limb — Reflexes ─────────────────────────────────────────────
        yield Label("Lower Limb — Reflexes", classes="subsection_header", id="nr_reflexes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _REFLEX_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l", classes="rg-w8")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r", classes="rg-w8")
        yield TextArea(id="nr_ll_reflex_notes", language="plain")

        # ── Lower Limb — Myotomes ─────────────────────────────────────────────
        yield Label("Lower Limb — Myotomes", classes="subsection_header", id="nr_myotomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _MYOTOME_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r")
        yield TextArea(id="nr_ll_myotome_notes", language="plain")

        # ── Lower Limb — Dermatomes ───────────────────────────────────────────
        yield Label("Lower Limb — Dermatomes", classes="subsection_header", id="nr_dermatomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix in _DERM_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(_DERM, id=f"{prefix}_l")
                yield Static("",       classes="rm_gap")
                yield RadioGroup(_DERM, id=f"{prefix}_r")
        yield TextArea(id="nr_ll_derm_notes", language="plain")

        # ── Lower Limb — Neurodynamics ────────────────────────────────────────
        yield Label("Lower Limb — Neurodynamics", classes="subsection_header", id="nr_neurodynamics")
        with Horizontal(classes="nd_hdr"):
            yield Static("",      classes="nd_hdr_lbl")
            yield Static("Left",  classes="nd_hdr_col")
            yield Static("",      classes="nd_hdr_gap")
            yield Static("Right", classes="nd_hdr_col")
        for label, prefix, has_deg in _ND_ROWS:
            with Horizontal(classes="nd_row"):
                yield Static(label, classes="nd_lbl")
                if has_deg:
                    yield Input(placeholder="°", id=f"{prefix}_l_deg", classes="nd_deg")
                    yield Static("", classes="nd_gap")
                yield Input(placeholder="Response", id=f"{prefix}_l_resp", classes="nd_resp")
                yield Static("", classes="nd_gap")
                if has_deg:
                    yield Input(placeholder="°", id=f"{prefix}_r_deg", classes="nd_deg")
                    yield Static("", classes="nd_gap")
                yield Input(placeholder="Response", id=f"{prefix}_r_resp", classes="nd_resp")
        yield TextArea(id="nr_ll_nd_notes", language="plain")

        # ── UMN Signs ─────────────────────────────────────────────────────────
        yield Label("UMN Signs", classes="subsection_header", id="nr_umn")
        with Horizontal(classes="umn_row"):
            for label, uid in _UMN_ITEMS:
                yield FlagButton(label, id=uid)
        yield TextArea(id="nr_umn_notes", language="plain")

        # ── General Notes ─────────────────────────────────────────────────────
        yield Label("General Notes:")
        yield TextArea(id="nr_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation — up/down across reflex + myotome + dermatome rows
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # Upper limb — reflexes + myotomes (3-tuple)
        for _, prefix, _ in _UL_REFLEX_ROWS + _UL_MYOTOME_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)
        # Upper limb — dermatomes (2-tuple)
        for _, prefix in _UL_DERM_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)
        # Lower limb — reflexes + myotomes (3-tuple)
        for _, prefix, _ in _REFLEX_ROWS + _MYOTOME_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)
        # Lower limb — dermatomes (2-tuple)
        for _, prefix in _DERM_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._grid_pos[fid]
        target_row = row - 1 if event.key == "up" else row + 1
        if 0 <= target_row < len(self._grid):
            try:
                self.query_one(f"#{self._grid[target_row][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(CheckButton.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if not self._loading:
            self.post_message(self.FieldChanged())

    # ------------------------------------------------------------------
    # collect / load / is_complete
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for _, uid in _UMN_ITEMS:
            try:
                data[uid] = self.query_one(f"#{uid}", FlagButton).value
            except Exception:
                data[uid] = None
        for _, prefix, has_deg in _UL_ND_ROWS + _ND_ROWS:
            for side in ("l", "r"):
                if has_deg:
                    fid = f"{prefix}_{side}_deg"
                    try:
                        data[fid] = self.query_one(f"#{fid}", Input).value.strip()
                    except Exception:
                        data[fid] = ""
                fid = f"{prefix}_{side}_resp"
                try:
                    data[fid] = self.query_one(f"#{fid}", Input).value.strip()
                except Exception:
                    data[fid] = ""
        for fid in (
            "nr_ul_reflex_notes", "nr_ul_myotome_notes", "nr_ul_derm_notes", "nr_ul_nd_notes",
            "nr_ll_reflex_notes", "nr_ll_myotome_notes", "nr_ll_derm_notes", "nr_ll_nd_notes",
            "nr_umn_notes", "nr_notes",
        ):
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for _, uid in _UMN_ITEMS:
                try:
                    self.query_one(f"#{uid}", FlagButton).set_value(data.get(uid))
                except Exception:
                    pass
            for _, prefix, has_deg in _UL_ND_ROWS + _ND_ROWS:
                for side in ("l", "r"):
                    if has_deg:
                        fid = f"{prefix}_{side}_deg"
                        try:
                            self.query_one(f"#{fid}", Input).value = data.get(fid, "")
                        except Exception:
                            pass
                    fid = f"{prefix}_{side}_resp"
                    try:
                        self.query_one(f"#{fid}", Input).value = data.get(fid, "")
                    except Exception:
                        pass
            for fid in (
                "nr_ul_reflex_notes", "nr_ul_myotome_notes", "nr_ul_derm_notes", "nr_ul_nd_notes",
                "nr_ll_reflex_notes", "nr_ll_myotome_notes", "nr_ll_derm_notes", "nr_ll_nd_notes",
                "nr_umn_notes", "nr_notes",
            ):
                try:
                    self.query_one(f"#{fid}", TextArea).text = data.get(fid, "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#nr_knee_l", RadioGroup).value is not None
        except Exception:
            return False
