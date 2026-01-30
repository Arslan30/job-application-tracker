"""
Email classification for job application lifecycle events
"""

import re
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime

from config import CLASSIFICATION_KEYWORDS, COMPANY_PATTERNS, ROLE_PATTERNS

logger = logging.getLogger(__name__)


def classify_email(subject: str, sender: str, body: str) -> Tuple[str, str, float]:
    """
    Classify email and return (event_type, confidence, score)
    
    Returns:
        - event_type: Applied/Rejected/Interview/Offer/Other
        - confidence: High/Medium/Low
        - score: numeric score for ranking
    """
    subject = (subject or "").lower()
    sender = (sender or "").lower()
    body = (body or "").lower()
    
    scores = {
        "Applied": 0,
        "Rejected": 0,
        "Interview": 0,
        "Offer": 0
    }
    
    # Score each category
    for event_type, keywords in CLASSIFICATION_KEYWORDS.items():
        # Subject keywords (weight: 3)
        for kw in keywords.get("subject", []):
            if kw.lower() in subject:
                scores[event_type] += 3
        
        # Sender keywords (weight: 2)
        for kw in keywords.get("sender", []):
            if kw.lower() in sender:
                scores[event_type] += 2
        
        # Body keywords (weight: 1)
        for kw in keywords.get("body", []):
            if kw.lower() in body:
                scores[event_type] += 1
    
    # Find max score
    max_score = max(scores.values())
    
    if max_score == 0:
        return "Other", "Low", 0
    
    # Get event type with max score
    event_type = max(scores, key=scores.get)
    
    # Determine confidence
    if max_score >= 5:
        confidence = "High"
    elif max_score >= 3:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    logger.debug(f"Classified as {event_type} with {confidence} confidence (score: {max_score})")
    
    return event_type, confidence, max_score


def extract_company(subject: str, body: str) -> Optional[str]:
    """Extract company name from email"""
    text = f"{subject} {body}"
    
    for pattern in COMPANY_PATTERNS:
        match = re.search(pattern, text)
        if match:
            company = match.group(1).strip()
            # Clean up
            company = re.sub(r'\s+', ' ', company)
            if len(company) > 3:  # Minimum length
                logger.debug(f"Extracted company: {company}")
                return company
    
    return None


def extract_role(subject: str, body: str) -> Optional[str]:
    """Extract role title from email"""
    text = f"{subject} {body}"
    
    for pattern in ROLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            role = match.group(0).strip()
            # Clean up
            role = re.sub(r'\s+', ' ', role)
            if len(role) > 3:
                logger.debug(f"Extracted role: {role}")
                return role
    
    return None


def extract_metadata(subject: str, sender: str, body: str) -> Dict[str, Optional[str]]:
    """
    Extract all possible metadata from email
    
    Returns dict with: event_type, confidence, company, role_title
    """
    event_type, confidence, score = classify_email(subject, sender, body)
    company = extract_company(subject, body)
    role_title = extract_role(subject, body)
    
    return {
        "event_type": event_type,
        "confidence": confidence,
        "company": company,
        "role_title": role_title,
        "score": score
    }