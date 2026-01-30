# Job Application Tracker

A comprehensive job application tracking system that automatically monitors your Outlook.com emails for application-related events and provides a Chrome/Edge extension for manual capture from job sites.

## Features

- 🔄 **Automatic Email Sync**: Reads your Outlook.com inbox via Microsoft Graph API
- 🤖 **Smart Classification**: Detects Applied/Rejected/Interview/Offer events using keyword heuristics
- 💾 **Local SQLite Database**: All data stored locally on your machine
- 📊 **Excel Export**: Export to `.xlsx` with Applications and Events sheets
- 🌐 **Browser Extension**: Manual capture from LinkedIn, Indeed, StepStone, XING, and any site
- 🔍 **Deduplication**: Intelligent matching and merging of applications
- 🧪 **Tested**: Includes pytest test suite
- 🔄 **CI/CD Ready**: GitHub Actions workflow included

## Requirements

- Windows 10/11
- Python 3.11 or higher
- Microsoft account (outlook.com, outlook.live.com, hotmail.com)
- Chrome or Edge browser (for extension)

## Setup Instructions

### 1. Create GitHub Repository
```bash
# Clone or download this project
cd job-application-tracker

# Initialize git (if not already initialized)
git init

# Add all files
git add .
git commit -m "Initial commit"

# Create repository on GitHub.com, then:
git remote add origin https://github.com/YOUR_USERNAME/job-application-tracker.git
git branch -M main
git push -u origin main
```

### 2. Azure App Registration

You need to register an application in Azure to access Microsoft Graph API:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill in:
   - **Name**: Job Application Tracker
   - **Supported account types**: Personal Microsoft accounts only
   - **Redirect URI**: Leave blank (we use device code flow)
4. Click **Register**
5. On the app page, copy the **Application (client) ID**
6. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
7. Add these permissions:
   - `Mail.Read`
   - `User.Read`
8. Click **Add permissions** (admin consent not required for personal accounts)
9. Go to **Authentication** → **Advanced settings** → Enable **Allow public client flows** → **Yes** → **Save**

### 3. Configure Application

Create a `.env` file or set environment variable with your client ID:

**Option A: Environment Variable (Recommended)**
```bash
# Windows Command Prompt
set AZURE_CLIENT_ID=your-client-id-here

# Windows PowerShell
$env:AZURE_CLIENT_ID="your-client-id-here"
```

**Option B: Edit config.py directly**
```python
# In config.py, replace:
CLIENT_ID = "YOUR_CLIENT_ID_HERE"
# with:
CLIENT_ID = "your-actual-client-id"
```

⚠️ **WARNING**: Never commit your Client ID to public repositories!

### 4. Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows Command Prompt:
venv\Scripts\activate.bat

# Windows PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 5. Initialize Database
```bash
python tracker.py init
```

This creates the SQLite database at `data/applications.db`.

### 6. First Sync
```bash
python tracker.py sync --since-days 30
```

The first time you run this:
1. You'll see a message with a URL and code
2. Open the URL in your browser
3. Enter the code when prompted
4. Sign in with your Microsoft account
5. Grant permissions
6. Return to the terminal - sync will continue automatically

The authentication token is cached in `state/token_cache.bin` for future use.

### 7. Install Browser Extension

#### Chrome:
1. Open `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The extension icon should appear in your toolbar

#### Edge:
1. Open `edge://extensions/`
2. Enable **Developer mode** (bottom left)
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The extension icon should appear in your toolbar

### 8. Using the Extension

**Manual Capture:**
1. Navigate to a job posting (LinkedIn, Indeed, StepStone, XING, or any site)
2. Click the extension icon
3. Fields will auto-populate if possible
4. Fill in any missing information
5. Click **Save**

**Export from Extension:**
1. Click extension icon
2. Click **Download CSV** or **Download JSON**
3. Save the file to `exports/` folder

**Import to Database:**
```bash
python tracker.py import --file exports/your_export.csv
```

### 9. Export to Excel
```bash
python tracker.py export --format xlsx
```

This creates `data/applications.xlsx` with two sheets:
- **Applications**: All application records
- **Events**: All events (emails, manual captures)

