"""
core/emoji_set.py
25개 이모티콘 템플릿의 config 정의 및 Pillow 기반 에셋 생성기.
실제 이모지 PNG 에셋(assets/emoji/)을 우선 사용하며,
에셋이 없으면 순수 Pillow 코드로 폴백한다.
"""
from __future__ import annotations

import math
import os
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

CANVAS = 128  # px

# ---------------------------------------------------------------------------
# 템플릿 config 정의
# ---------------------------------------------------------------------------

_CONFIGS: list[dict] = [
    # ================================================================
    # Emotions
    # ================================================================
    {
        "id": "happy",
        "name": "기쁨",
        "category": "emotions",
        "frames": 4,
        "duration_ms": 120,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 8, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 8, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFF9900", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "sad",
        "name": "슬픔",
        "category": "emotions",
        "frames": 4,
        "duration_ms": 160,
        "animation_type": "shake",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": -5, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 5, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": -5, "opacity": 255},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 5, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#4488FF00", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "angry",
        "name": "화남",
        "category": "emotions",
        "frames": 4,
        "duration_ms": 80,
        "animation_type": "vibrate",
        "face_placements": [
            {"frame": 1, "x": 12, "y": 12, "w": 100, "h": 100, "rotation": -2, "opacity": 255},
            {"frame": 2, "x": 18, "y": 10, "w": 100, "h": 100, "rotation": 2, "opacity": 255},
            {"frame": 3, "x": 10, "y": 14, "w": 100, "h": 100, "rotation": -3, "opacity": 255},
            {"frame": 4, "x": 20, "y": 10, "w": 100, "h": 100, "rotation": 3, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FF440000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "surprised",
        "name": "놀람",
        "category": "emotions",
        "frames": 3,
        "duration_ms": 140,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 4, "y": 4, "w": 120, "h": 120, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFF0000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "love",
        "name": "사랑",
        "category": "emotions",
        "frames": 4,
        "duration_ms": 150,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 9, "y": 9, "w": 110, "h": 110, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 9, "y": 9, "w": 110, "h": 110, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FF44AA00", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "laugh",
        "name": "웃음",
        "category": "emotions",
        "frames": 4,
        "duration_ms": 130,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 10, "y": 8, "w": 108, "h": 108, "rotation": -3, "opacity": 255},
            {"frame": 3, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 18, "y": 8, "w": 108, "h": 108, "rotation": 3, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFDD0000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    # ================================================================
    # Work
    # ================================================================
    {
        "id": "goHome",
        "name": "퇴근",
        "category": "work",
        "frames": 4,
        "duration_ms": 120,
        "animation_type": "shake",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 34, "y": 14, "w": 100, "h": 100, "rotation": 5, "opacity": 255},
            {"frame": 3, "x": 58, "y": 14, "w": 100, "h": 100, "rotation": 10, "opacity": 180},
            {"frame": 4, "x": 84, "y": 14, "w": 100, "h": 100, "rotation": 15, "opacity": 60},
        ],
        "layers": [
            {"type": "background", "color": "#00CC4400", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "overtime",
        "name": "야근",
        "category": "work",
        "frames": 3,
        "duration_ms": 300,
        "animation_type": "vibrate",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 15, "y": 16, "w": 100, "h": 100, "rotation": 2, "opacity": 230},
            {"frame": 3, "x": 13, "y": 14, "w": 100, "h": 100, "rotation": -1, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#111133FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "meeting",
        "name": "회의중",
        "category": "work",
        "frames": 3,
        "duration_ms": 400,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 18, "w": 100, "h": 100, "rotation": 6, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFFFFFF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "deploy",
        "name": "배포",
        "category": "work",
        "frames": 4,
        "duration_ms": 120,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 40, "w": 96, "h": 96, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 26, "w": 96, "h": 96, "rotation": -5, "opacity": 255},
            {"frame": 3, "x": 14, "y": 10, "w": 96, "h": 96, "rotation": -10, "opacity": 220},
            {"frame": 4, "x": 14, "y": -8, "w": 96, "h": 96, "rotation": -15, "opacity": 150},
        ],
        "layers": [
            {"type": "background", "color": "#002244FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "bug",
        "name": "버그",
        "category": "work",
        "frames": 3,
        "duration_ms": 200,
        "animation_type": "vibrate",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 80},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FF000000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "lgtm",
        "name": "LGTM",
        "category": "work",
        "frames": 3,
        "duration_ms": 150,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 9, "y": 9, "w": 110, "h": 110, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#00AA4400", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "coffee",
        "name": "커피타임",
        "category": "work",
        "frames": 3,
        "duration_ms": 200,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 4, "y": 8, "w": 80, "h": 80, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 4, "y": 4, "w": 80, "h": 80, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 4, "y": 8, "w": 80, "h": 80, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#F5DEB3FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    # ================================================================
    # Funny
    # ================================================================
    {
        "id": "fire",
        "name": "불타는눈",
        "category": "funny",
        "frames": 4,
        "duration_ms": 100,
        "animation_type": "vibrate",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#000000FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "party",
        "name": "파티",
        "category": "funny",
        "frames": 4,
        "duration_ms": 120,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 18, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 10, "w": 100, "h": 100, "rotation": -4, "opacity": 255},
            {"frame": 3, "x": 14, "y": 18, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 10, "w": 100, "h": 100, "rotation": 4, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFF0000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "spin",
        "name": "스핀",
        "category": "funny",
        "frames": 8,
        "duration_ms": 80,
        "animation_type": "spin",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 45, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 90, "opacity": 255},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 135, "opacity": 255},
            {"frame": 5, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 180, "opacity": 255},
            {"frame": 6, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 225, "opacity": 255},
            {"frame": 7, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 270, "opacity": 255},
            {"frame": 8, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 315, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFFFF00", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "rainbow",
        "name": "무지개",
        "category": "funny",
        "frames": 6,
        "duration_ms": 120,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 5, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 6, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFFFF00", "z_order": 0},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 1},
            {"type": "face", "z_order": 2},
        ],
    },
    {
        "id": "thug",
        "name": "선글라스",
        "category": "funny",
        "frames": 4,
        "duration_ms": 150,
        "animation_type": "fade_in",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#000000FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "cockroach",
        "name": "바퀴벌레",
        "category": "funny",
        "frames": 4,
        "duration_ms": 130,
        "animation_type": "shake",
        "face_placements": [
            {"frame": 1, "x": 20, "y": 6, "w": 88, "h": 88, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 24, "y": 8, "w": 88, "h": 88, "rotation": 5, "opacity": 255},
            {"frame": 3, "x": 20, "y": 6, "w": 88, "h": 88, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 16, "y": 8, "w": 88, "h": 88, "rotation": -5, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFFFFF00", "z_order": 0},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 1},
            {"type": "face", "z_order": 2},
        ],
    },
    {
        "id": "rip",
        "name": "RIP",
        "category": "funny",
        "frames": 4,
        "duration_ms": 200,
        "animation_type": "fade_out",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 180},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 100},
            {"frame": 4, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 30},
        ],
        "layers": [
            {"type": "background", "color": "#333333FF", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    # ================================================================
    # Reaction
    # ================================================================
    {
        "id": "ok",
        "name": "OK",
        "category": "reaction",
        "frames": 3,
        "duration_ms": 150,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 8, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 16, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#00BB5500", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "no",
        "name": "NO",
        "category": "reaction",
        "frames": 4,
        "duration_ms": 100,
        "animation_type": "shake",
        "face_placements": [
            {"frame": 1, "x": 6, "y": 14, "w": 100, "h": 100, "rotation": -6, "opacity": 255},
            {"frame": 2, "x": 22, "y": 14, "w": 100, "h": 100, "rotation": 6, "opacity": 255},
            {"frame": 3, "x": 6, "y": 14, "w": 100, "h": 100, "rotation": -6, "opacity": 255},
            {"frame": 4, "x": 22, "y": 14, "w": 100, "h": 100, "rotation": 6, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FF330000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "question",
        "name": "물음표",
        "category": "reaction",
        "frames": 3,
        "duration_ms": 200,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFAA0000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "exclaim",
        "name": "느낌표",
        "category": "reaction",
        "frames": 3,
        "duration_ms": 150,
        "animation_type": "pulse",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 9, "y": 9, "w": 110, "h": 110, "rotation": 0, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FF660000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
    {
        "id": "clap",
        "name": "박수",
        "category": "reaction",
        "frames": 4,
        "duration_ms": 120,
        "animation_type": "bounce",
        "face_placements": [
            {"frame": 1, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 2, "x": 14, "y": 8, "w": 100, "h": 100, "rotation": -2, "opacity": 255},
            {"frame": 3, "x": 14, "y": 14, "w": 100, "h": 100, "rotation": 0, "opacity": 255},
            {"frame": 4, "x": 14, "y": 8, "w": 100, "h": 100, "rotation": 2, "opacity": 255},
        ],
        "layers": [
            {"type": "background", "color": "#FFDD0000", "z_order": 0},
            {"type": "face", "z_order": 1},
            {"type": "overlay", "file": "overlay_{frame}.png", "z_order": 2},
        ],
    },
]

# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def get_all_emoji_configs() -> list[dict]:
    """25개 이모티콘 템플릿 config 리스트를 반환한다."""
    return list(_CONFIGS)


def get_emoji_by_category(category: str) -> list[dict]:
    """카테고리로 필터링된 템플릿 config 리스트를 반환한다."""
    return [c for c in _CONFIGS if c["category"] == category]


def get_emoji_by_id(emoji_id: str) -> dict:
    """ID로 단일 템플릿 config를 반환한다. 없으면 KeyError."""
    for c in _CONFIGS:
        if c["id"] == emoji_id:
            return c
    raise KeyError(f"이모티콘 ID를 찾을 수 없습니다: {emoji_id!r}")


# ---------------------------------------------------------------------------
# 에셋 생성기 (Pillow 기반)
# ---------------------------------------------------------------------------

def generate_template_assets(emoji_id: str, output_dir: str) -> None:
    """
    지정된 이모티콘의 템플릿 에셋(overlay 프레임 이미지 + config.json)을
    output_dir에 생성한다.

    Parameters
    ----------
    emoji_id:
        생성할 이모티콘 ID (예: "happy").
    output_dir:
        에셋을 저장할 디렉토리 경로. 없으면 자동 생성.
    """
    import json as _json

    cfg = get_emoji_by_id(emoji_id)
    os.makedirs(output_dir, exist_ok=True)

    # config.json 저장
    config_path = os.path.join(output_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)

    # overlay 이미지 생성
    _GENERATORS: dict[str, callable] = {
        # emotions
        "happy": _gen_happy,
        "sad": _gen_sad,
        "angry": _gen_angry,
        "surprised": _gen_surprised,
        "love": _gen_love,
        "laugh": _gen_laugh,
        # work
        "goHome": _gen_go_home,
        "overtime": _gen_overtime,
        "meeting": _gen_meeting,
        "deploy": _gen_deploy,
        "bug": _gen_bug,
        "lgtm": _gen_lgtm,
        "coffee": _gen_coffee,
        # funny
        "fire": _gen_fire,
        "party": _gen_party,
        "spin": _gen_spin,
        "rainbow": _gen_rainbow,
        "thug": _gen_thug,
        "cockroach": _gen_cockroach,
        "rip": _gen_rip,
        # reaction
        "ok": _gen_ok,
        "no": _gen_no,
        "question": _gen_question,
        "exclaim": _gen_exclaim,
        "clap": _gen_clap,
    }

    generator = _GENERATORS.get(emoji_id)
    if generator is None:
        raise ValueError(f"에셋 생성기가 없습니다: {emoji_id!r}")

    frames_count = cfg["frames"]
    overlays: list[Image.Image] = generator(frames_count)

    for i, overlay in enumerate(overlays):
        frame_no = i + 1
        out_path = os.path.join(output_dir, f"overlay_{frame_no}.png")
        overlay.save(out_path, format="PNG")


def generate_all_template_assets(templates_base_dir: str) -> None:
    """
    모든 25개 이모티콘 에셋을 templates_base_dir/{category}/{id}/ 구조로 생성한다.
    """
    for cfg in _CONFIGS:
        out_dir = os.path.join(templates_base_dir, cfg["category"], cfg["id"])
        generate_template_assets(cfg["id"], out_dir)


# ---------------------------------------------------------------------------
# 에셋 로딩 헬퍼
# ---------------------------------------------------------------------------

def _load_asset(name: str, size: int) -> Optional[Image.Image]:
    """
    assets/emoji/{name}.png 를 로드해 size x size 로 리사이즈한다.
    파일이 없으면 None 을 반환한다.
    """
    asset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "emoji")
    path = os.path.join(asset_dir, f"{name}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _place_asset(canvas: Image.Image, asset: Image.Image, x: int, y: int) -> None:
    """canvas 위의 (x, y) 좌표에 asset 을 RGBA 합성으로 붙여 넣는다."""
    canvas.paste(asset, (x, y), asset)


def _load_asset_scaled(name: str, base_size: int, scale: float) -> Optional[Image.Image]:
    """에셋을 base_size * scale 크기로 로드한다."""
    actual_size = max(1, int(base_size * scale))
    return _load_asset(name, actual_size)


# ---------------------------------------------------------------------------
# 내부 헬퍼 (코드 드로우)
# ---------------------------------------------------------------------------

def _blank(alpha: int = 0) -> Image.Image:
    """투명 128x128 캔버스를 반환한다."""
    return Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, alpha))


def _draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int,
                color: tuple) -> None:
    """간단한 하트 도형을 그린다."""
    half = size // 2
    draw.ellipse([cx - half, cy - half, cx, cy + half // 2], fill=color)
    draw.ellipse([cx, cy - half, cx + half, cy + half // 2], fill=color)
    draw.polygon([
        (cx - half, cy),
        (cx + half, cy),
        (cx, cy + size),
    ], fill=color)


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
               color: tuple) -> None:
    """5각 별을 그린다."""
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        radius = r if i % 2 == 0 else r // 2
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=color)


def _draw_flame(draw: ImageDraw.ImageDraw, cx: int, base_y: int, w: int,
                h: int, color: tuple, flicker: int = 0) -> None:
    """불꽃 형태 다각형을 그린다."""
    hw = w // 2
    tip_x = cx + flicker
    draw.polygon([
        (cx - hw, base_y),
        (cx + hw, base_y),
        (cx + hw // 2, base_y - h // 2),
        (tip_x, base_y - h),
        (cx - hw // 2, base_y - h // 2),
    ], fill=color)


# ---------------------------------------------------------------------------
# 이모티콘별 오버레이 생성기 (에셋 우선, 폴백 포함)
# ---------------------------------------------------------------------------

# ---- Emotions ----

def _gen_happy(n: int) -> list[Image.Image]:
    """
    기쁨: sparkles.png 를 4 코너에 토글 배치.
    에셋 없으면 코드 드로우 별로 폴백.
    """
    # 코너 위치 (x, y) — 각 스파클 20x20
    corner_positions = [(100, 6), (6, 10), (102, 46), (4, 50)]
    frames = []
    for i in range(n):
        img = _blank()
        for j, (sx, sy) in enumerate(corner_positions):
            if (i + j) % 2 == 0:  # 프레임마다 토글
                sparkle = _load_asset("sparkles", 20)
                if sparkle:
                    _place_asset(img, sparkle, sx, sy)
                else:
                    # 폴백: 코드 드로우 별
                    d = ImageDraw.Draw(img)
                    _draw_star(d, sx + 10, sy + 10, 8, (255, 220, 0, 230))
        frames.append(img)
    return frames


def _gen_sad(n: int) -> list[Image.Image]:
    """
    슬픔: droplet.png 두 방울, 프레임마다 Y 하강.
    에셋 없으면 코드 드로우 폴백.
    """
    # 눈물 X 위치 (좌안, 우안)
    drop_xs = [40, 74]
    frames = []
    for i in range(n):
        img = _blank()
        base_y = 78 + i * 8
        for dx in drop_xs:
            drop = _load_asset("droplet", 12)
            if drop:
                _place_asset(img, drop, dx, base_y)
            else:
                d = ImageDraw.Draw(img)
                d.ellipse([dx, base_y, dx + 10, base_y + 14], fill=(100, 160, 255, 200))
        frames.append(img)
    return frames


def _gen_angry(n: int) -> list[Image.Image]:
    """
    화남: anger.png 상단 우측, 스케일 지터.
    에셋 없으면 코드 드로우 혈관 폴백.
    """
    base_sizes = [28, 32, 30, 28]
    jitter_xy = [(0, 0), (2, -2), (-2, 1), (1, 2)]
    frames = []
    for i in range(n):
        img = _blank()
        sz = base_sizes[i % len(base_sizes)]
        jx, jy = jitter_xy[i % len(jitter_xy)]
        anger = _load_asset("anger", sz)
        if anger:
            _place_asset(img, anger, 94 + jx, 6 + jy)
        else:
            # 폴백: 혈관 심볼
            d = ImageDraw.Draw(img)
            col = (255, 50, 0, 230)
            d.line([(100, 8), (108, 30)], fill=col, width=3)
            d.line([(110, 8), (102, 30)], fill=col, width=3)
            d.line([(96, 15), (114, 15)], fill=col, width=2)
            d.line([(97, 23), (115, 23)], fill=col, width=2)
        frames.append(img)
    return frames


def _gen_surprised(n: int) -> list[Image.Image]:
    """
    놀람: collision.png (선택적 악센트) + 코드 드로우 방사형 선.
    """
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        if i == 1:  # 놀라는 순간
            cx, cy = 64, 64
            # 방사형 선 (코드 드로우 유지)
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                x1 = cx + 55 * math.cos(rad)
                y1 = cy + 55 * math.sin(rad)
                x2 = cx + 70 * math.cos(rad)
                y2 = cy + 70 * math.sin(rad)
                d.line([(x1, y1), (x2, y2)], fill=(255, 220, 0, 220), width=3)
            # collision.png 선택적 악센트 (상단 우측)
            collision = _load_asset("collision", 24)
            if collision:
                _place_asset(img, collision, 96, 4)
        frames.append(img)
    return frames


def _gen_love(n: int) -> list[Image.Image]:
    """
    사랑: red_heart.png 3개, 다른 크기(10~16px), 떠오르며 펄스.
    에셋 없으면 코드 드로우 하트 폴백.
    """
    # (x, y, size, y_float_offsets)
    heart_specs = [
        (8,  56, 10, [0, -3, -6, -8]),
        (106, 44, 14, [0, -4, -7, -10]),
        (50,  96, 16, [0, -2, -5, -7]),
    ]
    frames = []
    for i in range(n):
        img = _blank()
        for hx, hy, base_sz, floats in heart_specs:
            # 펄스: 짝수 프레임 약간 크게
            pulse = 1.15 if i % 2 == 1 else 1.0
            sz = max(1, int(base_sz * pulse))
            y_off = floats[i % len(floats)]
            heart = _load_asset("red_heart", sz)
            if heart:
                _place_asset(img, heart, hx, hy + y_off)
            else:
                d = ImageDraw.Draw(img)
                _draw_heart(d, hx + sz // 2, hy + y_off + sz // 2, sz,
                            (255, 80, 130, 220))
        frames.append(img)
    return frames


def _gen_laugh(n: int) -> list[Image.Image]:
    """
    웃음: droplet.png 작게(8px) 눈 바깥 코너, 바운스.
    에셋 없으면 코드 드로우 눈물 폴백.
    """
    # (x, y) — 좌안 바깥, 우안 바깥
    eye_outer = [(36, 72), (82, 72)]
    bounce_y = [0, -4, 0, -4]
    frames = []
    for i in range(n):
        img = _blank()
        by = bounce_y[i % len(bounce_y)]
        for ex, ey in eye_outer:
            drop = _load_asset("droplet", 8)
            if drop:
                _place_asset(img, drop, ex, ey + by)
            else:
                d = ImageDraw.Draw(img)
                d.ellipse([ex, ey + by, ex + 8, ey + by + 12],
                          fill=(100, 200, 255, 200))
        frames.append(img)
    return frames


# ---- Work ----

def _gen_go_home(n: int) -> list[Image.Image]:
    """
    퇴근: door.png(32px 우측) + dash.png(24px 좌측, 커지는 효과).
    에셋 없으면 코드 드로우 폴백.
    """
    door_x_positions = [90, 96, 104, 115]
    dash_sizes = [16, 20, 24, 28]
    frames = []
    for i in range(n):
        img = _blank()
        dx = door_x_positions[i % len(door_x_positions)]
        # 속도선 (dash 에셋 또는 코드 드로우)
        dash_sz = dash_sizes[i % len(dash_sizes)]
        dash = _load_asset("dash", dash_sz)
        if dash:
            _place_asset(img, dash, 4, 50)
        else:
            d = ImageDraw.Draw(img)
            for k in range(3):
                line_y = 50 + k * 12
                d.line([(4, line_y), (dx - 10, line_y)],
                       fill=(255, 200, 0, max(0, 180 - i * 40)), width=2)
        # 문 (door 에셋 또는 코드 드로우)
        door = _load_asset("door", 32)
        if door:
            _place_asset(img, door, dx - 16, 48)
        else:
            d = ImageDraw.Draw(img)
            d.rectangle([dx, 20, dx + 20, 108], outline=(150, 100, 50, 200), width=2)
            d.ellipse([dx + 14, 60, dx + 18, 66], fill=(180, 140, 60, 220))
        frames.append(img)
    return frames


def _gen_overtime(n: int) -> list[Image.Image]:
    """
    야근: moon.png(24px 상단우측) + zzz.png(20px 떠오름) + star.png(12px).
    에셋 없으면 코드 드로우 폴백.
    """
    zzz_y_positions = [30, 22, 14]
    frames = []
    for i in range(n):
        img = _blank()
        # 달
        moon = _load_asset("moon", 24)
        if moon:
            _place_asset(img, moon, 88, 4)
        else:
            d = ImageDraw.Draw(img)
            d.ellipse([88, 4, 112, 28], fill=(255, 230, 100, 200))
            d.ellipse([94, 4, 118, 28], fill=(20, 20, 50, 255))
        # 별
        star = _load_asset("star", 12)
        if star:
            _place_asset(img, star, 72, 4)
        else:
            d = ImageDraw.Draw(img)
            _draw_star(d, 78, 10, 5, (255, 255, 180, 180))
        # ZZZ — 떠오르며 페이드
        zzz_y = zzz_y_positions[i % len(zzz_y_positions)]
        alpha = max(0, 200 - i * 30)
        zzz = _load_asset("zzz", 20)
        if zzz and alpha > 0:
            # alpha 조절
            r, g, b, a = zzz.split()
            a = a.point(lambda x: int(x * alpha / 255))
            zzz = Image.merge("RGBA", (r, g, b, a))
            _place_asset(img, zzz, 96, zzz_y)
        else:
            d = ImageDraw.Draw(img)
            for zi in range(3):
                za = max(0, alpha - zi * 40)
                if za > 0:
                    d.text((100 - zi * 4, zzz_y - zi * 12), "z",
                           fill=(180, 180, 255, za))
        frames.append(img)
    return frames


def _gen_meeting(n: int) -> list[Image.Image]:
    """
    회의중: speech.png(28px 상단우측) + zzz.png(18px 나타나는 효과).
    에셋 없으면 코드 드로우 폴백.
    """
    frames = []
    for i in range(n):
        img = _blank()
        # 말풍선
        speech = _load_asset("speech", 28)
        if speech:
            _place_asset(img, speech, 94, 4)
        # ZZZ — 프레임마다 나타남
        zzz_alpha = [0, 120, 200][i % 3]
        zzz_y = 8 - i * 4
        zzz = _load_asset("zzz", 18)
        if zzz and zzz_alpha > 0:
            r, g, b, a = zzz.split()
            a = a.point(lambda x: int(x * zzz_alpha / 255))
            zzz = Image.merge("RGBA", (r, g, b, a))
            _place_asset(img, zzz, 86, zzz_y)
        else:
            d = ImageDraw.Draw(img)
            for zi in range(3):
                alpha = max(0, zzz_alpha - zi * 30)
                if alpha > 0:
                    d.text((90 + zi * 8, zzz_y + zi * (-6)),
                           "Z", fill=(150, 150, 200, alpha))
        frames.append(img)
    return frames


def _gen_deploy(n: int) -> list[Image.Image]:
    """
    배포: rocket.png(36px 위로 이동) + fire.png(20px 로켓 아래).
    에셋 없으면 코드 드로우 폴백.
    """
    rocket_y_positions = [88, 66, 44, 14]
    frames = []
    for i in range(n):
        img = _blank()
        ry = rocket_y_positions[i % len(rocket_y_positions)]
        rx = 46  # 로켓 x (중앙 기준)
        rocket = _load_asset("rocket", 36)
        if rocket:
            _place_asset(img, rocket, rx, ry)
        else:
            d = ImageDraw.Draw(img)
            d.polygon([(rx + 18, ry), (rx + 10, ry + 36), (rx + 26, ry + 36)],
                      fill=(220, 220, 240, 230))
        # 불꽃
        fire_y = ry + 32
        fire = _load_asset("fire", 20)
        if fire and fire_y < CANVAS:
            _place_asset(img, fire, rx + 8, fire_y)
        else:
            d = ImageDraw.Draw(img)
            _draw_flame(d, rx + 18, fire_y + 10, 16, 20, (255, 140, 0, 220),
                        flicker=i * 2 - 3)
        frames.append(img)
    return frames


def _gen_bug(n: int) -> list[Image.Image]:
    """
    버그: bug_insect.png(24px 하단좌측) + warning.png(20px 상단우측) + 코드 드로우 빨간 테두리.
    에셋 없으면 코드 드로우 폴백.
    """
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        if i % 2 == 0:
            # 빨간 경고 테두리 (코드 드로우 유지)
            for w in range(3):
                d.rectangle([w, w, CANVAS - w, CANVAS - w],
                             outline=(255, 0, 0, 200 - w * 40), width=1)
            # 벌레
            bug = _load_asset("bug_insect", 24)
            if bug:
                _place_asset(img, bug, 6, 96)
            else:
                d.line([(8, 100), (30, 120)], fill=(255, 50, 50, 220), width=4)
                d.line([(30, 100), (8, 120)], fill=(255, 50, 50, 220), width=4)
            # 경고
            warning = _load_asset("warning", 20)
            if warning:
                _place_asset(img, warning, 100, 6)
        frames.append(img)
    return frames


def _gen_lgtm(n: int) -> list[Image.Image]:
    """
    LGTM: check.png(28px 하단좌측) + sparkles.png(16px 흩어짐).
    에셋 없으면 코드 드로우 폴백.
    """
    sparkle_positions = [(68, 10), (102, 26), (88, 6)]
    frames = []
    for i in range(n):
        img = _blank()
        # 체크마크
        check = _load_asset("check", 28)
        if check:
            _place_asset(img, check, 6, 88)
        else:
            d = ImageDraw.Draw(img)
            alpha = 255 if i % 2 == 0 else 150
            d.line([(10, 95), (25, 115)], fill=(50, 200, 50, alpha), width=5)
            d.line([(25, 115), (55, 75)], fill=(50, 200, 50, alpha), width=5)
        # 스파클
        if i == 1:
            for sx, sy in sparkle_positions:
                sparkle = _load_asset("sparkles", 16)
                if sparkle:
                    _place_asset(img, sparkle, sx, sy)
                else:
                    d = ImageDraw.Draw(img)
                    _draw_star(d, sx + 8, sy + 8, 7, (255, 220, 0, 220))
        frames.append(img)
    return frames


def _gen_coffee(n: int) -> list[Image.Image]:
    """
    커피: coffee_cup.png(48px 우측) + 코드 드로우 김 선.
    에셋 없으면 코드 드로우 잔 + 김 폴백.
    """
    steam_offsets = [(0, 0), (2, -3), (0, 0)]
    frames = []
    for i in range(n):
        img = _blank()
        ox, oy = steam_offsets[i % len(steam_offsets)]
        cup = _load_asset("coffee_cup", 48)
        if cup:
            _place_asset(img, cup, 74, 68)
        else:
            d = ImageDraw.Draw(img)
            d.rectangle([68, 72, 116, 110], fill=(100, 60, 20, 220))
            d.rectangle([70, 74, 114, 108], fill=(60, 30, 10, 200))
            d.arc([110, 82, 126, 102], 270, 90, fill=(100, 60, 20, 220), width=4)
            d.rectangle([71, 90, 113, 107], fill=(40, 20, 5, 240))
        # 김 (코드 드로우 유지 — 에셋보다 자연스러움)
        d = ImageDraw.Draw(img)
        steam_y = 60 + oy
        for sx in [80, 90, 100]:
            d.arc([sx + ox - 4, steam_y - 8, sx + ox + 4, steam_y + 8],
                  200, 340, fill=(220, 220, 220, 150), width=2)
        frames.append(img)
    return frames


# ---- Funny ----

def _gen_fire(n: int) -> list[Image.Image]:
    """
    불타는 눈: fire.png(22px) 를 양쪽 눈 위치에, 얼굴 위(ON TOP of face).
    에셋 없으면 코드 드로우 불꽃 폴백.
    face_placements 기준: 얼굴 x=32, y=24, w=64, h=64.
    눈 위치 대략: 좌(48,48), 우(90,48) → 오버레이 좌표계로.
    """
    # 128x128 오버레이 상의 눈 위치 (얼굴 중심 기준)
    eye_positions = [(30, 46), (72, 46)]
    flickers = [(-2, 2, -3, 1), (1, -2, 2, -1)]
    frames = []
    for i in range(n):
        img = _blank()
        for j, (ex, ey) in enumerate(eye_positions):
            fk = flickers[j][i % len(flickers[j])]
            fire = _load_asset("fire", 22)
            if fire:
                _place_asset(img, fire, ex + fk, ey - 10)
            else:
                d = ImageDraw.Draw(img)
                _draw_flame(d, ex + 8, ey + 20, 18, 24, (255, 100, 0, 220), fk)
                _draw_flame(d, ex + 8, ey + 18, 12, 16, (255, 200, 0, 200), fk // 2)
        frames.append(img)
    return frames


def _gen_party(n: int) -> list[Image.Image]:
    """
    파티: party_popper.png(32px 상단좌측) + confetti.png(24px 상단우측)
          + 코드 드로우 컨페티 점.
    에셋 없으면 코드 드로우 폴백.
    """
    rng = random.Random(42)
    confetti_data = []
    for _ in range(20):
        confetti_data.append({
            "x": rng.randint(0, CANVAS),
            "y": rng.randint(0, CANVAS // 2),
            "color": (rng.randint(100, 255), rng.randint(100, 255), rng.randint(100, 255), 220),
            "size": rng.randint(4, 9),
        })
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        # 코드 드로우 컨페티 (배경 요소로 유지)
        for j, c in enumerate(confetti_data):
            if (i + j) % 2 == 0:
                dy = i * 6
                d.ellipse([c["x"] - c["size"], c["y"] + dy - c["size"],
                           c["x"] + c["size"], c["y"] + dy + c["size"]],
                          fill=c["color"])
        # party_popper
        popper = _load_asset("party_popper", 32)
        if popper:
            _place_asset(img, popper, 4, 4)
        else:
            d.polygon([(52, 10), (76, 10), (64, -5)], fill=(255, 100, 0, 200))
            d.line([(52, 10), (76, 10)], fill=(255, 200, 0, 200), width=2)
        # confetti 에셋 (상단 우측)
        confetti = _load_asset("confetti", 24)
        if confetti:
            _place_asset(img, confetti, 100, 4)
        frames.append(img)
    return frames


def _gen_spin(n: int) -> list[Image.Image]:
    """
    스핀: 코드 드로우 궤도 점 (유지) + dizzy.png(16px 선택적).
    """
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        # 회전 잔상 원 (코드 드로우 유지 — 기하학적 효과)
        for k in range(4):
            angle = math.radians((i * 45) + k * 90)
            px = int(64 + 48 * math.cos(angle))
            py = int(64 + 48 * math.sin(angle))
            alpha = 220 - k * 40
            d.ellipse([px - 6, py - 6, px + 6, py + 6],
                      fill=(255, 200, 0, alpha))
        # dizzy 선택적 액센트
        dizzy = _load_asset("dizzy", 16)
        if dizzy:
            _place_asset(img, dizzy, 56, 56)
        frames.append(img)
    return frames


def _gen_rainbow(n: int) -> list[Image.Image]:
    """
    무지개: 코드 드로우 색상 밴드 유지 (기하학적 패턴이라 에셋 불필요).
    """
    base_colors = [
        (255, 0, 0),
        (255, 127, 0),
        (255, 255, 0),
        (0, 200, 0),
        (0, 0, 255),
        (148, 0, 211),
    ]
    frames = []
    for i in range(n):
        img = _blank(255)
        d = ImageDraw.Draw(img)
        band_h = CANVAS // 6
        for j in range(6):
            rgb = base_colors[(j + i) % len(base_colors)]
            r, g, b = rgb
            d.rectangle([0, j * band_h, CANVAS, (j + 1) * band_h],
                        fill=(r, g, b, 180))
        frames.append(img)
    return frames


def _gen_thug(n: int) -> list[Image.Image]:
    """
    선글라스: sunglasses.png 위에서 아래로 드롭 (Y: -20 → 10 → 30 → 36)
              + 마지막 프레임 "deal with it" 텍스트.
    에셋 없으면 코드 드로우 선글라스 폴백.
    """
    # 프레임별 sunglasses Y 오프셋 (얼굴 눈 위치 기준 조정값)
    glass_y_offsets = [-20, 10, 30, 36]
    # 얼굴(x=32,y=24,w=64,h=64) 기준 눈은 약 y=44 근방 → 오버레이 절대 좌표
    base_glass_y = 44  # 눈 위치 절대 y
    frames = []
    for i in range(n):
        img = _blank()
        gy_abs = base_glass_y + glass_y_offsets[i % len(glass_y_offsets)]
        sunglasses = _load_asset("sunglasses", 64)
        if sunglasses:
            _place_asset(img, sunglasses, 32, gy_abs)
        else:
            d = ImageDraw.Draw(img)
            gy = glass_y_offsets[i % len(glass_y_offsets)]
            # 왼쪽 렌즈
            d.rectangle([20, gy + 32, 56, gy + 50], fill=(20, 20, 20, 230))
            d.rectangle([22, gy + 34, 54, gy + 48], fill=(40, 40, 80, 200))
            # 오른쪽 렌즈
            d.rectangle([72, gy + 32, 108, gy + 50], fill=(20, 20, 20, 230))
            d.rectangle([74, gy + 34, 106, gy + 48], fill=(40, 40, 80, 200))
            # 연결 다리
            d.rectangle([56, gy + 38, 72, gy + 44], fill=(60, 60, 60, 220))
            # 측면 다리
            d.line([(20, gy + 41), (4, gy + 41)], fill=(60, 60, 60, 200), width=3)
            d.line([(108, gy + 41), (124, gy + 41)], fill=(60, 60, 60, 200), width=3)
        # 마지막 프레임: "deal with it" 텍스트
        if i == n - 1:
            d = ImageDraw.Draw(img)
            d.text((18, 108), "deal with it", fill=(255, 255, 255, 200))
        frames.append(img)
    return frames


def _gen_cockroach(n: int) -> list[Image.Image]:
    """
    바퀴벌레: cockroach_emoji.png (메인 몸체, 얼굴은 위에 합성됨)
              + 코드 드로우 다리 애니메이션.
    에셋 없으면 코드 드로우 바퀴벌레 폴백.
    """
    body_offsets = [(-3, 0), (3, 0), (-3, 1), (3, -1)]
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        ox, oy = body_offsets[i % len(body_offsets)]
        bx, by = 64 + ox, 80 + oy
        body_w, body_h = 36, 52

        cockroach = _load_asset("cockroach_emoji", 56)
        if cockroach:
            # 에셋 배치 (다리 위에)
            _place_asset(img, cockroach, bx - 28, by - 28)
        else:
            # 폴백: 코드 드로우 몸통
            # 더듬이
            ant_lean = 4 * (1 if i % 2 == 0 else -1)
            d.line([(bx - 8, by - body_h // 2),
                    (bx - 20 + ant_lean, by - body_h // 2 - 20)],
                   fill=(80, 50, 20, 220), width=2)
            d.line([(bx + 8, by - body_h // 2),
                    (bx + 20 + ant_lean, by - body_h // 2 - 20)],
                   fill=(80, 50, 20, 220), width=2)
            # 몸통
            d.ellipse([bx - body_w // 2, by - body_h // 2,
                       bx + body_w // 2, by + body_h // 2],
                      fill=(120, 70, 30, 240))
            d.ellipse([bx - body_w // 4, by - body_h // 3,
                       bx + body_w // 6, by],
                      fill=(160, 100, 50, 120))

        # 다리 애니메이션 (코드 드로우 유지)
        leg_angles = [30, 0, -30] if i % 2 == 0 else [20, 10, -20]
        leg_y_offsets = [-14, 0, 14]
        for j, (la, lyo) in enumerate(zip(leg_angles, leg_y_offsets)):
            lx_start = bx - body_w // 2
            ly_start = by + lyo
            lx_end = lx_start - int(18 * math.cos(math.radians(la)))
            ly_end = ly_start + int(18 * math.sin(math.radians(abs(la))))
            d.line([(lx_start, ly_start), (lx_end, ly_end)],
                   fill=(80, 50, 20, 200), width=2)
            rx_start = bx + body_w // 2
            rx_end = rx_start + int(18 * math.cos(math.radians(la)))
            ry_end = ly_start + int(18 * math.sin(math.radians(abs(la))))
            d.line([(rx_start, ly_start), (rx_end, ry_end)],
                   fill=(80, 50, 20, 200), width=2)

        frames.append(img)
    return frames


def _gen_rip(n: int) -> list[Image.Image]:
    """
    RIP: skull.png(24px 코너) + 코드 드로우 묘비 (개선).
    에셋 없으면 코드 드로우 폴백.
    """
    alphas = [200, 160, 120, 70]
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        a = alphas[i % len(alphas)]
        # 묘비 (코드 드로우 개선)
        d.rectangle([44, 68, 84, 112], fill=(160, 160, 165, a))
        d.ellipse([44, 56, 84, 80], fill=(160, 160, 165, a))
        # 십자가
        d.line([(64, 58), (64, 72)], fill=(100, 100, 105, a), width=3)
        d.line([(57, 63), (71, 63)], fill=(100, 100, 105, a), width=3)
        # RIP 텍스트
        d.text((52, 82), "RIP", fill=(60, 60, 65, a))
        # 해골 (skull 에셋 코너 장식)
        skull = _load_asset("skull", 24)
        if skull:
            r, g, b, alpha_ch = skull.split()
            alpha_ch = alpha_ch.point(lambda x: int(x * a / 255))
            skull = Image.merge("RGBA", (r, g, b, alpha_ch))
            _place_asset(img, skull, 96, 6)
        frames.append(img)
    return frames


# ---- Reaction ----

def _gen_ok(n: int) -> list[Image.Image]:
    """
    OK: thumbs_up.png(32px 하단좌측) + 코드 드로우 "OK!" 텍스트.
    에셋 없으면 코드 드로우 폴백.
    """
    thumb_y_positions = [88, 78, 88]
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        ty = thumb_y_positions[i % len(thumb_y_positions)]
        thumb = _load_asset("thumbs_up", 32)
        if thumb:
            _place_asset(img, thumb, 6, ty)
        else:
            d.ellipse([8, ty - 20, 28, ty], fill=(255, 200, 150, 220))
            d.rectangle([10, ty, 28, ty + 18], fill=(255, 200, 150, 220))
        # "OK!" 텍스트
        d.text((8, ty + 34), "OK!", fill=(50, 180, 50, 230))
        frames.append(img)
    return frames


def _gen_no(n: int) -> list[Image.Image]:
    """
    NO: cross_mark.png(28px 하단중앙) + 코드 드로우 "NO" 텍스트.
    에셋 없으면 코드 드로우 X 폴백.
    """
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        offset = 4 if i % 2 == 0 else -4
        cross = _load_asset("cross_mark", 28)
        if cross:
            _place_asset(img, cross, 50 + offset, 88)
        else:
            d.line([(6 + offset, 98), (28 + offset, 120)],
                   fill=(220, 30, 30, 230), width=5)
            d.line([(28 + offset, 98), (6 + offset, 120)],
                   fill=(220, 30, 30, 230), width=5)
        d.text((10 + offset, 85), "NO", fill=(220, 30, 30, 230))
        frames.append(img)
    return frames


def _gen_question(n: int) -> list[Image.Image]:
    """
    물음표: question_mark.png(32px 상단우측) 팝인 스케일 애니메이션.
    에셋 없으면 코드 드로우 "?" 폴백.
    """
    # 팝인: 0.6x → 1.0x → 0.85x
    scales = [0.6, 1.0, 0.85]
    base_size = 32
    frames = []
    for i in range(n):
        img = _blank()
        s = scales[i % len(scales)]
        sz = max(1, int(base_size * s))
        qmark = _load_asset("question_mark", sz)
        if qmark:
            # 크기 변화에 따라 위치를 중앙 고정
            offset = (base_size - sz) // 2
            _place_asset(img, qmark, 90 + offset, 4 + offset)
        else:
            d = ImageDraw.Draw(img)
            d.text((int(92 - sz // 4), int(10 - (sz - 30) // 2)),
                   "?", fill=(255, 180, 0, 220))
        frames.append(img)
    return frames


def _gen_exclaim(n: int) -> list[Image.Image]:
    """
    느낌표: exclamation.png(32px 상단우측) 팝인 스케일 애니메이션.
    에셋 없으면 코드 드로우 "!" 폴백.
    """
    # 팝인: 0.6x → 1.0x → 0.6x
    scales = [0.6, 1.0, 0.6]
    base_size = 32
    frames = []
    for i in range(n):
        img = _blank()
        s = scales[i % len(scales)]
        sz = max(1, int(base_size * s))
        exclam = _load_asset("exclamation", sz)
        if exclam:
            offset = (base_size - sz) // 2
            _place_asset(img, exclam, 90 + offset, 4 + offset)
        else:
            d = ImageDraw.Draw(img)
            d.rectangle([100, 8, 108, 8 + sz], fill=(255, 80, 0, 220))
            d.ellipse([100, 8 + sz + 4, 108, 8 + sz + 12], fill=(255, 80, 0, 220))
        frames.append(img)
    return frames


def _gen_clap(n: int) -> list[Image.Image]:
    """
    박수: clap.png(36px 하단중앙) + sparkles.png(12px 양옆).
    에셋 없으면 코드 드로우 폴백.
    """
    frames = []
    for i in range(n):
        img = _blank()
        d = ImageDraw.Draw(img)
        # clap 에셋
        clap = _load_asset("clap", 36)
        if clap:
            _place_asset(img, clap, 46, 88)
        else:
            # 코드 드로우 파동
            if i % 2 == 0:
                for r in range(10, 40, 10):
                    alpha = max(0, 200 - r * 4)
                    d.ellipse([64 - r, CANVAS - 30 - r, 64 + r, CANVAS - 30 + r],
                              outline=(255, 200, 100, alpha), width=2)
        # sparkles 양옆
        sparkle_l = _load_asset("sparkles", 12)
        sparkle_r = _load_asset("sparkles", 12)
        if sparkle_l:
            _place_asset(img, sparkle_l, 4, 94)
        else:
            _draw_star(d, 10, 100, 6, (255, 220, 50, 200))
        if sparkle_r:
            _place_asset(img, sparkle_r, 112, 94)
        else:
            _draw_star(d, 118, 100, 6, (255, 220, 50, 200))
        frames.append(img)
    return frames
