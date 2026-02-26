# WAMPAT Generator

A Python-based GUI tool for generating `.wampat` pattern files for WAM (Whac-A-Mole) motor learning studies in virtual reality.

## Description

This tool automates the creation of WAMPAT (Whac-A-Mole Pattern) files for controlled experimental studies investigating motor learning and adaptation. It generates structured trial sequences with precise temporal control, spatial patterns, and performance feedback configurations.

The generator implements a within-participant 3×3 factorial design for studying motor learning under different feedback conditions and performance metrics.

## Features

- **GUI Interface**: User-friendly Tkinter-based interface with file browsing and live logging
- **Batch Generation**: Processes CSV study designs to generate multiple participant files automatically
- **Structured Phases**: Four distinct experimental phases per trial:
  - **Baseline**: No-feedback performance measurement
  - **Explore**: Learning phase with real-time feedback
  - **BestPerf**: Performance test with feedback
  - **Instructed**: Guided performance phase
- **Feedback Systems**: Three feedback modalities (Operation, Action, Task)
- **Performance Metrics**: Three measurement types (Time, Distance, MaxSpeed)
- **Segment Tracking**: Automated ID generation for data analysis (PPCCMMTT encoding)
- **Pattern Sequences**: Four predefined mole patterns (A, B, C, D) with 10 targets each

## Requirements

- Python 3.x (tested with Python 3.12)
- Tkinter (bundled with standard Python installations)
- No additional dependencies required

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/WAMPATgenerator.git
   cd WAMPATgenerator
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Mac/Linux
   ```

3. No package installation needed - uses Python standard library only

## Usage

### GUI Mode (Recommended)

**Windows:**
```bash
run.bat
```

**Cross-platform:**
```bash
python generate_wampat_expanded.py
```

Then:
1. Select your study CSV file (or use default `study.csv`)
2. Choose output directory (default: `generated_wampat/`)
3. Click "Generate .wampat files"
4. Review the log output for confirmation

### Command Line Mode

```bash
python generate_wampat_expanded.py path/to/study.csv ./output_folder
```

## Study Design

### Experimental Conditions

| Condition | Feedback Level | Description |
|-----------|----------------|-------------|
| OperationFB | Operation-level | Feedback on complete sequences |
| ActionFB | Action-level | Feedback on individual movements |
| TaskFB | Task-level | Feedback on overall performance |

### Performance Metrics

- **Time**: Task completion duration
- **Distance**: Total movement distance
- **MaxSpeed**: Peak velocity reached

### CSV Format

Expected columns (0-indexed):
```
0: Condition | 1: Metric | 2: Participant | 3: Order | 4: FB Order | 5: Metric Order
6: Baseline  | 7: Explore | 8: BestPerf  | 9: Instructed
```

Cells 6-9 contain pattern sequences (e.g., "AC", "BD", "ABCD")

## File Structure

```
WAMPATgenerator/
├── generate_wampat_expanded.py   # Main generator script
├── study.csv                      # Study design input
├── requirements.txt               # Dependencies (none needed)
├── run.bat                        # Windows launcher
├── exampleWAMPAT.wampat          # Sample output file
├── .gitignore                     # Git ignore rules
└── generated_wampat/              # Output directory (git-ignored)
    ├── 1_ActionFB_Distance.wampat
    ├── 1_ActionFB_MaxSpeed.wampat
    └── ...
```

## Generated File Format

Each `.wampat` file contains:
- Wall configuration (grid size, curvature, angle limits)
- Modifier settings (controller, motor space, feedback mode)
- Four experimental phases with:
  - Segment IDs for data tracking
  - Participant instructions
  - Mole sequences with coordinates and timing
  - Calibration points
  - Performance feedback displays
  - Phase completion markers

## Segment ID Encoding

Format: `PPCCMMTT`
- `PP`: Participant number (01-99)
- `CC`: Condition code (10=Operation, 20=Action, 30=Task)
- `MM`: Metric code (11=Distance, 22=MaxSpeed, 33=Time)
- `TT`: Phase code (00=Baseline, 10=Explore, 20=BestPerf, 30=Instructed)

Example: `13011113` = Participant 13, OperationFB, Distance, Instructed phase


## Contact

For further information you can contact me at: 
alexandrum9400@gmail.com
