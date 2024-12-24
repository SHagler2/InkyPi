import logging
import os
from utils.app_utils import resolve_path
from pathlib import Path

logger = logging.getLogger(__name__)

PLUGIN_DIR = "plugins"

class BasePlugin:
    """Base class for all plugins."""
    def __init__(self, config, **dependencies):
        self.config = config

    def generate_image(self, settings, device_config):
        raise NotImplementedError("generate_image must be implemented by subclasses")
    
    def generate_settings_template(self):
        template_params = {"settings_template": "base_plugin/settings.html"}

        settings_template = os.path.join(self.config.get("id"), "settings.html")
        settings_path = Path(resolve_path(PLUGIN_DIR)) / settings_template
        if settings_path.is_file():
            template_params["settings_template"] = settings_template
        return template_params