#!/usr/bin/env python3
"""
Job Application Tracker - Main CLI
"""

import sys
import logging
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from openpyxl import Workbook
from dateutil import parser, tz

import database
from config import (
    LOG_FILE_PATH, LOG_LEVEL, TIMEZONE, DEFAULT_SYNC_DAYS,
    EXCEL_EXPORT_PATH, STATUS_ORDER, REJECTED_OVERRIDES_ALL_EXCEPT_OFFER
)
from classifier import extract_metadata
from graph_client import GraphClient
from deduplicator import find_matching_application, merge_application_data

# Setup logging
LOG_FILE_PATH.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

TZ = tz.gettz(TIMEZONE)


def should_update_status(current_status: str, new_status: str) -> bool:
    """
    Determine if status should be updated based on pipeline rules
    """
    if current_status == new_status:
        return False
    
    current_order = STATUS_ORDER.get(current_status, -1)
    new_order = STATUS_ORDER.get(new_status, -1)
    
    # Rejected overrides everything except Offer
    if new_status == "Rejected":
        if REJECTED_OVERRIDES_ALL_EXCEPT_OFFER:
            return current_status != "Offer"
        return True
    
    # Offer overrides everything
    if new_status == "Offer":
        return True
    
    # Normal pipeline progression (higher order = later stage)
    return new_order > current_order


def process_email(email: Dict[str, Any]) -> bool:
    """
    Process a single email and create/update application and event
    
    Returns True if processed, False if skipped
    """
    message_id = email.get("id")
    internet_message_id = email.get("internetMessageId")
    
    # Check if already processed
    if database.is_email_processed(message_id):
        logger.debug(f"Email {message_id} already processed, skipping")
        return False
    
    # Extract email data
    subject = email.get("subject", "")
    sender_obj = email.get("from", {}).get("emailAddress", {})
    sender = sender_obj.get("address", "")
    received_dt = email.get("receivedDateTime", "")
    body_preview = email.get("bodyPreview", "")
    body_content = email.get("body", {}).get("content", "")
    
    logger.info(f"Processing email: {subject[:50]}... from {sender}")
    
    # Classify and extract metadata
    metadata = extract_metadata(subject, sender, body_content or body_preview)
    
    event_type = metadata["event_type"]
    confidence = metadata["confidence"]
    company = metadata["company"]
    role_title = metadata["role_title"]
    
    # Only process if confidence is at least Low
    if confidence == "Low" and event_type == "Other":
        logger.info(f"Skipping low-confidence 'Other' event")
        database.mark_email_processed(message_id, received_dt, internet_message_id)
        return False
    
    # Try to find matching application
    event_date = received_dt
    applied_date = received_dt if event_type == "Applied" else None
    
    application_id = find_matching_application(company, role_title, None, applied_date)
    
    if not application_id:
        # Create new application
        application_id = database.generate_application_id(company or "", role_title or "", "", applied_date or received_dt)
        
        database.insert_application(
            application_id=application_id,
            source="email",
            company=company,
            role_title=role_title,
            location=None,
            job_url=None,
            status=event_type,
            status_confidence=confidence,
            applied_date=applied_date,
            email_evidence=subject
        )
    else:
        # Update existing application
        existing = database.get_application(application_id)
        
        # Update status if appropriate
        if should_update_status(existing["status"], event_type):
            database.update_application(
                application_id,
                status=event_type,
                status_confidence=confidence
            )
        
        # Fill in missing data
        merge_application_data(
            application_id,
            new_company=company,
            new_role=role_title,
            new_location=None,
            new_job_url=None
        )
    
    # Create event
    database.insert_event(
        application_id=application_id,
        event_type=event_type,
        event_date=event_date,
        evidence_source="email",
        evidence_text=f"Subject: {subject}"
    )
    
    # Mark as processed
    database.mark_email_processed(message_id, received_dt, internet_message_id)
    
    logger.info(f"Created {event_type} event for application {application_id}")
    return True


def cmd_init(args):
    """Initialize database"""
    logger.info("Initializing database...")
    database.init_database()
    print("[OK] Database initialized successfully")
    print(f"  Location: {Path('data/applications.db').absolute()}")


def cmd_sync(args):
    """Sync emails from Outlook"""
    logger.info(f"Starting sync for last {args.since_days} days...")
    
    # Initialize database if needed
    database.init_database()
    
    # Create Graph client
    client = GraphClient()
    
    # Get user info
    try:
        user = client.get_user_info()
        print(f"[OK] Authenticated as: {user.get('userPrincipalName')}")
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        logger.error(f"Authentication failed: {e}")
        return
    
    # Fetch messages
    try:
        messages = client.get_messages(since_days=args.since_days)
        print(f"[OK] Fetched {len(messages)} messages")
    except Exception as e:
        print(f"[ERROR] Failed to fetch messages: {e}")
        logger.error(f"Failed to fetch messages: {e}")
        return
    
    # Process each message
    processed_count = 0
    skipped_count = 0
    
    for email in messages:
        try:
            if process_email(email):
                processed_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            logger.error(f"Error processing email {email.get('id')}: {e}")
            skipped_count += 1
    
    print(f"\n[OK] Sync complete:")
    print(f"  Processed: {processed_count} emails")
    print(f"  Skipped: {skipped_count} emails")


