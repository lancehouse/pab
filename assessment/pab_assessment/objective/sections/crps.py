"""CRPS — 09 Objective: Budapest / Valencia diagnostic criteria + clinical measures."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import CheckButton, FlagButton, GridInput, RadioGroup


# ---------------------------------------------------------------------------
# Domain tables — (prefix, display_label, indicator_id, [(field_id, label), ...])
# ---------------------------------------------------------------------------

_SX_DOMAINS: list[tuple[str, str, str, list]] = [
    ("crps_sx_sens",  "Sensory",           "crps_sx_sens_ind",  [
        ("crps_sx_hyperesth",    "Hyperesthesia"),
        ("crps_sx_hyperalg",     "Hyperalgesia"),
        ("crps_sx_allodynia",    "Allodynia"),
    ]),
    ("crps_sx_vaso",  "Vasomotor",          "crps_sx_vaso_ind",  [
        ("crps_sx_temp_asymm",   "Temp asymm"),
        ("crps_sx_skin_colour",  "Skin colour"),
        ("crps_sx_colour_asymm", "Colour asymm"),
    ]),
    ("crps_sx_sudo",  "Sudomotor/Oedema",   "crps_sx_sudo_ind",  [
        ("crps_sx_oedema",       "Oedema"),
        ("crps_sx_sweat_chng",   "Sweat chng"),
        ("crps_sx_sweat_asymm",  "Sweat asymm"),
    ]),
    ("crps_sx_motor", "Motor/Trophic",      "crps_sx_motor_ind", [
        ("crps_sx_rom_dec",      "Decr ROM"),
        ("crps_sx_weakness",     "Weakness"),
        ("crps_sx_tremor",       "Tremor"),
        ("crps_sx_dystonia",     "Dystonia"),
        ("crps_sx_trophic",      "Trophic"),
    ]),
]

_SG_DOMAINS: list[tuple[str, str, str, list]] = [
    ("crps_sg_sens",  "Sensory",           "crps_sg_sens_ind",  [
        ("crps_sg_hyperalg_pp",  "Hyperalg PP"),
        ("crps_sg_allod_lt",     "Allod LT"),
        ("crps_sg_allod_press",  "Allod Pres"),
        ("crps_sg_allod_jt",     "Allod Joint"),
    ]),
    ("crps_sg_vaso",  "Vasomotor",          "crps_sg_vaso_ind",  [
        ("crps_sg_temp_asymm",   "Temp asymm"),
        ("crps_sg_skin_colour",  "Skin colour"),
        ("crps_sg_colour_asymm", "Colour asymm"),
    ]),
    ("crps_sg_sudo",  "Sudomotor/Oedema",   "crps_sg_sudo_ind",  [
        ("crps_sg_oedema",       "Oedema"),
        ("crps_sg_sweat_chng",   "Sweat chng"),
        ("crps_sg_sweat_asymm",  "Sweat asymm"),
    ]),
    ("crps_sg_motor", "Motor/Trophic",      "crps_sg_motor_ind", [
        ("crps_sg_rom_dec",      "Decr ROM"),
        ("crps_sg_weakness",     "Weakness"),
        ("crps_sg_tremor",       "Tremor"),
        ("crps_sg_dystonia",     "Dystonia"),
        ("crps_sg_trophic",      "Trophic"),
    ]),
]

_ALL_SX_IDS   = [fid for _, _, _, items in _SX_DOMAINS for fid, _ in items]
_ALL_SG_IDS   = [fid for _, _, _, items in _SG_DOMAINS for fid, _ in items]
_ALL_FLAG_IDS = ["crps_disp_pain"] + _ALL_SX_IDS + _ALL_SG_IDS + ["crps_no_alt_dx"]

# Laterality grid — rows × columns
_LAT_ROWS: list[str] = ["quick", "vanilla", "context", "abstract"]
_LAT_ROW_LABELS: dict[str, str] = {
    "quick":    "Quick",
    "vanilla":  "Vanilla",
    "context":  "Context",
    "abstract": "Abstract",
}
# (col_key, header_label, unit_suffix)
_LAT_COLS: list[tuple[str, str, str]] = [
    ("l_acc",   "L acc",   "%"),
    ("l_speed", "L speed", "s"),
    ("r_acc",   "R acc",   "%"),
    ("r_speed", "R speed", "s"),
]
_LAT_IDS = [
    f"crps_lat_{row}_{col}" for row in _LAT_ROWS for col, _, _ in _LAT_COLS
]

_ALL_TA_IDS = [
    "crps_disp_pain_notes", "crps_sx_notes", "crps_sg_notes",
    "crps_no_alt_dx_notes", "crps_subtype_notes", "crps_notes",
    "crps_tpd_notes", "crps_vis_notes", "crps_lat_notes",
]

_SUBTYPE_FULL: dict[str, str] = {
    "T-I":   "Type I — no discrete nerve injury",
    "T-II":  "Type II — confirmed discrete nerve injury; signs extend beyond nerve territory",
    "Remit": "CRPS with Remission of Some Features",
    "NOS":   "CRPS Not Otherwise Specified — never fully met criteria",
}

_SUBTYPE = [
    ("T-I",   "success"),
    ("T-II",  "warning"),
    ("Remit", "primary"),
    ("NOS",   "default"),
]


# ---------------------------------------------------------------------------
# CRPSSection
# ---------------------------------------------------------------------------

class CRPSSection(BaseSection):
    """09 CRPS — Budapest / Valencia diagnostic criteria + clinical measures."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    CRPSSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    CRPSSection .section_title  { text-style: bold; margin-bottom: 0; }
    CRPSSection .crps_subtitle  { color: $text-muted; margin-bottom: 1; }
    CRPSSection .crps_rule_desc { color: $text-muted; margin-bottom: 0; }

    /* Rule row: description label + single FlagButton */
    CRPSSection .crps_rule_row             { layout: horizontal; height: 3; width: 100%; }
    CRPSSection .crps_rule_lbl             { width: 1fr; height: 3; content-align: left middle; }
    CRPSSection .crps_rule_row FlagButton  { width: 20; height: 3; max-width: 25%; }

    /* Domain header: name + triggered indicator */
    CRPSSection .crps_domain_hdr { layout: horizontal; height: 1; width: 100%; margin-top: 1; }
    CRPSSection .crps_domain_lbl { width: 1fr; text-style: bold; }
    CRPSSection .crps_domain_ind { width: auto; text-align: right; }
    CRPSSection .crps_ind_on     { color: $success; }
    CRPSSection .crps_ind_off    { color: $text-muted; }

    /* Button row: flags fill equally */
    CRPSSection .crps_btn_row            { layout: horizontal; height: 3; width: 100%; }
    CRPSSection .crps_btn_row FlagButton { width: 1fr; height: 3; min-width: 0; }

    /* Criteria summary box */
    CRPSSection .crps_summary_box   {
        width: 100%;
        height: auto;
        padding: 1 2;
        border: solid $panel-darken-2;
        margin: 1 0;
    }
    CRPSSection .crps_summary_met   { border: solid $success; color: $success; }
    CRPSSection .crps_summary_unmet { border: solid $panel-darken-2; }

    /* Laterality table */
    CRPSSection .lat_hdr         { layout: horizontal; height: 1; width: 100%; margin-top: 1; }
    CRPSSection .lat_hdr_blank   { width: 10; }
    CRPSSection .lat_hdr_col     { width: 1fr; text-align: center; color: $text-muted; }
    CRPSSection .lat_row         { layout: horizontal; height: 3; width: 100%; }
    CRPSSection .lat_row_lbl     { width: 10; height: 3; content-align: left middle; }
    CRPSSection .lat_row GridInput { width: 1fr; height: 3; }

    CRPSSection TextArea { height: auto; min-height: 2; max-height: 12; padding: 0 1; }
    CRPSSection Label    { height: auto; margin-top: 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lat_grid: list[list[str]] = []
        self._lat_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("09 CRPS Assessment", classes="section_title")
        yield Static("Budapest / Valencia Clinical Criteria (IASP 2004 / 2021)", classes="crps_subtitle")

        # ── 1 · Disproportionate Pain ─────────────────────────────────────────
        yield Label("1 · Disproportionate Pain", classes="subsection_header", id="crps_disp")
        with Horizontal(classes="crps_rule_row"):
            yield Static("Continuing pain disproportionate to inciting event", classes="crps_rule_lbl")
            yield FlagButton("Confirmed", id="crps_disp_pain")
        yield TextArea(id="crps_disp_pain_notes", language="plain")

        # ── 2 · Symptoms ──────────────────────────────────────────────────────
        yield Label("2 · Symptoms  (Patient Reported)", classes="subsection_header", id="crps_sx")
        yield Static("Rule 2: ≥ 1 symptom reported in 3 or more of the 4 domains", classes="crps_rule_desc")
        for _, domain_lbl, ind_id, items in _SX_DOMAINS:
            with Horizontal(classes="crps_domain_hdr"):
                yield Static(domain_lbl, classes="crps_domain_lbl")
                yield Static("○  –", id=ind_id, classes="crps_domain_ind crps_ind_off")
            with Horizontal(classes="crps_btn_row"):
                for fid, flabel in items:
                    yield FlagButton(flabel, id=fid)
        yield TextArea(id="crps_sx_notes", language="plain")

        # ── 3 · Signs ─────────────────────────────────────────────────────────
        yield Label("3 · Signs  (Clinician Observed)", classes="subsection_header", id="crps_sg")
        yield Static("Rule 3: ≥ 1 sign observed in 2 or more of the 4 domains", classes="crps_rule_desc")
        for _, domain_lbl, ind_id, items in _SG_DOMAINS:
            with Horizontal(classes="crps_domain_hdr"):
                yield Static(domain_lbl, classes="crps_domain_lbl")
                yield Static("○  –", id=ind_id, classes="crps_domain_ind crps_ind_off")
            with Horizontal(classes="crps_btn_row"):
                for fid, flabel in items:
                    yield FlagButton(flabel, id=fid)
        yield TextArea(id="crps_sg_notes", language="plain")

        # ── 4 · No Other Diagnosis ────────────────────────────────────────────
        yield Label("4 · No Other Diagnosis", classes="subsection_header", id="crps_no_dx")
        with Horizontal(classes="crps_rule_row"):
            yield Static("No better diagnosis explains this presentation", classes="crps_rule_lbl")
            yield FlagButton("Confirmed", id="crps_no_alt_dx")
        yield TextArea(id="crps_no_alt_dx_notes", language="plain")

        # ── Criteria Summary ──────────────────────────────────────────────────
        yield Label("Criteria Summary", classes="subsection_header", id="crps_summary_hdr")
        yield Static("", id="crps_summary", classes="crps_summary_box crps_summary_unmet")

        # ── Subtype Classification ─────────────────────────────────────────────
        yield Label("Subtype Classification", classes="subsection_header", id="crps_subtype_hdr")
        yield Static(
            "T-I = Type I · T-II = Type II · Remit = Remission of Some Features · NOS = Not Otherwise Specified",
            classes="crps_rule_desc",
        )
        yield RadioGroup(_SUBTYPE, id="crps_subtype")
        yield TextArea(id="crps_subtype_notes", language="plain")

        yield Label("General Notes:")
        yield TextArea(id="crps_notes", language="plain")

        # ── 5 · Two-Point Discrimination ──────────────────────────────────────
        yield Label("5 · Two-Point Discrimination", classes="subsection_header", id="crps_tpd")
        yield TextArea(id="crps_tpd_notes", language="plain")

        # ── 6 · Visualisation ─────────────────────────────────────────────────
        yield Label("6 · Visualisation", classes="subsection_header", id="crps_vis")
        yield TextArea(id="crps_vis_notes", language="plain")

        # ── 7 · Laterality ────────────────────────────────────────────────────
        yield Label("7 · Laterality", classes="subsection_header", id="crps_lat")
        with Horizontal(classes="lat_hdr"):
            yield Static("", classes="lat_hdr_blank")
            for _, hdr, _ in _LAT_COLS:
                yield Static(hdr, classes="lat_hdr_col")
        for row_key in _LAT_ROWS:
            with Horizontal(classes="lat_row"):
                yield Static(_LAT_ROW_LABELS[row_key], classes="lat_row_lbl")
                for col_key, _, unit in _LAT_COLS:
                    yield GridInput(
                        placeholder=unit,
                        id=f"crps_lat_{row_key}_{col_key}",
                    )
        yield TextArea(id="crps_lat_notes", language="plain")

    def on_mount(self) -> None:
        self._update_indicators_and_summary()
        self._lat_grid = []
        self._lat_grid_pos = {}
        for r_idx, row_key in enumerate(_LAT_ROWS):
            row_ids = [f"crps_lat_{row_key}_{col}" for col, _, _ in _LAT_COLS]
            self._lat_grid.append(row_ids)
            for c_idx, wid in enumerate(row_ids):
                self._lat_grid_pos[wid] = (r_idx, c_idx)

    # ── Field change → autosave ───────────────────────────────────────────────

    @on(CheckButton.Changed)
    @on(RadioGroup.Changed)
    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if not self._loading:
            self._update_indicators_and_summary()
            self.post_message(self.FieldChanged())

    @on(GridInput.Navigate)
    def _on_lat_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if not isinstance(focused, GridInput):
            return
        wid = focused.id or ""
        if wid not in self._lat_grid_pos:
            return
        row, col = self._lat_grid_pos[wid]
        n_rows = len(self._lat_grid)
        n_cols = len(self._lat_grid[0]) if self._lat_grid else 0
        d = event.direction
        if d == "up":
            new_r, new_c = max(0, row - 1), col
        elif d == "down":
            new_r, new_c = min(n_rows - 1, row + 1), col
        elif d == "left":
            new_r, new_c = row, max(0, col - 1)
        elif d == "right":
            new_r, new_c = row, min(n_cols - 1, col + 1)
        else:
            return
        target = self._lat_grid[new_r][new_c]
        try:
            self.query_one(f"#{target}", GridInput).focus()
        except Exception:
            pass

    # ── Reactive indicators + summary ─────────────────────────────────────────

    def _flag_value(self, fid: str) -> bool | None:
        try:
            return self.query_one(f"#{fid}", FlagButton).value
        except Exception:
            return None

    def _domain_triggered(self, items: list) -> bool:
        return any(self._flag_value(fid) is True for fid, _ in items)

    def _update_indicators_and_summary(self) -> None:
        for _, _, ind_id, items in _SX_DOMAINS + _SG_DOMAINS:
            triggered = self._domain_triggered(items)
            try:
                ind = self.query_one(f"#{ind_id}", Static)
                ind.update("■ triggered" if triggered else "○  –")
                ind.set_class(triggered, "crps_ind_on")
                ind.set_class(not triggered, "crps_ind_off")
            except Exception:
                pass

        sx_t  = sum(1 for _, _, _, items in _SX_DOMAINS if self._domain_triggered(items))
        sg_t  = sum(1 for _, _, _, items in _SG_DOMAINS if self._domain_triggered(items))
        disp  = self._flag_value("crps_disp_pain")
        no_dx = self._flag_value("crps_no_alt_dx")

        r2_met  = sx_t >= 3
        r3_met  = sg_t >= 2
        all_met = disp is True and r2_met and r3_met and no_dx is True

        def _s(v) -> str:
            return "✓" if v is True else "✗" if v is False else "–"

        summary = (
            f"Rule 1 · Disproportionate pain  :  {_s(disp)}\n"
            f"Rule 2 · Symptom domains        :  {sx_t} / 4  (need ≥ 3)  {'✓' if r2_met else '✗'}\n"
            f"Rule 3 · Sign domains           :  {sg_t} / 4  (need ≥ 2)  {'✓' if r3_met else '✗'}\n"
            f"Rule 4 · No other diagnosis     :  {_s(no_dx)}\n"
            f"\n"
            f"Clinical Criteria:  {'CRITERIA MET' if all_met else 'CRITERIA NOT MET'}"
        )
        try:
            summ = self.query_one("#crps_summary", Static)
            summ.update(summary)
            summ.set_class(all_met, "crps_summary_met")
            summ.set_class(not all_met, "crps_summary_unmet")
        except Exception:
            pass

    # ── collect / load / is_complete ─────────────────────────────────────────

    def collect(self) -> dict:
        data: dict = {}
        for fid in _ALL_FLAG_IDS:
            try:
                data[fid] = self.query_one(f"#{fid}", FlagButton).value
            except Exception:
                data[fid] = None
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for tid in _ALL_TA_IDS:
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        for lid in _LAT_IDS:
            try:
                data[lid] = self.query_one(f"#{lid}", GridInput).value.strip()
            except Exception:
                data[lid] = ""
        # Derived fields for report rendering
        sx_t  = sum(1 for _, _, _, items in _SX_DOMAINS if self._domain_triggered(items))
        sg_t  = sum(1 for _, _, _, items in _SG_DOMAINS if self._domain_triggered(items))
        disp  = data.get("crps_disp_pain")
        no_dx = data.get("crps_no_alt_dx")
        data["crps_sx_domains_triggered"] = sx_t
        data["crps_sg_domains_triggered"] = sg_t
        data["crps_criteria_met"] = (
            disp is True and sx_t >= 3 and sg_t >= 2 and no_dx is True
        )
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for fid in _ALL_FLAG_IDS:
                try:
                    self.query_one(f"#{fid}", FlagButton).set_value(data.get(fid))
                except Exception:
                    pass
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for tid in _ALL_TA_IDS:
                try:
                    self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
                except Exception:
                    pass
            for lid in _LAT_IDS:
                try:
                    self.query_one(f"#{lid}", GridInput).value = data.get(lid, "")
                except Exception:
                    pass
        finally:
            self._loading = False
        self._update_indicators_and_summary()

    def is_complete(self) -> bool:
        try:
            return self.query_one("#crps_disp_pain", FlagButton).value is not None
        except Exception:
            return False
