#!/usr/bin/env python3
"""
Dgraph client operations
"""

import requests
import json
import time
import logging
from typing import Dict

from config import DGRAPH_HOST, OUTPUT_FILE, MAX_RETRIES, RETRY_DELAY
from schema import DGRAPH_SCHEMA

logger = logging.getLogger(__name__)


def apply_dgraph_schema(retry: bool = True) -> bool:
    """Apply the schema to Dgraph with retry logic"""
    retries = 0
    delay = RETRY_DELAY
    
    while True:
        try:
            response = requests.post(f"{DGRAPH_HOST}/alter", data=DGRAPH_SCHEMA, timeout=10)
            
            # Check response
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('data', {}).get('code') == 'Success':
                        logger.info("✅ Schema applied successfully")
                        return True
                    else:
                        logger.warning(f"Schema response: {result}")
                        return True  # Consider success even with warnings
                except:
                    # If response is not JSON but status 200, still success
                    logger.info("✅ Schema applied successfully (non-JSON response)")
                    return True
            else:
                raise Exception(f"Schema application failed with status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            retries += 1
            if not retry or retries >= MAX_RETRIES:
                logger.error(f"❌ Error applying schema after {retries} attempts: {e}")
                return False
            
            logger.warning(f"⚠️ Failed to apply Dgraph schema (attempt {retries}/{MAX_RETRIES}): {e}")
            logger.info(f"🔄 Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff


def upload_to_dgraph(mutation: Dict, retry: bool = True) -> bool:
    """Save mutation to file and upload to Dgraph with retry logic"""
    try:
        # Save to single file (overwrites each time)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(mutation, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved mutation to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Error saving mutation to file: {e}")
        # Continue even if file save fails
    
    retries = 0
    delay = RETRY_DELAY
    
    while True:
        try:
            # Upload to Dgraph
            response = requests.post(
                f"{DGRAPH_HOST}/mutate?commitNow=true",
                headers={"Content-Type": "application/json"},
                json=mutation,
                timeout=30
            )
            
            logger.info(f"Dgraph response status: {response.status_code}")
            
            # Check if response is successful
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"Dgraph response: {result}")
                    
                    # Check if it's a successful mutation
                    if result.get('data', {}).get('code') == 'Success' or 'uids' in result.get('data', {}):
                        logger.info("✅ Data uploaded to Dgraph successfully")
                        return True
                    else:
                        logger.warning(f"Unexpected Dgraph response: {result}")
                        return True  # Still consider it success if status 200
                except ValueError as json_err:
                    logger.warning(f"Response is not JSON: {response.text[:200]}")
                    # If status 200 but not JSON, still consider success
                    return True
            else:
                raise Exception(f"Dgraph returned status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            retries += 1
            if not retry or retries >= MAX_RETRIES:
                logger.error(f"❌ Error uploading to Dgraph after {retries} attempts: {e}")
                return False
            
            logger.warning(f"⚠️ Failed to upload to Dgraph (attempt {retries}/{MAX_RETRIES}): {e}")
            logger.info(f"🔄 Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
