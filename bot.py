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
        "👋 Hi! Send me a video (max 2GB) and I'll watermark it.\n"
        "Use /setwatermark <text> to change text.\n"
        "Use /setcolor <black|white> to change color."
    )

async def set_watermark_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setwatermark YourName")
        return
    text = " ".join(context.args)
    db.set_watermark(user_id, text)
    await update.message.reply_text(f"✅ Watermark text updated: `{text}`", parse_mode='Markdown')

async def set_color_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /setcolor black or /setcolor white")
        return
    color = context.args[0].lower()
    if color not in ["black", "white"]:
        await update.message.reply_text("❌ Invalid color! Use 'black' or 'white'.")
        return
    db.set_color(user_id, color)
    color_name = "black" if color == "black" else "white"
    await update.message.reply_text(f"✅ Watermark color updated: {color_name}")

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

    logger.info(f"Received file: {file_obj.file_name or 'unknown'}, size: {file_obj.file_size} bytes")

    # 2. Check Size
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

            # Download with timeout
            logger.info("Fetching file info...")
            new_file = await asyncio.wait_for(
                context.bot.get_file(file_obj.file_id),
                timeout=Config.TIMEOUT
            )
            logger.info(f"File path from getFile: {new_file.file_path}")
            
            logger.info("Downloading file...")
            await asyncio.wait_for(
                new_file.download_to_drive(input_path),
                timeout=Config.TIMEOUT * 2
            )
            downloaded_size = os.path.getsize(input_path)
            logger.info(f"Downloaded: {downloaded_size} bytes")
            
            if downloaded_size != file_obj.file_size:
                raise ValueError(f"Size mismatch: expected {file_obj.file_size}, got {downloaded_size}")

            # Generate Watermark
            logger.info("Creating watermark...")
            user_data = db.get_user_data(user_id)
            success = await asyncio.to_thread(
                watermark.create_text_watermark, 
                user_data["text"], 
                watermark_path, 
                user_data["color"]
            )
            if not success:
                raise ValueError("Watermark creation failed")
            logger.info(f"Watermark created ({user_data['color']}): {os.path.getsize(watermark_path)} bytes")

            # Encode Video
            logger.info("Processing video with FFmpeg...")
            await asyncio.wait_for(
                asyncio.to_thread(watermark.process_video, input_path, output_path, watermark_path),
                timeout=Config.TIMEOUT * 5  # Longer for large files
            )
            output_size = os.path.getsize(output_path)
            logger.info(f"Processed: {output_size} bytes")

            # Upload
            await status_msg.edit_text("⬆️ Uploading...")
            logger.info("Uploading processed video...")
            await update.message.reply_video(
                video=open(output_path, 'rb'),
                caption="Here is your video! ✨"
            )
            logger.info("Upload successful")
            await status_msg.delete()

        except asyncio.TimeoutError:
            logger.error("Timeout during processing")
            await status_msg.edit_text("❌ Timeout: Video too large or slow connection.")
        except Exception as e:
            logger.error(f"Detailed error in handle_video: {type(e).__name__}: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Failed: {str(e)[:100]}...")
            if os.path.exists(output_path):
                await update.message.reply_document(document=open(output_path, 'rb'), caption="Partial output")

def main():
    if not Config.BOT_TOKEN:
        print("Error: BOT_TOKEN is not set!")
        return

    # Force HTTP/1.1 for local Bot API compatibility
    application = (
        ApplicationBuilder()
        .token(Config.BOT_TOKEN)
        .http_version('1.1')
        .get_updates_http_version('1.1')
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwatermark", set_watermark_command))
    application.add_handler(CommandHandler("setcolor", set_color_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot is running...")
    logger.info(f"Using BASE_URL: {Config.BASE_URL}")
    application.run_polling()

if __name__ == '__main__':
    main()
