"""
ShazamPi Music Plugin for InkyPi
Records audio from a USB microphone, detects music using YAMNet (TFLite),
identifies songs via Shazam, and displays album art with a title overlay.
Falls back to an idle display with weather info when no music is detected.
"""

import asyncio
import csv
import datetime
import io
import json
import logging
import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
ML_MODEL_PATH = os.path.join(PLUGIN_DIR, "ml-model", "1.tflite")
CLASS_MAP_PATH = os.path.join(PLUGIN_DIR, "ml-model", "yamnet_class_map.csv")
DEFAULT_IMAGE_PATH = os.path.join(PLUGIN_DIR, "resources", "default.jpg")

RAW_SAMPLE_RATE = 44100
DOWN_SAMPLE_RATE = 16000
AUDIO_GAIN = 3.0
WEATHER_CACHE_MINUTES = 30
STATUS_FILE = os.path.join(PLUGIN_DIR, "status.json")


class ShazamPi(BasePlugin):
    def __init__(self, config, **deps):
        super().__init__(config, **deps)
        self._interpreter = None
        self._class_names = None
        self._shazam = None
        self._last_song = None
        self._last_weather = None
        self._last_weather_fetch = None
        self._recording_duration = None

    def _set_status(self, stage, detail=""):
        """Write current status to a JSON file for the web UI to poll."""
        try:
            status = {
                "stage": stage,
                "detail": detail,
                "timestamp": time.time(),
            }
            with open(STATUS_FILE, 'w') as f:
                json.dump(status, f)
        except Exception:
            pass  # Non-critical, don't break the pipeline

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = False
        return template_params

    def generate_image(self, settings, device_config):
        logger.info("=== ShazamPi Plugin: Starting ===")
        self._set_status("starting", "Initializing...")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        recording_duration = int(settings.get("recordingDuration", 5))

        # 1. Record audio from USB mic
        self._set_status("recording", f"Recording {recording_duration}s of audio...")
        raw_audio = self._record_audio(recording_duration)

        # 2. Detect music via YAMNet
        self._set_status("detecting", "Analyzing audio for music...")
        confidence = float(settings.get("musicConfidence", 0.2))
        is_music, top_class, top_score = self._detect_music(raw_audio, recording_duration, confidence)
        self._set_status("detected", f"{top_class} ({top_score:.0%})")

        # 3. If music detected, identify via Shazam
        if is_music:
            logger.info("Music detected, identifying via Shazam...")
            self._set_status("identifying", "Music detected! Asking Shazam...")
            song = self._identify_song(raw_audio)
            if song:
                self._last_song = song
                self._shazam_fail_count = 0
                self._set_status("rendering", f"Found: {song['title']} by {song['artist']}")
                return self._render_song(song, dimensions, settings)
            else:
                self._shazam_fail_count = getattr(self, '_shazam_fail_count', 0) + 1
                logger.warning(f"Shazam failed to identify (attempt #{self._shazam_fail_count})")
                self._set_status("unidentified", f"Could not identify song (attempt #{self._shazam_fail_count})")
                return self._render_unidentified(
                    dimensions, settings, device_config, top_class, top_score
                )

        # 4. No music: show idle display
        logger.info("No music detected, showing idle display")
        self._shazam_fail_count = 0
        self._set_status("idle", f"No music detected ({top_class} {top_score:.0%})")
        return self._render_idle(dimensions, settings, device_config)

    # ========== Audio Recording ==========

    def _find_usb_mic(self):
        import sounddevice as sd
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if 'USB' in device['name']:
                return idx
        return None

    def _record_audio(self, recording_duration):
        import sounddevice as sd

        logger.info(f"Recording {recording_duration}s of audio...")

        device_idx = self._find_usb_mic()
        if device_idx is not None:
            sd.default.device = (device_idx, None)
            logger.debug(f"Using USB mic at device index {device_idx}")
        else:
            logger.warning("USB mic not found, using default audio device")

        # Record directly at 16kHz to avoid expensive resampling
        audio = sd.rec(
            int(recording_duration * DOWN_SAMPLE_RATE),
            samplerate=DOWN_SAMPLE_RATE,
            channels=1,
            dtype=np.float32
        )
        sd.wait()

        # Normalize and apply gain
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
        audio = np.clip(audio * AUDIO_GAIN, -1.0, 1.0)

        return np.squeeze(audio)

    # ========== Music Detection (YAMNet) ==========

    def _init_yamnet(self, recording_duration):
        if self._interpreter is not None and self._recording_duration == recording_duration:
            return

        logger.info("Loading YAMNet TFLite model...")
        try:
            from ai_edge_litert.interpreter import Interpreter
            self._interpreter = Interpreter(model_path=ML_MODEL_PATH)
        except (ModuleNotFoundError, ImportError):
            import tflite_runtime.Interpreter as tfl
            self._interpreter = tfl.Interpreter(model_path=ML_MODEL_PATH)

        input_details = self._interpreter.get_input_details()
        self._waveform_input_index = input_details[0]['index']

        output_details = self._interpreter.get_output_details()
        self._scores_output_index = output_details[0]['index']

        self._interpreter.resize_tensor_input(
            self._waveform_input_index,
            [recording_duration * DOWN_SAMPLE_RATE],
            strict=True
        )
        self._interpreter.allocate_tensors()
        self._recording_duration = recording_duration

        # Load class names
        with open(CLASS_MAP_PATH) as f:
            reader = csv.reader(f)
            self._class_names = [row[2] for row in reader]
            self._class_names = self._class_names[1:]  # Skip header

        logger.info("YAMNet model loaded")

    def _detect_music(self, waveform, recording_duration, confidence_threshold):
        self._init_yamnet(recording_duration)

        self._interpreter.set_tensor(self._waveform_input_index, waveform)
        self._interpreter.invoke()

        scores = self._interpreter.get_tensor(self._scores_output_index)
        scores_mean = scores.mean(axis=0)
        top_i = scores_mean.argmax()
        top_class = self._class_names[top_i]
        top_score = float(scores_mean[top_i])

        logger.info(f"YAMNet top class: '{top_class}' (score: {top_score:.3f})")
        is_music = 'Music' in top_class and top_score > confidence_threshold
        return is_music, top_class, top_score

    # ========== Song Identification (Shazam) ==========

    def _identify_song(self, raw_audio):
        import scipy.io.wavfile as wav
        from shazamio import Shazam

        # Convert to WAV buffer
        audio_buffer = io.BytesIO()
        wav.write(audio_buffer, DOWN_SAMPLE_RATE, raw_audio)
        audio_buffer.seek(0)

        # Run Shazam async recognition
        if self._shazam is None:
            self._shazam = Shazam()

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._shazam.recognize(audio_buffer.read())
            )

            if result and 'track' in result:
                track = result['track']
                album_art = track.get('images', {}).get('coverart')
                song = {
                    'title': track.get('title', 'Unknown'),
                    'artist': track.get('subtitle', 'Unknown'),
                    'album_art': album_art,
                }
                logger.info(f"Identified: {song['title']} by {song['artist']}")
                return song

            # Log why Shazam failed
            if result:
                matches = result.get('matches', [])
                logger.warning(f"Shazam returned no track. matches={len(matches)}, keys={list(result.keys())}")
            else:
                logger.warning("Shazam returned empty result")
            return None
        except Exception as e:
            logger.error(f"Shazam identification error: {e}", exc_info=True)
            return None
        finally:
            loop.close()

    # ========== Rendering ==========

    def _render_song(self, song, dimensions, settings):
        fit_mode = settings.get("fitMode", "fit")

        album_art_url = song.get('album_art')
        if album_art_url:
            image = self.image_loader.from_url(
                album_art_url, dimensions, timeout_ms=30000, fit_mode=fit_mode
            )
        else:
            image = None

        if not image:
            image = self.image_loader.from_file(
                DEFAULT_IMAGE_PATH, dimensions, fit_mode=fit_mode
            )

        if image:
            # Add title/artist overlay at bottom
            image = self._add_title_overlay(
                image, song['title'], song.get('artist', '')
            )
            # In fit mode, add rotated "Now Playing..." in the left letterbox bar
            if fit_mode == 'fit':
                image = self._add_now_playing_label(image)

        logger.info("=== ShazamPi Plugin: Song image generated ===")
        return image

    def _add_now_playing_label(self, image):
        """Add rotated 'Now Playing...' text in the left black letterbox bar."""
        img = image.copy()
        width, height = img.size

        # Find the left black bar width by scanning for non-black pixels
        bar_width = 0
        pixels = img.load()
        for x in range(width // 4):
            col_black = all(pixels[x, y] == (0, 0, 0) for y in range(0, height, height // 10))
            if col_black:
                bar_width = x + 1
            else:
                break

        if bar_width < 20:
            return img

        text = "Now Playing..."

        # Find font size that fits text within the display height
        try:
            font_size = max(10, int(bar_width * 0.4))
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
            )
            # Shrink until text fits within height
            tmp_img = Image.new('RGBA', (1, 1))
            tmp_draw = ImageDraw.Draw(tmp_img)
            while font_size > 10:
                bbox = tmp_draw.textbbox((0, 0), text, font=font)
                if bbox[2] - bbox[0] <= int(height * 0.75):
                    break
                font_size -= 1
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
                )
        except Exception:
            font = ImageFont.load_default()

        # Render text horizontally, then rotate
        tmp = Image.new('RGBA', (height, bar_width), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp)
        text_bbox = tmp_draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        tx = (height - text_w) // 2
        ty = (bar_width - text_h) // 2
        tmp_draw.text((tx, ty), text, font=font, fill=(150, 150, 150, 255))

        # Rotate 90° CCW so text reads bottom-to-top
        rotated = tmp.rotate(90, expand=True)

        # Paste onto the left bar area
        img.paste(rotated, (0, 0), rotated)

        return img

    def _render_unidentified(self, dimensions, settings, device_config, top_class, top_score):
        """Render when music is detected but Shazam can't identify it.
        If we have a last song, just re-render it (display stays the same).
        Otherwise show the default/idle image."""
        if self._last_song:
            logger.info("=== ShazamPi Plugin: Unidentified, keeping last song display ===")
            return self._render_song(self._last_song, dimensions, settings)

        logger.info("=== ShazamPi Plugin: Unidentified, no prior song ===")
        return self._render_idle(dimensions, settings, device_config)

    def _render_idle(self, dimensions, settings, device_config):
        width, height = dimensions
        weather = self._get_weather(settings, device_config)

        # Create black canvas
        canvas = Image.new('RGB', dimensions, (0, 0, 0))

        # Try to load weather icon centered on screen
        icon_img = None
        if weather and weather.get('icon_url'):
            try:
                icon_img = self.image_loader.from_url(
                    weather['icon_url'], (300, 300), timeout_ms=10000, fit_mode='fit'
                )
            except Exception as e:
                logger.debug(f"Failed to load weather icon: {e}")

        # Load fonts
        try:
            temp_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                max(40, int(height * 0.10))
            )
            desc_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                max(28, int(height * 0.06))
            )
        except Exception:
            temp_font = ImageFont.load_default()
            desc_font = temp_font

        draw = ImageDraw.Draw(canvas)
        padding = 10

        if weather:
            temp_text = weather['temperature']
            desc_text = weather['weather_sub_description']
        else:
            temp_text = "Listening..."
            desc_text = "No music detected"

        # Measure text
        temp_bbox = draw.textbbox((0, 0), temp_text, font=temp_font)
        temp_h = temp_bbox[3] - temp_bbox[1]
        temp_w = temp_bbox[2] - temp_bbox[0]

        desc_bbox = draw.textbbox((0, 0), desc_text, font=desc_font)
        desc_h = desc_bbox[3] - desc_bbox[1]
        desc_w = desc_bbox[2] - desc_bbox[0]

        # Calculate vertical layout: icon + temp + description, raised up
        icon_h = 300 if icon_img else 0
        gap_after_icon = 15
        gap_after_temp = 20
        total_h = icon_h + (gap_after_icon if icon_img else 0) + temp_h + gap_after_temp + desc_h
        start_y = (height - total_h) // 2 - int(height * 0.06)  # Shift up

        # Draw weather icon centered
        if icon_img:
            icon_x = (width - icon_img.size[0]) // 2
            canvas.paste(icon_img, (icon_x, start_y))
            start_y += icon_h + gap_after_icon

        # Draw temperature
        draw.text(
            ((width - temp_w) // 2, start_y),
            temp_text, font=temp_font, fill=(255, 255, 255)
        )
        start_y += temp_h + gap_after_temp

        # Draw description
        draw.text(
            ((width - desc_w) // 2, start_y),
            desc_text, font=desc_font, fill=(180, 180, 180)
        )

        # Note at bottom right
        try:
            small_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                max(12, int(height * 0.03))
            )
        except Exception:
            small_font = ImageFont.load_default()
        note = "No Music Playing or Song Not Found"
        note_bbox = draw.textbbox((0, 0), note, font=small_font)
        note_w = note_bbox[2] - note_bbox[0]
        note_h = note_bbox[3] - note_bbox[1]
        draw.text(
            (width - note_w - 10, height - note_h - 8),
            note, font=small_font, fill=(100, 100, 100)
        )

        logger.info("=== ShazamPi Plugin: Idle image generated ===")
        return canvas

    # ========== Weather ==========

    def _find_weather_settings(self, device_config):
        """Search loop config for a weather plugin instance and borrow its settings."""
        try:
            for loop in device_config.loop_manager.loops:
                for plugin_ref in loop.plugin_order:
                    if plugin_ref.plugin_id == "weather" and plugin_ref.plugin_settings:
                        ws = plugin_ref.plugin_settings
                        lat = ws.get("latitude", "")
                        lon = ws.get("longitude", "")
                        if lat and lon:
                            logger.info("Borrowing weather settings from Weather plugin")
                            return {
                                "geoCoordinates": f"{lat}, {lon}",
                                "units": ws.get("units", "imperial"),
                                "weatherProvider": ws.get("weatherProvider", "OpenWeatherMap"),
                            }
        except Exception as e:
            logger.debug(f"Could not read weather plugin settings: {e}")
        return None

    def _get_weather(self, settings, device_config):
        api_key = settings.get("weatherApiKey", "").strip()
        coords = settings.get("geoCoordinates", "").strip()

        # If no local weather config, try borrowing from weather plugin
        if not coords:
            borrowed = self._find_weather_settings(device_config)
            if borrowed:
                coords = borrowed["geoCoordinates"]
                if not api_key:
                    # Try loading API key from env (weather plugin stores it there)
                    api_key = device_config.load_env_key("OPEN_WEATHER_MAP_SECRET") or ""
                settings = {**settings, "units": borrowed.get("units", settings.get("units", "imperial"))}

        if not api_key or not coords:
            return self._last_weather

        # Use cache if fresh enough
        if (self._last_weather and self._last_weather_fetch and
                datetime.datetime.now() - self._last_weather_fetch <
                datetime.timedelta(minutes=WEATHER_CACHE_MINUTES)):
            return self._last_weather

        units = settings.get("units", "imperial")
        try:
            lat, lon = [x.strip() for x in coords.split(',')]
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&units={units}&appid={api_key}"
            )

            from utils.http_client import get_http_session
            session = get_http_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            temp_unit = {'metric': '\u00b0C', 'imperial': '\u00b0F'}.get(units, 'K')
            temperature = str(round(data['main']['temp'])) + temp_unit
            feels_like = str(round(data['main']['feels_like'])) + temp_unit
            condition = data['weather'][0]['description']

            icon_code = data['weather'][0].get('icon', '01d')
            icon_url = f"https://openweathermap.org/img/wn/{icon_code}@4x.png"

            self._last_weather = {
                'temperature': temperature,
                'weather_sub_description': f"Feels like {feels_like}. {condition}".title(),
                'icon_url': icon_url,
            }
            self._last_weather_fetch = datetime.datetime.now()
            return self._last_weather

        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return self._last_weather

    # ========== Title Overlay ==========

    def _add_title_overlay(self, image, title, subtitle=""):
        img = image.copy()
        draw = ImageDraw.Draw(img, 'RGBA')
        width, height = img.size

        # Font sizing
        try:
            title_font_size = max(16, int(height * 0.03))
            subtitle_font_size = max(14, int(height * 0.022))
            title_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_font_size
            )
            subtitle_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", subtitle_font_size
            )
        except Exception:
            title_font = ImageFont.load_default()
            subtitle_font = title_font
            logger.warning("Could not load custom font, using default")

        padding = max(10, int(height * 0.012))

        # Measure text
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_h = title_bbox[3] - title_bbox[1]
        title_w = title_bbox[2] - title_bbox[0]

        subtitle_h = 0
        subtitle_w = 0
        if subtitle:
            sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_h = sub_bbox[3] - sub_bbox[1]
            subtitle_w = sub_bbox[2] - sub_bbox[0]

        # Calculate overlay height
        total_text_h = title_h + (subtitle_h + padding // 2 if subtitle else 0)
        bar_top = height - total_text_h - padding * 2

        # Draw semi-transparent background bar
        draw.rectangle(
            [(0, bar_top), (width, height)],
            fill=(0, 0, 0, 180)
        )

        # Draw title (centered)
        title_x = (width - title_w) // 2
        title_y = bar_top + padding
        self._draw_outlined_text(draw, title_x, title_y, title, title_font)

        # Draw subtitle (centered, below title)
        if subtitle:
            sub_x = (width - subtitle_w) // 2
            sub_y = title_y + title_h + padding // 2
            self._draw_outlined_text(draw, sub_x, sub_y, subtitle, subtitle_font)

        return img

    def _draw_outlined_text(self, draw, x, y, text, font, outline=2):
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
