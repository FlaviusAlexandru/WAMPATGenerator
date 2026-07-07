"""
unity_pattern_builder.py
------------------------
Standalone GUI for assembling .wampat files with Unity-aware detection.

This window scans a Unity Pattern scripts folder, reports the actions the
runtime expects, and lets users build phase sequences by dragging mole types
into the five study phases, then editing their wall positions. The legacy
A1..D2 palette was a full-wall tiling scheme for a 5-row by 9-column wall,
so the old presets are being replaced by explicit mole type and position data.
"""

from __future__ import annotations

import os
import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, scrolledtext, ttk

from generate_wampat_expanded import build_wampat, derive_no_feedback_sequence


DEFAULT_UNITY_PATTERN_DIR = r"C:\Users\FU05OG\Documents\GitHub\Whack_A_Mole_VR\Assets\Scripts\Patterns"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated_wampat")

MOLE_TYPE_OPTIONS = [
    "SimpleTarget",
    "BallMole",
    "DistractorLeft",
    "DistractorRight",
    "GestureMole",
    "Invisible",
    "BalloonMole",
    "WaspMole",
    "KeyMole",
    "CountdownMole",
]
DEFAULT_MOLE_TYPE = MOLE_TYPE_OPTIONS[0]
DEFAULT_MOLE_X = "5"
DEFAULT_MOLE_Y = "3"
DEFAULT_MOLE_LIFETIME = "5"
PHASE_KEYS = ["Baseline", "Explore", "BestPerf", "Instructed", "NoFeedback"]
VALID_CONDITIONS = ["OperationFB", "ActionFB", "TaskFB"]
VALID_METRICS = ["Time", "Distance", "MaxSpeed"]
UNITY_STATEMENT_TEMPLATES = [
    "MOLE:(TYPE = SimpleTarget, X = 5, Y = 3, LIFETIME = 5)",
    "WAIT:(HIT)",
    "WAIT:(TIME = 3)",
    "SEGMENT:(ID = 01103300, LABEL = Baseline)",
    "MODIFIER:(PERFORMANCEFEEDBACK = None, JUDGEMENT = Time)",
    "MESSAGE:(LABEL = Session_Start, TIME = 3)",
    "CALIBRATION:(TYPE=PERFORMANCE, STATE=START)",
]

ACTION_RE = re.compile(r'case\s+"([A-Z][A-Z0-9_]*)"|keyValue\[0\]\s*==\s*"([A-Z][A-Z0-9_]*)"')


def format_mole_entry(mole_type: str, x_pos: str = DEFAULT_MOLE_X, y_pos: str = DEFAULT_MOLE_Y, lifetime: str = DEFAULT_MOLE_LIFETIME) -> str:
    return f"{mole_type}@{x_pos},{y_pos},{lifetime}"


def parse_mole_entry(entry: str) -> tuple[str, str, str, str]:
    mole_type = DEFAULT_MOLE_TYPE
    x_pos = DEFAULT_MOLE_X
    y_pos = DEFAULT_MOLE_Y
    lifetime = DEFAULT_MOLE_LIFETIME

    raw = (entry or "").strip()
    if "@" in raw:
        mole_type_part, position_part = raw.split("@", 1)
        mole_type = mole_type_part.strip() or DEFAULT_MOLE_TYPE
        position_bits = [part.strip() for part in position_part.split(",") if part.strip()]
        if len(position_bits) >= 2:
            x_pos = position_bits[0]
            y_pos = position_bits[1]
        if len(position_bits) >= 3:
            lifetime = position_bits[2]
    elif raw:
        mole_type = raw

    return mole_type, x_pos, y_pos, lifetime


