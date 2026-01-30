# Job Application Tracker

A local-first job application tracking system that automatically monitors your Outlook.com emails for application-related events, supports manual capture from job sites via a Chrome/Edge extension, and provides a Streamlit-based web UI for daily use.

All data stays on your machine. No server, no cloud backend.

---

## Features

- **Automatic Email Sync**
  - Reads Outlook.com / outlook.live.com emails via Microsoft Graph (device code flow)
  - Detects Applied / Interview / Offer / Rejected events using keyword heuristics

- **Manual Capture via Browser Extension**
  - Chrome / Edge extension
  - Works with LinkedIn, Indeed, StepStone, XING, and any site
  - Export captured jobs as CSV or JSON

- **Local SQLite Database**
  - All data stored locally
  - No external services required

- **Streamlit Web UI**
  - View and edit applications
  - Update status, notes, follow-up dates
  - Trigger email sync from UI

- **Excel Export**
  - Export to `.xlsx` with:
    - Applications sheet
    - Events sheet

- **Deduplication**
  - Intelligent merging based on job URL or company + role + time window

---

## Requirements

- Windows 10 / 11
- Python **3.11 or higher** (tested with 3.13)
- Microsoft personal account  
  (`outlook.com`, `outlook.live.com`, `hotmail.com`)
- Chrome or Edge (for extension)

---

## Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/job-application-tracker.git
cd job-application-tracker
2. Create Virtual Environment
python -m venv venv
venv\Scripts\activate
3. Install Dependencies
pip install -r requirements.txt
Includes:

msal

requests

openpyxl

python-dateutil

streamlit

4. Azure App Registration (Microsoft Graph)
Required to read Outlook emails.

Go to https://portal.azure.com

Azure Active Directory → App registrations → New registration

Settings

Name: Job Application Tracker

Supported account types: Personal Microsoft accounts only

Redirect URI: Leave empty (device code flow)

Copy Application (client) ID

API permissions:

Microsoft Graph → Delegated

Mail.Read

User.Read

Authentication → Advanced settings
Enable Allow public client flows → Save

5. Configure Client ID
Option A (Recommended): Environment Variable
set AZURE_CLIENT_ID=your-client-id-here
Option B: Edit config.py (local only)
CLIENT_ID = "your-client-id-here"
Never commit your real Client ID.

6. Initialize Database
python tracker.py init
Creates:

data/applications.db
7. First Email Sync (CLI)
python tracker.py sync --since-days 30
First run:

A login URL and code are shown

Open the URL, enter the code

Sign in and grant permissions

Sync continues automatically

Tokens are cached locally in state/ (gitignored).

Streamlit UI (Recommended Daily Use)
Start UI (Windows-safe)
run_ui.bat
Or manually:

venv\Scripts\python -m streamlit run ui.py
UI runs at:

http://127.0.0.1:8501
From the UI you can:
View all applications

Edit status, notes, follow-up date

Trigger email sync

Export to Excel

Browser Extension Setup
Chrome / Edge
Open:

Chrome: chrome://extensions/

Edge: edge://extensions/

Enable Developer mode

Click Load unpacked

Select the extension/ folder

Typical Workflow
When you apply for a job
Automatic (email-based)

Apply normally

Confirmation email arrives

Run email sync (UI or CLI)

Application is created automatically

Manual

Open job posting

Click extension

Review / fill fields

Export CSV → import into tracker

Regular / Weekly Tasks
Review applications in UI

Update statuses after interviews

Add notes

Set follow-up dates

Export Excel for backup/reporting

CLI Commands
# Initialize database
python tracker.py init

# Sync emails (default: 30 days)
python tracker.py sync

# Sync emails (custom range)
python tracker.py sync --since-days 60

# Import manual capture
python tracker.py import --file exports/manual_capture.csv

# Export to Excel
python tracker.py export --format xlsx
Data Model
Applications Table
application_id

company

role_title

location

job_url

status

status_confidence

applied_date

source

notes

next_follow_up_date

Events Table
event_id

application_id

event_type

event_date

evidence_source

evidence_text

Deduplication Logic
Exact job URL match

Same company + role within configurable time window

Rules:

Existing data is preserved

Missing fields are filled

Notes are appended

Events are always added

Troubleshooting
Email sync fails
Ensure UI is started via venv\Scripts\python

Delete state/ token cache and re-authenticate if needed

Unicode errors on Windows
Fixed: project uses ASCII-only console output

UI package errors
Ensure subprocesses use sys.executable

Always launch UI via run_ui.bat

Project Structure
job-application-tracker/
├── tracker.py        # CLI
├── ui.py             # Streamlit UI
├── run_ui.bat        # Windows UI launcher
├── database.py
├── classifier.py
├── graph_client.py
├── deduplicator.py
├── config.py
├── extension/
├── data/             # Local DB (gitignored)
├── state/            # Token cache (gitignored)
├── exports/
└── tests/
Security Notes
The following are never committed (enforced by .gitignore):

state/* (auth tokens)

data/*.db

data/*.xlsx

real exports

venv/

All personal data remains local.

License
MIT License — free to use and modify for your own job search.