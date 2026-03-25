# WAM2026Data Folder Reset Runbook

Use this runbook when you regenerate WAMPAT files and want the data folder structure rebuilt safely.

## Goal

Prepare a fresh top-level test structure in WAM2026Data based on generated WAMPAT files, while preserving existing data by archiving it.

## Canonical Paths

- Data root: C:\Users\biho\OneDrive - Aalborg Universitet\Documents\WAM2026Data
- WAMPAT source folder: C:\Users\biho\OneDrive - Aalborg Universitet\Documents\GitHub\WAMPATGenerator\generated_wampat

## Rules

1. Never delete existing populated data.
2. Leave .stfolder untouched (Syncthing program folder).
3. Archive old top-level data into PilotTestData.
4. Recreate top-level participant folders 1 through 24.
5. For each participant, create subfolders from WAMPAT names in generated_wampat.

## Expected Top Level After Reset

- .stfolder
- 1
- 2
- ...
- 24
- PilotTestData

## Archive Convention

- Create: WAM2026Data\PilotTestData
- Create timestamped archive folder:
  - WAM2026Data\PilotTestData\Archive_YYYYMMDD_HHMMSS
- Move existing top-level items into that archive folder,
  except:
  - .stfolder
  - PilotTestData

## Rebuild Logic From WAMPAT Filenames

WAMPAT files follow this naming pattern:

Participant_Condition_Metric.wampat

Example:

1_ActionFB_Distance.wampat

From each file:

- Participant folder: 1
- Subfolder name: ActionFB_Distance

Create all needed subfolders under each participant.

## Final Structure Example

WAM2026Data\1\ActionFB_Distance
WAM2026Data\1\ActionFB_MaxSpeed
WAM2026Data\1\ActionFB_Time
WAM2026Data\1\OperationFB_Distance
WAM2026Data\1\OperationFB_MaxSpeed
WAM2026Data\1\OperationFB_Time
WAM2026Data\1\TaskFB_Distance
WAM2026Data\1\TaskFB_MaxSpeed
WAM2026Data\1\TaskFB_Time

## Notes

- Keep any odd/legacy naming in archived data unchanged.
- New structure should use normalized names from generated_wampat files.
- If no .wampat files are found, stop and report the issue.

## How To Ask Later

If you want this procedure run again, ask:

Please run the reset procedure from WAM2026Data_Folder_Reset_Runbook.md
