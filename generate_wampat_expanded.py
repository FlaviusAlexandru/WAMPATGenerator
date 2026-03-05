"""
generate_wampat.py
------------------
Generates .wampat pattern files for the WAM study recreation.

Study design: within-participant 3x3 factorial
  - 3 Conditions: OperationFB, ActionFB, TaskFB
  - 3 Metrics:    Time, Distance, MaxSpeed
  - 4 Phases per trial: Baseline, Explore, BestPerf, Instructed

File naming: {Participant}_{Condition}_{Metric}.wampat
  e.g. 1_OperationFB_Time.wampat

CSV columns expected (0-indexed):
  0: Condition   1: Metric   2: Participant   3: Order
  4: FB Order    5: Metric Order
  6: Baseline    7: Explore  8: BestPerf      9: Instructed

Usage:
  python generate_wampat.py                         # uses defaults below
  python generate_wampat.py path/to/study.csv ./out # custom csv + output dir
"""

import csv
import io
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CSV  = os.path.join(os.path.dirname(__file__), "study.csv")
DEFAULT_OUT  = os.path.join(os.path.dirname(__file__), "generated_wampat")

WALL_CONFIG = (
    "WALL:(ROW = 5, COL = 9, SIZEX = 5.85, SIZEY = 2.98, "
    "CURVEX = 0.1, CURVEY = 0.1, MAXANGLE = 80, MOLESCALEX = 34, MOLESCALEY = 34)"
)

DEFAULT_MODIFIER = (
    "MODIFIER:(EYEPATCH = None, MIRROR = False, CONTROLLEROFFSET = 0.0, "
    "PRISM = 0.0, HIDEWALL = None, HIDEWALLAMOUNT = 0.5, GEOMETRICMIRROR = False, "
    "MAINCONTROLLER = Right, MOTORSPACE = Medium, "
    "PERFORMANCEFEEDBACK = None, JUDGEMENT = None)"
)

# Segment ID encoding: PPCCMMTT
# PP = Participant (01-99)
# CC = Condition (10=Operation, 20=Action, 30=Task)
# MM = Metric (11=Distance, 22=MaxSpeed, 33=Time)
# TT = Phase (00=Baseline, 10=Explore, 20=BestPerf, 30=Instructed)
def generate_segment_id(participant: str, condition: str, metric: str, phase: str) -> str:
    """Generate a unique segment ID for logging/analysis."""
    pp = participant.zfill(2)
    
    cc_map = {"OperationFB": "10", "ActionFB": "20", "TaskFB": "30"}
    cc = cc_map.get(condition, "00")
    
    mm_map = {"Distance": "11", "MaxSpeed": "22", "Time": "33"}
    mm = mm_map.get(metric, "00")
    
    tt_map = {"Baseline": "00", "Explore": "10", "BestPerf": "20", "Instructed": "30"}
    tt = tt_map.get(phase, "00")
    
    return pp + cc + mm + tt


def _mole_sequence(coords: list) -> str:
    """Build a sequence of MOLE + WAIT:(HIT) lines from a list of (X, Y) tuples."""
    lines = []
    for x, y in coords:
        lines.append(f"MOLE:(X = {x}, Y = {y}, LIFETIME = 5)")
        lines.append("WAIT:(HIT)")
    return "\n".join(lines)


PATTERN_BLOCKS = {
    "A": _mole_sequence([
        (2, 2), (3, 1), (7, 5), (6, 3), (9, 4),
        (1, 4), (1, 3), (5, 2), (5, 5), (8, 2),
    ]),
    "B": _mole_sequence([
        (2, 4), (3, 5), (7, 1), (4, 3), (1, 2),
        (9, 2), (9, 3), (5, 4), (5, 1), (8, 4),
    ]),
    "C": _mole_sequence([
        (6, 2), (8, 1), (2, 5), (3, 2), (7, 4),
        (4, 5), (4, 1), (4, 4), (7, 3), (3, 3),
    ]),
    "D": _mole_sequence([
        (6, 4), (8, 5), (2, 1), (3, 4), (4, 2),
        (6, 1), (6, 5), (7, 2), (2, 3), (8, 3),
    ]),
}

VALID_CONDITIONS = {"OperationFB", "ActionFB", "TaskFB"}

