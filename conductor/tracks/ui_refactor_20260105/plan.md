# Plan: UI Refactor & History Feature

## Goal
Refactor the Android App UI to simplify the fetching process, introduce a history feature, and allow saving data as Zip files.

## Context
Currently, the app has separate buttons for "Morning" and "Evening" reports. The user wants a unified experience where the app simply "fetches what is available". Additionally, users should be able to view past reports (History) and save reports as Zip files.

## Phases

### Phase 1: Analysis & Preparation
- [x] Analyze `MainActivity.kt` and data fetching logic.
- [x] Determine storage strategy for History (SharedPrefs vs File System vs Room). *Decision: File System (JSON files) + simple listing.*

### Phase 2: UI/UX Refactor (Main Screen)
- [x] Remove separate "Fetch Morning" / "Fetch Evening" buttons.
- [x] Implement a single "Refresh" / "Fetch" mechanism via **FloatingActionButton (FAB)** in the bottom-right corner.
- [x] Move "History" and "Save Zip" to the Toolbar as icons.
- [x] Update UI to display the latest content automatically or show a list of today's reports.

### Phase 3: History Feature
- [x] Create a "History" screen/list.
- [x] Implement logic to save fetched reports locally with timestamps.
- [x] Implement logic to read and display the list of saved reports.
- [x] Allow clicking a history item to view it.

### Phase 4: Zip Save Feature
- [x] Add a "Save" icon to the report view (Toolbar/Menu).
- [x] Implement logic to download the corresponding Zip file from the server (if remote) or package local content (if local).
    -   *Note:* The cloud produces `morning_report.zip` and `evening_report.zip`. We should download these.

## Task List

### Step 1: Cleanup & Setup
- [x] Remove `btnFetchMorning` and `btnFetchEvening` from layout and code.
- [x] Add a generic `Toolbar` with "History" and "Save" actions (or place them appropriately).

### Step 2: Logic - Generic Fetch
- [x] Modify `fetchReport` to try fetching available reports for the day (e.g., check `morning.json` AND `evening.json`).
- [x] Store successful fetches locally (e.g., `files/history/YYYY-MM-DD_type.json`).

### Step 3: Logic - History
- [x] Create `HistoryActivity` (or Fragment).
- [x] Implement `HistoryAdapter` to list files in `files/history/`.

### Step 4: Logic - Save Zip
- [x] Implement `downloadZip(type: String)` which downloads the zip to the user's public "Downloads" folder.

### Step 5: Integration
- [x] Connect "History" button to `HistoryActivity`.
- [x] Connect "Save" icon to `downloadZip`.