@dataclass
class DetectedSurface:
    pattern_dir: str
    files: list[str]
    actions: list[str]
    parser_notes: list[str]


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def detect_unity_pattern_surface(pattern_dir: str) -> DetectedSurface:
    files: list[str] = []
    actions: set[str] = set()
    parser_notes: list[str] = []

    if not os.path.isdir(pattern_dir):
        return DetectedSurface(pattern_dir=pattern_dir, files=[], actions=[], parser_notes=["Pattern folder not found."])

    candidate_files = [
        "PatternInterface.cs",
        "PatternParser.cs",
        "PatternPlayer.cs",
        "PatternManager.cs",
        "PatternReadWriter.cs",
    ]

    for filename in candidate_files:
        path = os.path.join(pattern_dir, filename)
        if not os.path.isfile(path):
            continue

        files.append(filename)
        source = _read_text(path)

        for match in ACTION_RE.findall(source):
            action = match[0] or match[1]
            if action:
                actions.add(action)

        if filename == "PatternParser.cs":
            parser_notes.append("Parser contract: KEY:(properties), where parentheses may be empty")
            if "[ABCD][12]" in source:
                parser_notes.append("Half-token parsing supported: A1..D2")
            if "ABCD" in source:
                parser_notes.append("Legacy letter-only parsing supported")
            if "WAIT:(HIT)" in source:
                parser_notes.append("Progression mode is triggered by WAIT:(HIT)")
        if filename == "PatternReadWriter.cs" and "TestPatterns" in source:
            parser_notes.append("Pattern files are loaded from persistentDataPath/TestPatterns")

    if not files:
        parser_notes.append("No Pattern*.cs files were found in the selected folder.")

    return DetectedSurface(
        pattern_dir=pattern_dir,
        files=sorted(files),
        actions=sorted(actions),
        parser_notes=parser_notes,
    )


