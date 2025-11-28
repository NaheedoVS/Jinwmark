import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # On Heroku, we read these from the "Config Vars" settings
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Prioritize local Bot API; no HTTPS fallback
    BASE_URL = os.getenv("BASE_URL") or "http://telegram-bot-api:8081/bot"
    
    # Increased for 2GB support
    MAX_FILE_SIZE_MB = 2000
    
    # Processing Timeouts (increased for large files)
    TIMEOUT = 3000  # 50 minutes
    
    # JSON DB (Note: On Heroku free tier, this file clears when the dyno restarts. 
    # For permanent storage on Heroku, you would typically need a Postgres database)
    DB_FILE = "user_data.json"
    
    # Watermark Settings
    DEFAULT_WATERMARK = "Pglinsan"
    FONT_SIZE = 36
    OPACITY = 128
    MARGIN_X = 20
    MARGIN_Y = 20
