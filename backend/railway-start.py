"""
Railway-optimized startup script for VoiceAI Backend
"""
import os
import logging
from multitenant_saas_app import app

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Railway configuration
PORT = int(os.environ.get("PORT", 8000))
HOST = "0.0.0.0"

if __name__ == "__main__":
    logger.info(f"🚀 Starting VoiceAI SaaS Platform on Railway")
    logger.info(f"📡 Server: {HOST}:{PORT}")
    logger.info(f"🌍 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    
    import uvicorn
    uvicorn.run(
        "multitenant_saas_app:app",
        host=HOST,
        port=PORT,
        log_level="info",
        access_log=True
    )