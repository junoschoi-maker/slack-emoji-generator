# Slack Emoji Generator - Project Instructions

## Overview
프로필 사진 → 배경 제거 → 얼굴 감지 → 템플릿 합성 → 움직이는 GIF 이모티콘 세트 생성

## Tech Stack
- Python 3.11+
- Streamlit (Web UI)
- Pillow (이미지 처리, GIF 생성)
- rembg (배경 제거)
- mediapipe (얼굴 감지)

## Constraints
- Slack emoji: 128x128px, <128KB, GIF format
- Animation: 2~4 frames, simple (bounce, shake, spin, fade)
- Templates: JSON config + PNG frame layers

## Directory Structure
- `app.py` — Streamlit main app
- `core/` — Core engine modules
- `templates/` — Template assets and configs
- `output/` — Generated emoji output
- `tests/` — Unit tests

## Coding Standards
- Korean comments where helpful
- Type hints on all functions
- No hardcoded secrets — use .env + os.getenv()
