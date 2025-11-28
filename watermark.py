import ffmpeg
import logging
import os
from PIL import Image, ImageDraw, ImageFont
from config import Config

logger = logging.getLogger(__name__)

def get_color_rgb(color: str):
    """Map color name to RGB tuple."""
    color = color.lower()
    if color == "black":
        return (0, 0, 0)
    elif color == "white":
        return (255, 255, 255)
    else:
        logger.warning(f"Invalid color '{color}', defaulting to white")
        return (255, 255, 255)

def create_text_watermark(text: str, output_path: str, color: str = "white"):
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
        rgb_color = get_color_rgb(color)
        draw.text((15, 15), text, font=font, fill=(*rgb_color, Config.OPACITY))

        img.save(output_path, "PNG")
        return True
    except Exception as e:
        logger.error(f"Error creating text image: {e}")
        return False

def process_video(input_video: str, output_video: str, watermark_img: str):
    try:
        # Validate input
        if not os.path.exists(input_video) or os.path.getsize(input_video) == 0:
            raise ValueError("Invalid input file")
        
        probe = ffmpeg.probe(input_video)
        if 'streams' not in probe or not any(s['codec_type'] == 'video' for s in probe['streams']):
            raise ValueError("Invalid video file: No video stream")
        
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        in_file = ffmpeg.input(input_video)
        overlay_file = ffmpeg.input(watermark_img)

        # Fix aspect ratio to prevent distortion
        video = in_file.video.filter('scale', f'iw*sar:ih').filter('setsar', '1').overlay(
            overlay_file, 
            x=f"main_w-overlay_w-{Config.MARGIN_X}", 
            y=f"main_h-overlay_h-{Config.MARGIN_Y}"
        )

        output_args = {
            'vcodec': 'libx264',
            'preset': 'ultrafast',  # Faster for large files
            'crf': 26,              # Balance quality/size
            'movflags': '+faststart',
            'threads': 0,           # Use all cores
            'maxrate': '5M',        # Cap bitrate
            'bufsize': '10M'
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
    except Exception as e:
        logger.error(f"Unexpected error in process_video: {e}")
        raise e
