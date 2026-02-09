from plugins.base_plugin.base_plugin import BasePlugin
from openai import OpenAI
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)

# OpenAI models
OPENAI_TEXT_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5", "gpt-5-mini", "gpt-5-nano"]
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# Gemini models (use full model names for new API)
GEMINI_TEXT_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class AIText(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": False,
            "service": "OpenAI or Google Gemini",
            "expected_key": "OPEN_AI_SECRET or GOOGLE_GEMINI_SECRET"
        }
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        logger.info("=== AI Text Plugin: Starting text generation ===")

        provider = settings.get("provider", "openai")
        text_prompt = settings.get('textPrompt', '')

        # Use provided title, or auto-generate from prompt
        title = settings.get("title")
        if not title and text_prompt:
            # Create title from prompt (truncated)
            title = text_prompt.strip()
            if len(title) > 40:
                title = title[:37] + "..."

        if not text_prompt.strip():
            raise RuntimeError("Text Prompt is required.")

        logger.info(f"Provider: {provider}")
        logger.debug(f"Prompt: '{text_prompt}'")

        if provider == "gemini":
            prompt_response = self._generate_with_gemini(settings, device_config, text_prompt)
        else:
            prompt_response = self._generate_with_openai(settings, device_config, text_prompt)

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        # Convert literal \n to HTML line breaks
        formatted_response = prompt_response.replace('\\n', '<br>').replace('\n', '<br>')

        image_template_params = {
            "title": title,
            "content": formatted_response,
            "plugin_settings": settings
        }

        image = self.render_image(dimensions, "ai_text.html", "ai_text.css", image_template_params)

        logger.info("=== AI Text Plugin: Text generation complete ===")
        return image

    def _generate_with_openai(self, settings, device_config, text_prompt):
        """Generate text using OpenAI."""
        api_key = device_config.load_env_key("OPEN_AI_SECRET")
        if not api_key:
            raise RuntimeError("OpenAI API Key not configured. Add OPEN_AI_SECRET in Settings > API Keys.")

        # Sanitize API key
        api_key = api_key.encode('ascii', errors='ignore').decode('ascii').strip()

        text_model = settings.get('textModel', DEFAULT_OPENAI_MODEL)
        if text_model not in OPENAI_TEXT_MODELS:
            logger.warning(f"Unknown OpenAI model: {text_model}, using anyway")

        logger.info(f"OpenAI Settings: model={text_model}")

        try:
            ai_client = OpenAI(api_key=api_key)
            return self._fetch_openai_text(ai_client, text_model, text_prompt)
        except Exception as e:
            logger.error(f"Failed to make OpenAI request: {str(e)}")
            raise RuntimeError("OpenAI request failure, please check logs.")

    def _generate_with_gemini(self, settings, device_config, text_prompt):
        """Generate text using Google Gemini."""
        api_key = device_config.load_env_key("GOOGLE_GEMINI_SECRET")
        if not api_key:
            raise RuntimeError("Google Gemini API Key not configured. Add GOOGLE_GEMINI_SECRET in Settings > API Keys.")

        # Sanitize API key
        api_key = api_key.encode('ascii', errors='ignore').decode('ascii').strip()

        text_model = settings.get('geminiTextModel', DEFAULT_GEMINI_MODEL)

        logger.info(f"Gemini Settings: model={text_model}")

        try:
            from google import genai

            client = genai.Client(api_key=api_key)

            # Add randomness to prevent cached/repeated responses
            random_seed = random.randint(1, 1000000)

            # Check if prompt is asking for a joke - use special handling
            prompt_lower = text_prompt.lower()
            is_joke_request = any(word in prompt_lower for word in ["joke", "funny", "humor", "laugh", "pun"])

            if is_joke_request:
                # Random variety injectors for joke prompts
                styles = ["witty", "clever", "silly", "dry", "absurd", "punny", "observational", "surreal", "dark", "wholesome"]
                topics = ["technology", "food", "animals", "work", "relationships", "science", "history", "sports", "music", "travel"]
                random_style = random.choice(styles)
                random_topic = random.choice(topics)

                system_prompt = (
                    f"You are a {random_style} comedian who never repeats jokes. "
                    "Keep responses under 70 words. Be creative and original. "
                    "Respond directly without introductions or explanations."
                )

                # For generic joke requests, inject variety
                if len(text_prompt.split()) < 6:
                    enhanced_prompt = f"{text_prompt} (make it {random_style}, maybe about {random_topic})"
                else:
                    enhanced_prompt = text_prompt
            else:
                # General-purpose text generation
                system_prompt = (
                    "You are a helpful and creative text generation assistant. "
                    "Keep responses under 70 words. Be concise and relevant. "
                    "Respond directly without introductions or explanations."
                )
                enhanced_prompt = text_prompt

            full_prompt = f"{system_prompt}\n\nUser request: {enhanced_prompt}"
            response = client.models.generate_content(
                model=text_model,
                contents=full_prompt,
                config={
                    "temperature": 2.0,
                    "seed": random_seed
                }
            )
            result = response.text.strip()

            logger.info(f"Generated text response: {result[:100]}...")
            return result

        except ImportError:
            logger.error("google-genai package not installed")
            raise RuntimeError("Google Gemini SDK not installed. Run: pip install google-genai")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to make Gemini request: {error_msg}")

            # Provide user-friendly error messages
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                raise RuntimeError("Gemini rate limit reached. Please wait a minute and try again, or try a different model.")
            elif "API_KEY" in error_msg.upper() or "401" in error_msg:
                raise RuntimeError("Gemini API key is invalid. Please check your GOOGLE_GEMINI_SECRET in Settings > API Keys.")
            elif "404" in error_msg:
                raise RuntimeError("Gemini model not found. Please select a different model.")
            else:
                raise RuntimeError(f"Gemini error: {error_msg[:100]}")

    def _fetch_openai_text(self, ai_client, model, text_prompt):
        """Fetch text response from OpenAI."""
        logger.info(f"Getting text response from OpenAI, model: {model}")

        system_content = (
            "You are a highly intelligent text generation assistant. Generate concise, "
            "relevant, and accurate responses tailored to the user's input. The response "
            "should be 70 words or less."
            "IMPORTANT: Do not rephrase, reword, or provide an introduction. Respond directly "
            "to the request without adding explanations or extra context "
            "IMPORTANT: If the response naturally requires a newline for formatting, provide "
            "the '\n' newline character explicitly for every new line. For regular sentences "
            "or paragraphs do not provide the new line character."
            f"For context, today is {datetime.today().strftime('%Y-%m-%d')}"
        )

        response = ai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": text_prompt}
            ],
            temperature=1
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"Generated text response: {result[:100]}...")
        return result
