import ffmpeg
import logging
import os
from PIL import Image, ImageDraw, ImageFont
from config import Config

logger = logging.getLogger(__name__)

def create_text_watermark(text: str, output_path: str):
    try:
        # On Heroku Linux, arial.ttf might not exist, so we use default or DejaVu if available
        try:
            # Try loading a common linux font, fallback to default
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", Config.FONT_SIZE)
        except IOError:
            font = ImageFont.load_default()

        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        width = text_width + 30
        height = text_height + 30
        
        img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((15, 15), text, font=font, fill=(255, 255, 255, Config.OPACITY))

        img.save(output_path, "PNG")
        return True
    except Exception as e:
        logger.error(f"Error creating text image: {e}")
        return False

def process_video(input_video: str, output_video: str, watermark_img: str):
    try:
        probe = ffmpeg.probe(input_video)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        if not video_stream:
            raise ValueError("No video stream found")

        in_file = ffmpeg.input(input_video)
        overlay_file = ffmpeg.input(watermark_img)

        video = in_file.overlay(
            overlay_file, 
            x=f"main_w-overlay_w-{Config.MARGIN_X}", 
            y=f"main_h-overlay_h-{Config.MARGIN_Y}"
        )

        output_args = {
            'vcodec': 'libx264',
            'preset': 'veryfast', # Faster processing for Heroku
            'crf': 26,            # Slightly lower quality to save file size
            'movflags': '+faststart'
        }

        if audio_stream:
            stream = ffmpeg.output(video, in_file.audio, output_video, **output_args)
        else:
            stream = ffmpeg.output(video, output_video, **output_args)

        stream.run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        return True

    except ffmpeg.Error as e:
        logger.error(f"FFmpeg Error: {e.stderr.decode('utf8')}")
        raise e