def cmd_import(args):
    """Import from CSV/JSON file"""
    logger.info(f"Importing from {args.file}...")
    
    database.init_database()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] File not found: {args.file}")
        return
    
    imported_count = 0
    
    # Determine format
    if file_path.suffix.lower() == '.csv':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                entries = list(reader)
        except Exception as e:
            print(f"[ERROR] Error reading CSV file: {e}")
            return
    elif file_path.suffix.lower() == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        except Exception as e:
            print(f"[ERROR] Error reading JSON file: {e}")
            return
    else:
        print(f"[ERROR] Unsupported file format: {file_path.suffix}")
        return
    
    if not entries:
        print(f"[ERROR] No entries found in file")
        return
    
    print(f"[OK] Loaded {len(entries)} entries from file")
    
    for entry in entries:
        try:
            company = entry.get('company', '').strip()
            role_title = entry.get('role_title', '').strip()
            location = entry.get('location', '').strip()
            job_url = entry.get('job_url', '').strip()
            source = entry.get('source', 'manual').strip()
            status = entry.get('status', 'Applied').strip()
            applied_date = entry.get('applied_date', '').strip()
            notes = entry.get('notes', '').strip()
            
            # Skip template rows
            if company.lower() in ['example corp', 'techcorp gmbh']:
                continue
            
            # Parse date
            if not applied_date:
                applied_date = database.get_current_timestamp()
            else:
                try:
                    dt = parser.parse(applied_date)
                    applied_date = dt.isoformat()
                except:
                    applied_date = database.get_current_timestamp()
            
            # Find or create application
            application_id = find_matching_application(company, role_title, job_url, applied_date)
            
            if not application_id:
                application_id = database.generate_application_id(company, role_title, job_url, applied_date)
                database.insert_application(
                    application_id=application_id,
                    source=source,
                    company=company,
                    role_title=role_title,
                    location=location,
                    job_url=job_url,
                    status=status,
                    status_confidence="High",
                    applied_date=applied_date,
                    notes=notes
                )
                
                # Create Applied event
                database.insert_event(
                    application_id=application_id,
                    event_type="Applied",
                    event_date=applied_date,
                    evidence_source="manual_import",
                    evidence_text=f"Imported from {file_path.name}"
                )
                
                imported_count += 1
                logger.info(f"Imported application: {company} - {role_title}")
            else:
                # Merge data
                merge_application_data(
                    application_id,
                    new_company=company,
                    new_role=role_title,
                    new_location=location,
                    new_job_url=job_url,
                    new_notes=notes
                )
                logger.info(f"Merged with existing application: {application_id}")
        
        except Exception as e:
            logger.error(f"Error importing entry: {e}")
    
    print(f"\n[OK] Import complete:")
    print(f"  Imported: {imported_count} new applications")


def cmd_export(args):
    """Export to Excel"""
    logger.info(f"Exporting to {args.format}...")
    
    if args.format != 'xlsx':
        print(f"[ERROR] Only xlsx format is currently supported")
        return
    
    # Get data
    applications = database.get_all_applications()
    events = database.get_all_events()
    
    if not applications:
        print("[ERROR] No applications to export")
        return
    
    # Create workbook
    wb = Workbook()
    
    # Applications sheet
    ws_apps = wb.active
    ws_apps.title = "Applications"
    
    # Define column mapping from DB keys to Excel headers
    apps_columns = [
        ('application_id', 'ApplicationID'),
        ('created_at', 'CreatedAt'),
        ('last_updated_at', 'LastUpdatedAt'),
        ('source', 'Source'),
        ('company', 'Company'),
        ('role_title', 'RoleTitle'),
        ('location', 'Location'),
        ('job_url', 'JobURL'),
        ('status', 'Status'),
        ('status_confidence', 'StatusConfidence'),
        ('applied_date', 'AppliedDate'),
        ('email_evidence', 'EmailEvidence'),
        ('notes', 'Notes'),
        ('next_follow_up_date', 'NextFollowUpDate')
    ]
    
    # Write headers
    ws_apps.append([header for _, header in apps_columns])
    
    # Write data
    for app in applications:
        row = [app.get(db_key, '') or '' for db_key, _ in apps_columns]
        ws_apps.append(row)
    
    # Events sheet
    ws_events = wb.create_sheet("Events")
    
    events_columns = [
        ('event_id', 'EventID'),
        ('application_id', 'ApplicationID'),
        ('event_type', 'EventType'),
        ('event_date', 'EventDate'),
        ('evidence_source', 'EvidenceSource'),
        ('evidence_text', 'EvidenceText')
    ]
    
    # Write headers
    ws_events.append([header for _, header in events_columns])
    
    # Write data
    for event in events:
        row = [event.get(db_key, '') or '' for db_key, _ in events_columns]
        ws_events.append(row)
    
    # Save workbook
    output_path = Path(EXCEL_EXPORT_PATH)
    output_path.parent.mkdir(exist_ok=True)
    wb.save(output_path)
    
    print(f"[OK] Exported to: {output_path.absolute()}")
    print(f"  Applications: {len(applications)}")
    print(f"  Events: {len(events)}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Job Application Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # init command
    parser_init = subparsers.add_parser('init', help='Initialize database')
    parser_init.set_defaults(func=cmd_init)
    
    # sync command
    parser_sync = subparsers.add_parser('sync', help='Sync emails from Outlook')
    parser_sync.add_argument('--since-days', type=int, default=DEFAULT_SYNC_DAYS,
                            help=f'Days to sync (default: {DEFAULT_SYNC_DAYS})')
    parser_sync.set_defaults(func=cmd_sync)
    
    # import command
    parser_import = subparsers.add_parser('import', help='Import from CSV/JSON')
    parser_import.add_argument('--file', required=True, help='File to import')
    parser_import.set_defaults(func=cmd_import)
    
    # export command
    parser_export = subparsers.add_parser('export', help='Export to file')
    parser_export.add_argument('--format', default='xlsx', choices=['xlsx'],
                              help='Export format (default: xlsx)')
    parser_export.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()