## Usage

### Commands
```bash
# Initialize database
python tracker.py init

# Sync emails from last 30 days (default)
python tracker.py sync

# Sync emails from last 60 days
python tracker.py sync --since-days 60

# Import from CSV/JSON
python tracker.py import --file exports/manual_capture.csv

# Export to Excel
python tracker.py export --format xlsx
```

### Extension Icons

You'll need to add icon files to `extension/icons/`:
- `icon16.png` (16x16)
- `icon48.png` (48x48)
- `icon128.png` (128x128)

You can create simple placeholder icons or use any job/clipboard related icons.

## Configuration

Edit `config.py` to customize:

- **Email classification keywords** (add industry-specific terms)
- **Company/role extraction patterns** (improve regex patterns)
- **Status pipeline order** (change status hierarchy)
- **Merge window** (days for deduplication matching)
- **Timezone** (default: Europe/Berlin)

## Data Model

### Applications Table
- `application_id`: Unique identifier (hash of company+role+url+date)
- `company`: Company name
- `role_title`: Job title
- `location`: Job location
- `job_url`: Job posting URL
- `status`: Applied/Interview/Offer/Rejected/Draft
- `status_confidence`: High/Medium/Low
- `applied_date`: When you applied
- `source`: email/manual/LinkedIn/Indeed/etc
- `notes`: Additional notes

### Events Table
- `event_id`: Auto-increment ID
- `application_id`: Foreign key to applications
- `event_type`: Type of event (Applied/Rejected/Interview/Offer/Other)
- `event_date`: When event occurred
- `evidence_source`: email/manual_import
- `evidence_text`: Email subject or description

## Deduplication Logic

The system uses intelligent matching:

1. **Priority 1**: Exact `job_url` match
2. **Priority 2**: Same `company` + `role_title` within 14 days (configurable)

When a match is found:
- Empty fields are filled with new data
- Existing data is NOT overwritten
- Notes are appended
- Events are always created (never duplicated)

## Troubleshooting

### Authentication Errors

**Error: "AADSTS7000218: The request body must contain the following parameter: 'client_assertion' or 'client_secret'."**
- Solution: Make sure you enabled "Allow public client flows" in Azure app settings

**Error: "AADSTS650053: The application asked for permissions that require user consent."**
- Solution: For personal Microsoft accounts, no admin consent needed. Just sign in when prompted.

**Token expired errors:**
- The system automatically refreshes tokens
- If issues persist, delete `state/token_cache.bin` and re-authenticate

### Parsing Limitations

- **Email classification** is keyword-based and may not catch all variations
- **Company/role extraction** uses regex patterns - may miss non-standard formats
- **Solution**: Use manual extension capture for missed applications

### Extension Not Working

- **Content script not injecting**: Reload the extension and refresh the job page
- **No data extracted**: Fill in fields manually - extension still works for saving
- **CSV download not working**: Check browser's download settings/permissions

### No Emails Found

- Verify you're using the correct Microsoft account
- Check emails are in the Inbox folder
- Try increasing `--since-days` parameter
- Verify emails contain job-related keywords

## Development

### Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_classifier.py -v

# Run with coverage
python -m pytest tests/ -v --cov=. --cov-report=html
```

### Project Structure
```
job-application-tracker/
├── tracker.py          # Main CLI
├── database.py         # Database operations
├── classifier.py       # Email classification
├── graph_client.py     # Microsoft Graph API
├── deduplicator.py     # Deduplication logic
├── config.py           # Configuration
├── extension/          # Browser extension
│   ├── manifest.json
│   ├── popup.html/js
│   ├── background.js
│   └── content/        # Site-specific extractors
└── tests/              # Test suite
```

## Security Notes

⚠️ **NEVER commit these files to Git:**
- `state/token_cache.bin` - Contains authentication tokens
- `data/*.db` - Contains your personal data
- `data/*.xlsx` - Contains your personal data
- Any files with your Azure Client ID if hardcoded

The `.gitignore` file is configured to protect these files.

## License

MIT License - Feel free to modify and use for your own job search!

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review existing GitHub Issues
3. Create a new issue with details about your problem

---

**Good luck with your job search! 🎯**