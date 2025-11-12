#!/usr/bin/env python3
"""
Configuration settings for Dgraph Monitor
"""

# === Elasticsearch Configuration ===
ES_HOST = "http://localhost:9200"
ES_INDEX_NAME = "graphdb"

# === Dgraph Configuration ===
DGRAPH_HOST = "http://localhost:8180"

# === File Output Configuration ===
OUTPUT_FILE = "dgraph_mutation_latest.json"  # Single file that gets overwritten

# === Monitoring Configuration ===
CHECK_INTERVAL = 30  # Check every 30 seconds
MAX_RETRIES = 20  # Maximum number of connection retry attempts
RETRY_DELAY = 30  # Initial delay between retries in seconds (will increase exponentially)

# === API Configuration ===
API_HOST = "0.0.0.0"
API_PORT = 8006
API_TITLE = "Dgraph Monitor API"
API_DESCRIPTION = "Monitors Elasticsearch and pushes new entries to Dgraph"
API_VERSION = "1.0.0"

# === Logging Configuration ===
LOG_FILE = "dgraph_monitor.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
