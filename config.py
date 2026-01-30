"""
Configuration for Job Application Tracker
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Directories
DATA_DIR = BASE_DIR / "data"
STATE_DIR = BASE_DIR / "state"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"

# Ensure directories exist
for dir_path in [DATA_DIR, STATE_DIR, LOGS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "applications.db"

# State files
TOKEN_CACHE_PATH = STATE_DIR / "token_cache.bin"
STATE_FILE_PATH = STATE_DIR / "state.json"

# Export files
EXCEL_EXPORT_PATH = DATA_DIR / "applications.xlsx"

# Logging
LOG_FILE_PATH = LOGS_DIR / "tracker.log"
LOG_LEVEL = "INFO"

# Timezone
TIMEZONE = "Europe/Berlin"

# Microsoft Graph API
GRAPH_SCOPES = ["Mail.Read", "User.Read"]
GRAPH_AUTHORITY = "https://login.microsoftonline.com/consumers"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

# Azure App Registration (user must fill these)
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")

# Email processing
DEFAULT_SYNC_DAYS = 30
MAX_EMAILS_PER_REQUEST = 50

# Status pipeline order (lower = earlier stage)
STATUS_ORDER = {
    "Draft": 0,
    "Applied": 1,
    "Interview": 2,
    "Offer": 3,
    "Rejected": 99,  # Special handling
    "Other": -1
}

# Status transition rules
REJECTED_OVERRIDES_ALL_EXCEPT_OFFER = True

# Deduplication settings
MERGE_WINDOW_DAYS = 14  # Days within which to consider company+role matches as duplicates

# Classification keywords
CLASSIFICATION_KEYWORDS = {
    "Applied": {
        "subject": ["application received", "thank you for applying", "application confirmation", 
                   "we received your application", "bewerbung eingegangen", "bewerbungseingang"],
        "sender": ["noreply", "no-reply", "recruiting", "talent", "hr@", "jobs@", "careers@"],
        "body": ["application has been received", "reviewing your application"]
    },
    "Rejected": {
        "subject": ["unfortunately", "not moving forward", "other candidates", "not selected",
                   "absage", "leider", "andere kandidaten"],
        "sender": ["noreply", "no-reply", "recruiting", "talent", "hr@"],
        "body": ["regret to inform", "not be moving forward", "other candidates", 
                "decided to pursue", "nicht berücksichtigen"]
    },
    "Interview": {
        "subject": ["interview", "next steps", "schedule", "gespräch", "vorstellungsgespräch"],
        "sender": ["recruiting", "talent", "hr@", "team@"],
        "body": ["interview", "schedule a call", "meet with", "talk with", "gespräch", 
                "kennenlernen"]
    },
    "Offer": {
        "subject": ["offer", "congratulations", "welcome to", "angebot", "glückwunsch"],
        "sender": ["hr@", "recruiting", "talent"],
        "body": ["pleased to offer", "offer letter", "welcome to our team", "angebot"]
    }
}

# Company extraction patterns (will match common formats)
COMPANY_PATTERNS = [
    r"(?:from|at|with|bei)\s+([A-Z][A-Za-z0-9\s&]+(?:GmbH|AG|Inc|LLC|Ltd|Corporation|Corp)?)",
    r"([A-Z][A-Za-z0-9\s&]+(?:GmbH|AG|Inc|LLC|Ltd|Corporation|Corp))",
]

# Role extraction patterns
ROLE_PATTERNS = [
    r"(?:position|role|for|als)\s+([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Designer|Consultant))",
    r"(Senior|Junior|Lead|Principal|Staff)?\s*(Software|Data|Product|Project|Marketing|Sales)\s+(Engineer|Developer|Manager|Analyst|Designer|Scientist)",
]