import os
import logging
import asyncio
import tempfile
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    filters
)

from config import Config
from storage import db
import watermark

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Send me a video (max 20MB) and I'll watermark it.\n"
        "Use /setwatermark <text> to change settings."
    )

async def set_watermark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setwatermark YourName")
        return
    text = " ".join(context.args)
    db.set_watermark(user_id, text)
    await update.message.reply_text(f"✅ Watermark updated: `{text}`", parse_mode='Markdown')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 1. Check Input
    if update.message.video:
        file_obj = update.message.video
    elif update.message.document and 'video' in update.message.document.mime_type:
        file_obj = update.message.document
    else:
        await update.message.reply_text("Please send a valid video file.")
        return

    # 2. Check Size (Heroku/Standard API Limit)
    if file_obj.file_size > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ File too big! Max size is {Config.MAX_FILE_SIZE_MB}MB.")
        return

    status_msg = await update.message.reply_text("⏳ Processing...")

    # 3. Process with Temp Directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            input_path = os.path.join(temp_dir, "input.mp4")
            output_path = os.path.join(temp_dir, "output.mp4")
            watermark_path = os.path.join(temp_dir, "wm.png")

            # Download
            new_file = await context.bot.get_file(file_obj.file_id)
            await new_file.download_to_drive(input_path)

            # Generate Watermark
            user_text = db.get_watermark(user_id)
            await asyncio.to_thread(watermark.create_text_watermark, user_text, watermark_path)

            # Encode Video
            await asyncio.to_thread(watermark.process_video, input_path, output_path, watermark_path)

            # Upload
            await status_msg.edit_text("⬆️ Uploading...")
            await update.message.reply_video(
                video=open(output_path, 'rb'),
                caption="Here is your video! ✨"
            )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Error: {e}")
            await status_msg.edit_text("❌ Failed to process video.")

def main():
    if not Config.BOT_TOKEN:
        print("Error: BOT_TOKEN is not set!")
        return

    application = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwatermark", set_watermark_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
