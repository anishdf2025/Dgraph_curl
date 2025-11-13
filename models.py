#!/usr/bin/env python3
"""
Data models and type definitions
"""

from typing import Dict, List, Optional
from datetime import datetime

# === Global State ===
monitor_state = {
    "is_running": False,
    "last_check": None,
    "total_processed": 0,
    "last_batch_size": 0,
    "errors": []
}

# === Global tracking to prevent duplicates ===
global_citations = {}
global_judges = {}
global_advocates = {}
global_outcomes = {}
global_case_durations = {}
global_courts = {}
