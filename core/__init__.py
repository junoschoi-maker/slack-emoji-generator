# Slack Emoji Generator - Core Module
from .face_detector import detect_and_crop_face, get_face_landmarks
from .background_remover import remove_background, remove_background_from_bytes
from .gif_generator import create_animated_gif, optimize_gif_size, save_gif
from .template_engine import TemplateEngine, Template
from .emoji_set import (
    get_all_emoji_configs,
    get_emoji_by_category,
    get_emoji_by_id,
    generate_template_assets,
    generate_all_template_assets,
)

__all__ = [
    "detect_and_crop_face",
    "get_face_landmarks",
    "remove_background",
    "remove_background_from_bytes",
    "create_animated_gif",
    "optimize_gif_size",
    "save_gif",
    "TemplateEngine",
    "Template",
    "get_all_emoji_configs",
    "get_emoji_by_category",
    "get_emoji_by_id",
    "generate_template_assets",
    "generate_all_template_assets",
]