# Feedback type mapping based on condition
FEEDBACK_TYPE_MAP = {
    "OperationFB": "Operation",
    "ActionFB": "Action",
    "TaskFB": "Task"
}

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def build_phase_block(participant: str, condition: str, metric: str,
                     phase_name: str, sequence: str, is_baseline: bool = False) -> str:
    """Returns the WAMPAT text for one phase (e.g. Baseline with sequence 'AC')."""
    segment_id = generate_segment_id(participant, condition, metric, phase_name)
    feedback_type = FEEDBACK_TYPE_MAP.get(condition, "Operation")
    
    lines = [
        f"// ============ Phase: {phase_name} (sequence: {sequence}) ============",
        f"SEGMENT:(ID = {segment_id}, LABEL = {phase_name})",
    ]
        # Set performance feedback and judgement parameters per phase
    if is_baseline:
        lines.append(f"MODIFIER:(PERFORMANCEFEEDBACK = None, JUDGEMENT = {metric})")
    else:
        lines.append(f"MODIFIER:(PERFORMANCEFEEDBACK = {feedback_type}, JUDGEMENT = {metric})")    
    # Add phase-specific instructions
    if phase_name == "Baseline":
        lines.append("MESSAGE:(LABEL = Get_Ready.., TIME = 3)")
        lines.append("WAIT:(TIME = 4)")
        lines.append("CALIBRATION:(TYPE=PERFORMANCE, STATE=START)")
    elif phase_name == "Explore":
        lines.append("MESSAGE:(LABEL = Explore_The_Feedback, TIME = 3)")
        lines.append("WAIT:(TIME = 4)")
    elif phase_name == "BestPerf":
        lines.append("MESSAGE:(LABEL = Obtain_The_Best_Feedback_Possible, TIME = 3)")
        lines.append("WAIT:(TIME = 4)")
    elif phase_name == "Instructed":
        lines.append("MESSAGE:(LABEL = Follow_Performance_Instructions, TIME = 3)")
        lines.append("WAIT:(TIME = 4)")
    
    # Add pattern blocks with feedback after each (for non-Baseline)
    for char in sequence:
        block = PATTERN_BLOCKS.get(char.upper())
        if block is None:
            print(f"  WARNING: Unknown pattern key '{char}' in sequence '{sequence}' - skipped.")
            continue
        lines.append(f"// --- Pattern Block {char.upper()} ---")
        lines.append(block)
        
        # Show task feedback after each pattern block (for non-Baseline phases)
        if not is_baseline:
            lines.append("FEEDBACK:(TIME = 10)")
            lines.append("WAIT:(TIME = 10)")
    
    # Add calibration point (for all phases)
    lines.append("// --- Calibration Point ---")
    lines.append(f"SEGMENT:(ID = {segment_id}99, LABEL = Calibration_Point)")
    lines.append("MOLE:(X = 5, Y = 3, LIFETIME = 5) // Center calibration")
    lines.append("WAIT:(HIT)")
    
    # Add feedback question for non-Baseline phases
    if not is_baseline:
        lines.append("MESSAGE:(LABEL = Questions.., TIME = 3)")
        lines.append("WAIT:(TIME = 3)")
    
    # Add calibration end for Baseline phase
    if is_baseline:
        lines.append("CALIBRATION:(TYPE=PERFORMANCE, STATE=END)")
    
    lines.append(f"// ============ End of {phase_name} ============")
    lines.append("WAIT:(TIME = 2)")
    return "\n".join(lines)


