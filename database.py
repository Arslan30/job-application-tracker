"""
Database operations for Job Application Tracker
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from config import DATABASE_PATH, TIMEZONE
from dateutil import tz

logger = logging.getLogger(__name__)

# Timezone
TZ = tz.gettz(TIMEZONE)


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Applications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_updated_at TEXT NOT NULL,
            source TEXT,
            company TEXT,
            role_title TEXT,
            location TEXT,
            job_url TEXT,
            status TEXT NOT NULL,
            status_confidence TEXT,
            applied_date TEXT,
            email_evidence TEXT,
            notes TEXT,
            next_follow_up_date TEXT
        )
    """)
    
    # Events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            evidence_source TEXT,
            evidence_text TEXT,
            FOREIGN KEY (application_id) REFERENCES applications(application_id)
        )
    """)
    
    # Processed emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            graph_message_id TEXT PRIMARY KEY,
            received_at TEXT NOT NULL,
            internet_message_id TEXT
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_company ON applications(company)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_app ON events(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def generate_application_id(company: str, role_title: str, job_url: str, applied_date: str) -> str:
    """
    Generate stable application ID from normalized fields
    """
    # Normalize inputs
    company_norm = (company or "").lower().strip()
    role_norm = (role_title or "").lower().strip()
    url_norm = (job_url or "").lower().strip()
    date_norm = (applied_date or "").strip()
    
    # Create hash input
    hash_input = f"{company_norm}|{role_norm}|{url_norm}|{date_norm}"
    
    # Generate hash
    hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
    return f"app_{hash_obj.hexdigest()[:16]}"


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format with timezone"""
    return datetime.now(TZ).isoformat()


def insert_application(
    application_id: str,
    source: str,
    company: Optional[str],
    role_title: Optional[str],
    location: Optional[str],
    job_url: Optional[str],
    status: str,
    status_confidence: Optional[str],
    applied_date: Optional[str],
    email_evidence: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Insert new application"""
    conn = get_connection()
    cursor = conn.cursor()
    
    now = get_current_timestamp()
    
    try:
        cursor.execute("""
            INSERT INTO applications (
                application_id, created_at, last_updated_at, source, company, 
                role_title, location, job_url, status, status_confidence, 
                applied_date, email_evidence, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id, now, now, source, company, role_title, location,
            job_url, status, status_confidence, applied_date, email_evidence, notes
        ))
        conn.commit()
        logger.info(f"Inserted application {application_id}")
        return True
    except sqlite3.IntegrityError:
        logger.debug(f"Application {application_id} already exists")
        return False
    finally:
        conn.close()


def update_application(
    application_id: str,
    status: Optional[str] = None,
    status_confidence: Optional[str] = None,
    company: Optional[str] = None,
    role_title: Optional[str] = None,
    location: Optional[str] = None,
    job_url: Optional[str] = None,
    email_evidence: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Update existing application"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = []
    params = []
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if status_confidence is not None:
        updates.append("status_confidence = ?")
        params.append(status_confidence)
    if company is not None:
        updates.append("company = ?")
        params.append(company)
    if role_title is not None:
        updates.append("role_title = ?")
        params.append(role_title)
    if location is not None:
        updates.append("location = ?")
        params.append(location)
    if job_url is not None:
        updates.append("job_url = ?")
        params.append(job_url)
    if email_evidence is not None:
        updates.append("email_evidence = ?")
        params.append(email_evidence)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    if not updates:
        conn.close()
        return False
    
    updates.append("last_updated_at = ?")
    params.append(get_current_timestamp())
    params.append(application_id)
    
    query = f"UPDATE applications SET {', '.join(updates)} WHERE application_id = ?"
    
    cursor.execute(query, params)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    
    if updated:
        logger.info(f"Updated application {application_id}")
    
    return updated


def get_application(application_id: str) -> Optional[Dict[str, Any]]:
    """Get application by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def insert_event(
    application_id: str,
    event_type: str,
    event_date: str,
    evidence_source: str,
    evidence_text: Optional[str] = None
) -> int:
    """Insert event and return event_id"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events (application_id, event_type, event_date, evidence_source, evidence_text)
        VALUES (?, ?, ?, ?, ?)
    """, (application_id, event_type, event_date, evidence_source, evidence_text))
    
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"Inserted event {event_id} for application {application_id}")
    return event_id


def mark_email_processed(graph_message_id: str, received_at: str, internet_message_id: Optional[str] = None):
    """Mark email as processed"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO processed_emails (graph_message_id, received_at, internet_message_id)
            VALUES (?, ?, ?)
        """, (graph_message_id, received_at, internet_message_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already processed
    finally:
        conn.close()


def is_email_processed(graph_message_id: str) -> bool:
    """Check if email already processed"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_emails WHERE graph_message_id = ?", (graph_message_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_all_applications() -> List[Dict[str, Any]]:
    """Get all applications"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_events() -> List[Dict[str, Any]]:
    """Get all events"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]