class PhaseEditor(ttk.Frame):
    def __init__(self, master: tk.Misc, phase_key: str, add_callback):
        super().__init__(master)
        self.phase_key = phase_key
        self.add_callback = add_callback
        self.label_var = tk.StringVar(value=phase_key)
        self.type_var = tk.StringVar(value=DEFAULT_MOLE_TYPE)
        self.x_var = tk.StringVar(value=DEFAULT_MOLE_X)
        self.y_var = tk.StringVar(value=DEFAULT_MOLE_Y)
        self.lifetime_var = tk.StringVar(value=DEFAULT_MOLE_LIFETIME)

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 4))

        ttk.Label(header, text=phase_key, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(header, text="Clear", width=8, command=self.clear).pack(side="right")

        label_row = ttk.Frame(self)
        label_row.pack(fill="x", pady=(0, 4))
        ttk.Label(label_row, text="Label", width=8).pack(side="left")
        ttk.Entry(label_row, textvariable=self.label_var).pack(side="left", fill="x", expand=True)

        self.tokens = tk.Listbox(self, height=4, selectmode="browse", exportselection=False)
        self.tokens.pack(fill="x")
        self.tokens.bind("<<ListboxSelect>>", self._load_selected_entry)

        edit_panel = ttk.Frame(self)
        edit_panel.pack(fill="x", pady=(4, 0))

        type_row = ttk.Frame(edit_panel)
        type_row.pack(fill="x")
        ttk.Label(type_row, text="Type", width=8).pack(side="left")
        ttk.Combobox(type_row, textvariable=self.type_var, values=MOLE_TYPE_OPTIONS, state="readonly").pack(side="left", fill="x", expand=True)

        position_row = ttk.Frame(edit_panel)
        position_row.pack(fill="x", pady=(4, 0))
        ttk.Label(position_row, text="X", width=8).pack(side="left")
        ttk.Entry(position_row, textvariable=self.x_var, width=6).pack(side="left")
        ttk.Label(position_row, text="Y", width=3).pack(side="left", padx=(6, 0))
        ttk.Entry(position_row, textvariable=self.y_var, width=6).pack(side="left")
        ttk.Label(position_row, text="Lifetime", width=8).pack(side="left", padx=(6, 0))
        ttk.Entry(position_row, textvariable=self.lifetime_var, width=6).pack(side="left")

        ttk.Button(edit_panel, text="Update selected", command=self.update_selected).pack(anchor="w", pady=(4, 0))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(4, 0))

        ttk.Button(buttons, text="Up", width=6, command=self.move_up).pack(side="left")
        ttk.Button(buttons, text="Down", width=6, command=self.move_down).pack(side="left", padx=(4, 0))
        ttk.Button(buttons, text="Remove", width=8, command=self.remove_selected).pack(side="left", padx=(4, 0))

        self.drop_target = ttk.Frame(self, padding=4, relief="ridge")
        self.drop_target.pack(fill="x", pady=(4, 0))
        ttk.Label(self.drop_target, text="Drop mole types here", foreground="#666666").pack(anchor="w")

    def add_token(self, token: str) -> None:
        self.tokens.insert("end", format_mole_entry(token))
        self._select_last()
        self._load_selected_entry()
        self.add_callback()

    def update_selected(self) -> None:
        selection = self.tokens.curselection()
        if not selection:
            return
        index = selection[0]
        self.tokens.delete(index)
        self.tokens.insert(index, format_mole_entry(
            self.type_var.get().strip() or DEFAULT_MOLE_TYPE,
            self.x_var.get().strip() or DEFAULT_MOLE_X,
            self.y_var.get().strip() or DEFAULT_MOLE_Y,
            self.lifetime_var.get().strip() or DEFAULT_MOLE_LIFETIME,
        ))
        self.tokens.selection_set(index)
        self.tokens.see(index)
        self.add_callback()

    def clear(self) -> None:
        self.tokens.delete(0, "end")
        self.add_callback()

    def remove_selected(self) -> None:
        selection = self.tokens.curselection()
        if not selection:
            return
        self.tokens.delete(selection[0])
        self.add_callback()

    def move_up(self) -> None:
        selection = self.tokens.curselection()
        if not selection:
            return
        index = selection[0]
        if index <= 0:
            return
        token = self.tokens.get(index)
        self.tokens.delete(index)
        self.tokens.insert(index - 1, token)
        self.tokens.selection_set(index - 1)
        self._load_selected_entry()
        self.add_callback()

    def move_down(self) -> None:
        selection = self.tokens.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= self.tokens.size() - 1:
            return
        token = self.tokens.get(index)
        self.tokens.delete(index)
        self.tokens.insert(index + 1, token)
        self.tokens.selection_set(index + 1)
        self._load_selected_entry()
        self.add_callback()

    def values(self) -> list[str]:
        return list(self.tokens.get(0, "end"))

    def label(self) -> str:
        value = self.label_var.get().strip()
        return value or self.phase_key

    def _load_selected_entry(self, event=None) -> None:
        selection = self.tokens.curselection()
        if not selection:
            return
        mole_type, x_pos, y_pos, lifetime = parse_mole_entry(self.tokens.get(selection[0]))
        self.type_var.set(mole_type)
        self.x_var.set(x_pos)
        self.y_var.set(y_pos)
        self.lifetime_var.set(lifetime)

    def _select_last(self) -> None:
        if self.tokens.size() > 0:
            last = self.tokens.size() - 1
            self.tokens.selection_clear(0, "end")
            self.tokens.selection_set(last)
            self.tokens.see(last)


class UnityPatternBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Unity-Aware WAMPAT Builder")
        self.minsize(1200, 760)

        self.phase_editors: dict[str, PhaseEditor] = {}
        self.drag_token: str | None = None
        self.drag_preview: tk.Toplevel | None = None
        self.detected_surface = detect_unity_pattern_surface(DEFAULT_UNITY_PATTERN_DIR)

        self.unity_dir_var = tk.StringVar(value=DEFAULT_UNITY_PATTERN_DIR)
        self.output_dir_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.output_name_var = tk.StringVar(value="custom_pattern.wampat")
        self.participant_var = tk.StringVar(value="1")
        self.condition_var = tk.StringVar(value=VALID_CONDITIONS[0])
        self.metric_var = tk.StringVar(value=VALID_METRICS[0])

        self._build_layout()
        self._apply_detection(self.detected_surface)
        self._rebuild_preview()

    def _build_layout(self) -> None:
        viewport = ttk.Frame(self, padding=0)
        viewport.pack(fill="both", expand=True)

        self.layout_canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.layout_canvas.yview)
        self.layout_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.layout_canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_layout = ttk.Frame(self.layout_canvas, padding=12)
        layout_window = self.layout_canvas.create_window((0, 0), window=self.scrollable_layout, anchor="nw")

        def _sync_scrollregion(event) -> None:
            self.layout_canvas.configure(scrollregion=self.layout_canvas.bbox("all"))

        def _sync_canvas_width(event) -> None:
            self.layout_canvas.itemconfigure(layout_window, width=event.width)

        self.scrollable_layout.bind("<Configure>", _sync_scrollregion)
        self.layout_canvas.bind("<Configure>", _sync_canvas_width)

        self.bind_all("<MouseWheel>", self._on_mousewheel)

        left = ttk.Frame(self.scrollable_layout)
        left.pack(side="left", fill="y", padx=(0, 12))

        right = ttk.Frame(self.scrollable_layout)
        right.pack(side="right", fill="both", expand=True)

        self._build_detection_panel(left)
        self._build_palette_panel(left)
        self._build_statement_panel(left)
        self._build_metadata_panel(left)

        self._build_phase_panel(right)
        self._build_preview_panel(right)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not hasattr(self, "layout_canvas"):
            return
        delta = int(-1 * (event.delta / 120))
        self.layout_canvas.yview_scroll(delta, "units")

    def _build_detection_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Unity Pattern Surface", padding=10)
        panel.pack(fill="x", pady=(0, 12))

        ttk.Label(panel, text="Pattern scripts folder").pack(anchor="w")
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=(4, 8))
        ttk.Entry(row, textvariable=self.unity_dir_var, width=44).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse", command=self._browse_unity_dir).pack(side="left", padx=(6, 0))
        ttk.Button(panel, text="Detect", command=self._run_detection).pack(anchor="w")

        self.detected_files_var = tk.StringVar(value="No scan yet")
        self.detected_actions_var = tk.StringVar(value="No scan yet")
        self.detected_notes_var = tk.StringVar(value="")

        ttk.Label(panel, textvariable=self.detected_files_var, wraplength=330, justify="left").pack(anchor="w", pady=(8, 0))
        ttk.Label(panel, textvariable=self.detected_actions_var, wraplength=330, justify="left").pack(anchor="w", pady=(6, 0))
        ttk.Label(panel, textvariable=self.detected_notes_var, wraplength=330, justify="left", foreground="#555555").pack(anchor="w", pady=(6, 0))

    def _build_palette_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Drag Tokens", padding=10)
        panel.pack(fill="x", pady=(0, 12))

        self.palette_frame = ttk.Frame(panel)
        self.palette_frame.pack(fill="x")

        for index, token in enumerate(MOLE_TYPE_OPTIONS):
            button = tk.Label(
                self.palette_frame,
                text=token,
                relief="raised",
                padx=10,
                pady=6,
                bg="#f0f0f0",
                cursor="hand2",
            )
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)
            button.bind("<ButtonPress-1>", lambda event, value=token: self._start_drag(event, value))
            button.bind("<B1-Motion>", self._drag_motion)
            button.bind("<ButtonRelease-1>", self._end_drag)

        self.palette_frame.columnconfigure(0, weight=1)
        self.palette_frame.columnconfigure(1, weight=1)

        hint = ttk.Label(panel, text="Drop a mole type onto a phase card, then edit X/Y to place it on the wall.", wraplength=320)
        hint.pack(anchor="w", pady=(8, 0))

    def _build_statement_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Unity Statement Reference", padding=10)
        panel.pack(fill="x", pady=(0, 12))

        ttk.Label(
            panel,
            text="The reader accepts KEY:(properties). MOLE also accepts TYPE so you can choose a mole prefab and position it on the wall.",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        for template in UNITY_STATEMENT_TEMPLATES:
            ttk.Label(panel, text=template, wraplength=320, justify="left").pack(anchor="w", pady=1)

    def _build_metadata_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Output Settings", padding=10)
        panel.pack(fill="x")

        self._add_labeled_entry(panel, "Participant", self.participant_var)
        self._add_labeled_combo(panel, "Condition", self.condition_var, VALID_CONDITIONS)
        self._add_labeled_combo(panel, "Metric", self.metric_var, VALID_METRICS)

        out_row = ttk.Frame(panel)
        out_row.pack(fill="x", pady=(6, 0))
        ttk.Label(out_row, text="Output folder", width=14).pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="Browse", command=self._browse_output_dir).pack(side="left", padx=(6, 0))

        name_row = ttk.Frame(panel)
        name_row.pack(fill="x", pady=(6, 0))
        ttk.Label(name_row, text="File name", width=14).pack(side="left")
        ttk.Entry(name_row, textvariable=self.output_name_var).pack(side="left", fill="x", expand=True)

        button_row = ttk.Frame(panel)
        button_row.pack(fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Load sample", command=self._load_sample_layout).pack(side="left")
        ttk.Button(button_row, text="Clear all", command=self._clear_all_phases).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Export .wampat", command=self._export_pattern).pack(side="right")

    def _build_phase_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Phase Builder", padding=10)
        panel.pack(fill="both", expand=False)

        for phase_key in PHASE_KEYS:
            editor = PhaseEditor(panel, phase_key, self._rebuild_preview)
            editor.pack(fill="x", pady=(0, 10))
            editor.drop_target.bind("<Enter>", lambda event, name=phase_key: self._highlight_phase(name, True))
            editor.drop_target.bind("<Leave>", lambda event, name=phase_key: self._highlight_phase(name, False))
            self.phase_editors[phase_key] = editor

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Live Preview", padding=10)
        panel.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Label(panel, text="Preview uses Unity-style KEY:(properties) lines. Mole entries are exported as TYPE + wall coordinates, and your phase labels stay attached to the segment comments.", wraplength=760, justify="left").pack(anchor="w", pady=(0, 8))

        self.preview = scrolledtext.ScrolledText(panel, height=24, wrap="none", font=("Consolas", 9))
        self.preview.pack(fill="both", expand=True)

    def _add_labeled_entry(self, parent: tk.Misc, label: str, variable: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 6))
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)

    def _add_labeled_combo(self, parent: tk.Misc, label: str, variable: tk.StringVar, values: list[str]) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 6))
        ttk.Label(row, text=label, width=14).pack(side="left")
        combo = ttk.Combobox(row, textvariable=variable, values=values, state="readonly")
        combo.pack(side="left", fill="x", expand=True)

    def _browse_unity_dir(self) -> None:
        path = filedialog.askdirectory(title="Select Unity Pattern folder")
        if path:
            self.unity_dir_var.set(path)
            self._run_detection()

    def _browse_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_dir_var.set(path)

    def _run_detection(self) -> None:
        self.detected_surface = detect_unity_pattern_surface(self.unity_dir_var.get().strip())
        self._apply_detection(self.detected_surface)

    def _apply_detection(self, surface: DetectedSurface) -> None:
        if surface.files:
            self.detected_files_var.set("Detected files: " + ", ".join(surface.files))
        else:
            self.detected_files_var.set("Detected files: none")

        if surface.actions:
            self.detected_actions_var.set("Detected actions: " + ", ".join(surface.actions))
        else:
            self.detected_actions_var.set("Detected actions: none")

        if surface.parser_notes:
            self.detected_notes_var.set("Notes: " + " | ".join(surface.parser_notes))
        else:
            self.detected_notes_var.set("Notes: none")

    def _start_drag(self, event: tk.Event, token: str) -> None:
        self.drag_token = token
        self.drag_preview = tk.Toplevel(self)
        self.drag_preview.overrideredirect(True)
        self.drag_preview.attributes("-topmost", True)
        label = tk.Label(self.drag_preview, text=token, bg="#d9e8ff", relief="solid", padx=10, pady=4)
        label.pack()
        self._move_drag(event)

    def _drag_motion(self, event: tk.Event) -> None:
        self._move_drag(event)

    def _move_drag(self, event: tk.Event) -> None:
        if self.drag_preview is None:
            return
        self.drag_preview.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

    def _end_drag(self, event: tk.Event) -> None:
        if self.drag_preview is not None:
            self.drag_preview.destroy()
            self.drag_preview = None

        token = self.drag_token
        self.drag_token = None
        if not token:
            return

        target = self.winfo_containing(event.x_root, event.y_root)
        phase_name = self._resolve_phase_from_widget(target)
        if phase_name:
            self.phase_editors[phase_name].add_token(token)
            self._rebuild_preview()

    def _resolve_phase_from_widget(self, widget) -> str | None:
        while widget is not None:
            for phase_name, editor in self.phase_editors.items():
                if widget == editor.drop_target or widget == editor.tokens:
                    return phase_name
            widget = getattr(widget, "master", None)
        return None

    def _highlight_phase(self, phase_name: str, active: bool) -> None:
        editor = self.phase_editors[phase_name]
        editor.drop_target.configure(style="DropTargetActive.TFrame" if active else "DropTarget.TFrame")

    def _phase_sequence(self, phase_name: str) -> str:
        values = self.phase_editors[phase_name].values()
        return "\n".join(values)

    def _rebuild_preview(self) -> None:
        baseline = self._phase_sequence("Baseline")
        explore = self._phase_sequence("Explore")
        best_perf = self._phase_sequence("BestPerf")
        instructed = self._phase_sequence("Instructed")
        no_feedback = self._phase_sequence("NoFeedback") or derive_no_feedback_sequence(instructed)
        phase_labels = {key: editor.label() for key, editor in self.phase_editors.items()}

        participant = self.participant_var.get().strip() or "1"
        condition = self.condition_var.get().strip() or VALID_CONDITIONS[0]
        metric = self.metric_var.get().strip() or VALID_METRICS[0]

        preview_text = build_wampat(
            participant=participant,
            condition=condition,
            metric=metric,
            baseline=baseline,
            explore=explore,
            best_perf=best_perf,
            instructed=instructed,
            no_feedback_instructed=no_feedback,
            phase_labels=phase_labels,
        )

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", preview_text)
        self.preview.configure(state="disabled")

    def _load_sample_layout(self) -> None:
        sample_layout = {
            "Baseline": [("SimpleTarget", "5", "3"), ("BallMole", "2", "2")],
            "Explore": [("DistractorLeft", "3", "1"), ("WaspMole", "7", "5")],
            "BestPerf": [("BalloonMole", "6", "2"), ("KeyMole", "8", "4")],
            "Instructed": [("GestureMole", "4", "5"), ("CountdownMole", "1", "4")],
            "NoFeedback": [("Invisible", "6", "1"), ("DistractorRight", "7", "2")],
        }
        for phase_name, tokens in sample_layout.items():
            editor = self.phase_editors[phase_name]
            editor.clear()
            for mole_type, x_pos, y_pos in tokens:
                editor.tokens.insert("end", format_mole_entry(mole_type, x_pos, y_pos))
            editor._select_last()
            editor._load_selected_entry()
        self.phase_editors["Baseline"].label_var.set("Baseline")
        self.phase_editors["Explore"].label_var.set("Explore")
        self.phase_editors["BestPerf"].label_var.set("BestPerf")
        self.phase_editors["Instructed"].label_var.set("Instructed")
        self.phase_editors["NoFeedback"].label_var.set("NoFeedback")
        self._rebuild_preview()

    def _clear_all_phases(self) -> None:
        for editor in self.phase_editors.values():
            editor.clear()
        self._rebuild_preview()

    def _export_pattern(self) -> None:
        self._rebuild_preview()

        output_dir = self.output_dir_var.get().strip() or DEFAULT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        filename = self.output_name_var.get().strip()
        if not filename:
            filename = "custom_pattern.wampat"
        if not filename.lower().endswith(".wampat"):
            filename += ".wampat"

        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(self.preview.get("1.0", "end-1c"))

        messagebox.showinfo("Export complete", f"Pattern saved to:\n{output_path}")


def main() -> None:
    app = UnityPatternBuilderApp()
    style = ttk.Style(app)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("DropTarget.TFrame", background="#f5f5f5")
    style.configure("DropTargetActive.TFrame", background="#dff0d8")
    app.mainloop()


if __name__ == "__main__":
    main()