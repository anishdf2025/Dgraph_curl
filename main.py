#!/usr/bin/env python3
"""
Main FastAPI application - Entry point
"""

import asyncio
import logging
from fastapi import FastAPI

from config import API_HOST, API_PORT, API_TITLE, API_DESCRIPTION, API_VERSION, LOG_FILE, LOG_LEVEL, LOG_FORMAT
from config import ES_HOST, DGRAPH_HOST, CHECK_INTERVAL, MAX_RETRIES, RETRY_DELAY
from models import monitor_state
from api_endpoints import root, get_status, start_monitoring, stop_monitoring, process_now, get_stats
from monitor import monitor_and_process

# === Setup Logging ===
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === FastAPI App ===
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

# === Register Routes ===
app.add_api_route("/", root, methods=["GET"])
app.add_api_route("/status", get_status, methods=["GET"])
app.add_api_route("/start", start_monitoring, methods=["POST"])
app.add_api_route("/stop", stop_monitoring, methods=["POST"])
app.add_api_route("/process-now", process_now, methods=["POST"])
app.add_api_route("/stats", get_stats, methods=["GET"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("=" * 70)
    logger.info(f"🚀 {API_TITLE} Started")
    logger.info("=" * 70)
    logger.info(f"Elasticsearch: {ES_HOST}")
    logger.info(f"Dgraph: {DGRAPH_HOST}")
    logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Max Retries: {MAX_RETRIES}")
    logger.info(f"Initial Retry Delay: {RETRY_DELAY} seconds (exponential backoff)")
    logger.info("=" * 70)
    
    # Auto-start monitoring (even if Dgraph/ES is down - will retry in background)
    logger.info("🔄 Auto-starting monitoring with automatic retry...")
    monitor_state["is_running"] = True
    asyncio.create_task(monitor_and_process())
    logger.info("✅ Monitoring task started! Will automatically retry connections if services are down.")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    monitor_state["is_running"] = False
    logger.info("=" * 70)
    logger.info(f"🛑 {API_TITLE} Stopped")
    logger.info(f"Total documents processed: {monitor_state['total_processed']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
