"""
Microsoft Graph API client for reading Outlook emails
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

import msal
import requests
from dateutil import parser, tz

from config import (
    CLIENT_ID, GRAPH_SCOPES, GRAPH_AUTHORITY, GRAPH_ENDPOINT,
    TOKEN_CACHE_PATH, MAX_EMAILS_PER_REQUEST, TIMEZONE
)

logger = logging.getLogger(__name__)

TZ = tz.gettz(TIMEZONE)


class GraphClient:
    """Microsoft Graph API client with Device Code Flow"""
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.authority = GRAPH_AUTHORITY
        self.scopes = GRAPH_SCOPES
        self.token_cache = self._load_token_cache()
        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self.token_cache
        )
    
    def _load_token_cache(self) -> msal.SerializableTokenCache:
        """Load token cache from file"""
        cache = msal.SerializableTokenCache()
        if TOKEN_CACHE_PATH.exists():
            with open(TOKEN_CACHE_PATH, 'r') as f:
                cache.deserialize(f.read())
        return cache
    
    def _save_token_cache(self):
        """Save token cache to file"""
        if self.token_cache.has_state_changed:
            TOKEN_CACHE_PATH.parent.mkdir(exist_ok=True)
            with open(TOKEN_CACHE_PATH, 'w') as f:
                f.write(self.token_cache.serialize())
    
    def get_access_token(self) -> str:
        """Get access token, prompting for device code if needed"""
        # Try to get token silently first
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
            if result and "access_token" in result:
                logger.info("Token acquired silently")
                return result["access_token"]
        
        # Device code flow
        logger.info("Starting device code flow authentication...")
        flow = self.app.initiate_device_flow(scopes=self.scopes)
        
        if "user_code" not in flow:
            raise Exception(f"Failed to create device flow: {flow.get('error_description')}")
        
        print("\n" + "="*60)
        print("AUTHENTICATION REQUIRED")
        print("="*60)
        print(flow["message"])
        print("="*60 + "\n")
        
        # Wait for user to authenticate
        result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" not in result:
            raise Exception(f"Authentication failed: {result.get('error_description')}")
        
        self._save_token_cache()
        logger.info("Authentication successful")
        return result["access_token"]
    
    def _make_request(self, url: str, params: Optional[Dict] = None, retry_count: int = 3) -> Dict[str, Any]:
        """Make Graph API request with retry and backoff"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                if response.status_code == 401:  # Token expired
                    logger.info("Token expired, refreshing...")
                    token = self.get_access_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception("Max retries exceeded")
    
    def get_messages(self, since_days: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch messages from inbox with pagination
        
        Returns list of message objects with: id, subject, from, receivedDateTime, bodyPreview, body
        """
        since_date = (datetime.now(TZ) - timedelta(days=since_days)).isoformat()
        
        url = f"{GRAPH_ENDPOINT}/me/messages"
        params = {
            "$filter": f"receivedDateTime ge {since_date}",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,internetMessageId",
            "$orderby": "receivedDateTime desc",
            "$top": MAX_EMAILS_PER_REQUEST
        }
        
        all_messages = []
        
        logger.info(f"Fetching messages from last {since_days} days...")
        
        while url:
            data = self._make_request(url, params)
            messages = data.get("value", [])
            all_messages.extend(messages)
            
            logger.info(f"Fetched {len(messages)} messages (total: {len(all_messages)})")
            
            # Get next page
            url = data.get("@odata.nextLink")
            params = None  # Next link already has params
        
        logger.info(f"Total messages fetched: {len(all_messages)}")
        return all_messages
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user info"""
        url = f"{GRAPH_ENDPOINT}/me"
        return self._make_request(url)