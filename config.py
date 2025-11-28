import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # On Heroku, we read these from the "Config Vars" settings
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Standard Telegram API URL
    BASE_URL = os.getenv("BASE_URL", "https://api.telegram.org/bot")
    
    # Heroku has tight storage limits, so we stick to standard API limits (20MB)
    MAX_FILE_SIZE_MB = 20
    
    # Processing Timeouts
    TIMEOUT = 120
    
    # JSON DB (Note: On Heroku free tier, this file clears when the dyno restarts. 
    # For permanent storage on Heroku, you would typically need a Postgres database)
    DB_FILE = "user_data.json"
    
    # Watermark Settings
    DEFAULT_WATERMARK = "@WatermarkedBot"
    FONT_SIZE = 36
    OPACITY = 128
    MARGIN_X = 20
    MARGIN_Y = 20
