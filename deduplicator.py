"""
Deduplication and merging logic for applications
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dateutil import parser, tz

from config import MERGE_WINDOW_DAYS, TIMEZONE
from database import get_connection, get_application, update_application

logger = logging.getLogger(__name__)

TZ = tz.gettz(TIMEZONE)


def find_matching_application(
    company: Optional[str],
    role_title: Optional[str],
    job_url: Optional[str],
    applied_date: Optional[str]
) -> Optional[str]:
    """
    Find existing application that matches the criteria
    
    Priority:
    1. Exact job_url match
    2. Company + role match within merge window
    
    Returns: application_id if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Priority 1: URL match
    if job_url:
        cursor.execute(
            "SELECT application_id FROM applications WHERE job_url = ? AND job_url != ''",
            (job_url,)
        )
        row = cursor.fetchone()
        if row:
            conn.close()
            logger.info(f"Found match by job_url: {row[0]}")
            return row[0]
    
    # Priority 2: Company + Role match within window
    if company and role_title and applied_date:
        try:
            applied_dt = parser.parse(applied_date)
            window_start = (applied_dt - timedelta(days=MERGE_WINDOW_DAYS)).isoformat()
            window_end = (applied_dt + timedelta(days=MERGE_WINDOW_DAYS)).isoformat()
            
            cursor.execute("""
                SELECT application_id FROM applications 
                WHERE company = ? 
                AND role_title = ?
                AND applied_date >= ?
                AND applied_date <= ?
                LIMIT 1
            """, (company, role_title, window_start, window_end))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                logger.info(f"Found match by company+role+date: {row[0]}")
                return row[0]
        except Exception as e:
            logger.warning(f"Error parsing date for merge: {e}")
    
    conn.close()
    return None


def merge_application_data(
    application_id: str,
    new_company: Optional[str],
    new_role: Optional[str],
    new_location: Optional[str],
    new_job_url: Optional[str],
    new_notes: Optional[str] = None
) -> bool:
    """
    Merge new data into existing application
    Only updates fields that are currently empty
    """
    existing = get_application(application_id)
    if not existing:
        return False
    
    updates = {}
    
    # Only fill in blanks
    if not existing.get("company") and new_company:
        updates["company"] = new_company
    
    if not existing.get("role_title") and new_role:
        updates["role_title"] = new_role
    
    if not existing.get("location") and new_location:
        updates["location"] = new_location
    
    if not existing.get("job_url") and new_job_url:
        updates["job_url"] = new_job_url
    
    # Always append notes if provided
    if new_notes:
        existing_notes = existing.get("notes") or ""
        if existing_notes:
            updates["notes"] = f"{existing_notes}\n{new_notes}"
        else:
            updates["notes"] = new_notes
    
    if updates:
        update_application(application_id, **updates)
        logger.info(f"Merged data into application {application_id}: {list(updates.keys())}")
        return True
    
    return False