def build_wampat(participant: str, condition: str, metric: str,
                 baseline: str, explore: str, best_perf: str, instructed: str) -> str:
    """Returns the full content of one .wampat file."""
    sections = [
        f"// ========================================",
        f"// Participant:        {participant}",
        f"// Condition:          {condition}",
        f"// Performance Metric: {metric}",
        f"// ========================================",
        "",
        WALL_CONFIG,
        DEFAULT_MODIFIER,
        "",
        "// --- Initial Wait ---",
        f"MESSAGE:(LABEL = Session_{condition}_{metric}_Start, TIME = 3)",
        "WAIT:(TIME = 5)",
        "",
        f"// --- Study condition: {condition} | Metric: {metric} ---",
        "",
        build_phase_block(participant, condition, metric, "Baseline", baseline, is_baseline=True),
        "",
        "MESSAGE:(LABEL = Baseline_Completed, TIME = 2)",
        "WAIT:(TIME = 3)",
        "",
        build_phase_block(participant, condition, metric, "Explore", explore, is_baseline=False),
        "",
        "MESSAGE:(LABEL = Exploration_Completed, TIME = 2)",
        "WAIT:(TIME = 3)",
        "",
        build_phase_block(participant, condition, metric, "BestPerf", best_perf, is_baseline=False),
        "",
        "MESSAGE:(LABEL = Best_Performance_Completed, TIME = 2)",
        "WAIT:(TIME = 3)",
        "",
        build_phase_block(participant, condition, metric, "Instructed", instructed, is_baseline=False),
        "",
        f"MESSAGE:(LABEL = Session_Complete, TIME = 3)",
        "WAIT:(TIME = 5)",
    ]
    return "\n".join(sections) + "\n"


def generate_from_csv(csv_path: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    created = 0
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row

        for row in reader:
            # Ignore short or empty rows
            if len(row) < 10:
                continue

            condition   = row[0].strip()
            metric      = row[1].strip()
            participant = row[2].strip()
            baseline    = row[6].strip()
            explore     = row[7].strip()
            best_perf   = row[8].strip()
            instructed  = row[9].strip()

            # Skip balance/metadata rows - valid rows have numeric participant + known condition
            if not participant.isdigit():
                continue
            if condition not in VALID_CONDITIONS:
                continue

            content   = build_wampat(participant, condition, metric,
                                     baseline, explore, best_perf, instructed)
            file_name = f"{participant}_{condition}_{metric}.wampat"
            file_path = os.path.join(out_dir, file_name)

            with open(file_path, "w", encoding="utf-8") as out:
                out.write(content)

            print(f"  Created: {file_name}")
            created += 1

    print(f"\nDone. {created} files created, {skipped} skipped.")
    print(f"Output folder: {os.path.abspath(out_dir)}")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WAMPAT Generator (WAM Study)")
        self.resizable(True, True)
        self.minsize(560, 400)

        pad = {"padx": 10, "pady": 6}

        # --- CSV row ---
        tk.Label(self, text="Input CSV:", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self.csv_var = tk.StringVar(value=DEFAULT_CSV)
        tk.Entry(self, textvariable=self.csv_var, width=55).grid(row=0, column=1, sticky="ew", **pad)
        tk.Button(self, text="Browse…", command=self._pick_csv).grid(row=0, column=2, **pad)

        # --- Output dir row ---
        tk.Label(self, text="Output folder:", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self.out_var = tk.StringVar(value=DEFAULT_OUT)
        tk.Entry(self, textvariable=self.out_var, width=55).grid(row=1, column=1, sticky="ew", **pad)
        tk.Button(self, text="Browse…", command=self._pick_out).grid(row=1, column=2, **pad)

        # --- Generate button ---
        tk.Button(self, text="Generate .wampat files", command=self._run,
                  bg="#0078d4", fg="white", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=4).grid(row=2, column=0, columnspan=3, pady=(4, 8))

        # --- Log area ---
        self.log = scrolledtext.ScrolledText(self, state="disabled", height=16,
                                              font=("Consolas", 9), wrap="word")
        self.log.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

    # -----------------------------------------------------------------------
    def _pick_csv(self):
        path = filedialog.askopenfilename(
            title="Select study CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.csv_var.set(path)

    def _pick_out(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.out_var.set(path)

    def _log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def _run(self):
        csv_path = self.csv_var.get().strip()
        out_dir  = self.out_var.get().strip()

        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showerror("File not found", f"CSV not found:\n{csv_path}")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        self._log(f"Reading:   {csv_path}")
        self._log(f"Output to: {os.path.abspath(out_dir)}\n")

        # Redirect stdout into the log widget while generate_from_csv runs
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            generate_from_csv(csv_path, out_dir)
        except Exception as exc:
            sys.stdout = old_stdout
            messagebox.showerror("Error", str(exc))
            return
        finally:
            sys.stdout = old_stdout

        for line in buf.getvalue().splitlines():
            self._log(line)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
