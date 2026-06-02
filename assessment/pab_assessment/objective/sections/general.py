"""General Observation — 01 Objective Examination."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import MultiSelectGroup, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets — labels ≤ 6 chars (border: none gives full 6 chars)
# ---------------------------------------------------------------------------

_SEV4  = [("Norm",  "success"), ("Mild",   "warning"), ("Mod",    "error"),   ("Sev",   "error")]
_LORD3 = [("Norm",  "success"), ("↑Inc",   "warning"), ("↓Dec",   "warning")]
_KYPH3 = [("Norm",  "success"), ("↑Inc",   "warning"), ("↓Dec",   "warning")]
_LEAN4 = [("None",  "success"), ("Left",   "warning"), ("Right",  "warning"), ("Fwd",   "default")]
_BRTH4 = [("Norm",  "success"), ("Apical", "warning"), ("Abdo",   "warning"), ("Paradx","error")]
_SCAP5 = [("Norm",  "success"), ("Prot",   "warning"), ("Retr",   "warning"), ("Elev",  "warning"), ("Depr", "warning")]
_GAIT2 = [("Norm",  "success"), ("Antlg",  "warning")]
_SLS4  = [("<1s",   "error"),   ("<5s",    "warning"), ("<10s",   "warning"), ("Norm",  "success")]
_STS4  = [("Norm",  "success"), ("Hand",   "warning"), ("Reduc",  "warning"), ("Unabl", "error")]


# ---------------------------------------------------------------------------
# GeneralSection
# ---------------------------------------------------------------------------

class GeneralSection(BaseSection):
    """01 General Observation — physical stats, posture, functional movement."""

    _nav_include_inputs = True  # include Input (stats) in arrow-key nav candidates

    class FieldChanged(Message):
        pass

    # (row label, data-key, gang options)
    _POSTURE_ROWS: list[tuple[str, str, list]] = [
        ("Lumbar lordosis",   "go_lx_lord", _LORD3),
        ("Thoracic kyphosis", "go_tx_kyph", _KYPH3),
        ("Antalgic lean",     "go_lean",    _LEAN4),
        ("Sway posture",      "go_sway",    _SEV4),
        ("Breathing",         "go_breath",  _BRTH4),
        ("Scapular L",        "go_scap_l",  _SCAP5),
        ("Scapular R",        "go_scap_r",  _SCAP5),
        ("Muscle wasting",    "go_wasting", _SEV4),
    ]
    _FUNCTIONAL_ROWS: list[tuple[str, str, list]] = [
        ("Gait",         "go_gait",  _GAIT2),
        ("SLS Left",     "go_sls_l", _SLS4),
        ("SLS Right",    "go_sls_r", _SLS4),
        ("Sit-to-stand", "go_sts",   _STS4),
    ]

    _INPUT_IDS = ()
    _TA_IDS    = ("go_general_notes", "go_transfer_cmt", "go_posture_notes", "go_functional_notes")

    DEFAULT_CSS = """
    GeneralSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    GeneralSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* Physical stats row */
    GeneralSection .stats_row   { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    GeneralSection .stats_lbl   { height: 3; content-align: right middle; padding: 0 1; }
    GeneralSection .stats_input { width: 10; height: 3; padding: 0 1; }
    GeneralSection .stats_unit  { width: 6;  height: 3; content-align: left middle; color: $text-muted; }

    /* Observation rows — label + gang + comment input */
    GeneralSection .obs_row   { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    GeneralSection .obs_label { width: 20; height: 3; content-align: left middle; }
    GeneralSection .obs_cmt   { height: 3; width: 1fr; }

    GeneralSection TextArea { width: 1fr; height: auto; min-height: 2; padding: 0 1; }
    GeneralSection Label    { height: auto; margin-top: 0; }

    /* General mobility inline row */
    GeneralSection .mob_row     { layout: horizontal; height: auto; width: 100%; margin-bottom: 0; }
    GeneralSection .mob_lbl     { width: 20; height: auto; content-align: left top; padding-top: 1; }
    GeneralSection .mob_row TextArea { width: 1fr; min-height: 2; }
    """

    def compose(self) -> ComposeResult:
        yield Label("01 General Observation", classes="section_title")

        # ── Physical ──────────────────────────────────────────────────────────
        yield Label("Physical", classes="subsection_header", id="go_physical")
        yield TextArea(id="go_general_notes", language="plain")
        with Horizontal(classes="mob_row"):
            yield Static("General mobility:", classes="mob_lbl")
            yield TextArea(id="go_transfer_cmt", language="plain")

        # ── Posture ───────────────────────────────────────────────────────────
        yield Label("Posture", classes="subsection_header", id="go_posture")
        for label, key, opts in self._POSTURE_ROWS:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_label")
                if key == "go_lean":
                    yield MultiSelectGroup(opts, id=key)
                else:
                    yield RadioGroup(opts, id=key)
                yield Input(id=f"{key}_cmt", classes="obs_cmt")
        yield Label("Posture notes:")
        yield TextArea(id="go_posture_notes", language="plain")

        # ── Functional Movement ───────────────────────────────────────────────
        yield Label("Functional Movement", classes="subsection_header", id="go_functional_movement")
        for label, key, opts in self._FUNCTIONAL_ROWS:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_label")
                yield RadioGroup(opts, id=key)
                yield Input(id=f"{key}_cmt", classes="obs_cmt")
        yield Label("Functional notes:")
        yield TextArea(id="go_functional_notes", language="plain")

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(MultiSelectGroup.Changed)
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
        for iid in self._INPUT_IDS:
            try:
                data[iid] = self.query_one(f"#{iid}", Input).value.strip()
            except Exception:
                data[iid] = ""
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for msg in self.query(MultiSelectGroup):
            data[msg.id] = msg.value
        for inp in self.query("Input.obs_cmt"):
            data[inp.id] = inp.value
        for tid in self._TA_IDS:
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for iid in self._INPUT_IDS:
                try:
                    self.query_one(f"#{iid}", Input).value = data.get(iid, "")
                except Exception:
                    pass
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for msg in self.query(MultiSelectGroup):
                msg.set_value(data.get(msg.id))
            for inp in self.query("Input.obs_cmt"):
                inp.value = data.get(inp.id, "")
            for tid in self._TA_IDS:
                try:
                    self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return bool(self.query_one("#go_general_notes", TextArea).text.strip())
        except Exception:
            return False
