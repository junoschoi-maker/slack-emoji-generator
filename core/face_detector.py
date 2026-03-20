"""
face_detector.py — 얼굴 감지 및 크롭 모듈
mediapipe Tasks API (0.10.x+) 사용
"""

import logging
import os
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 모델 파일 경로
_MODEL_DIR = os.path.join(os.path.expanduser("~"), ".mediapipe", "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "blaze_face_short_range.tflite")
_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"


def _ensure_model() -> str:
    """모델 파일이 없으면 자동 다운로드하고 경로를 반환."""
    if os.path.exists(_MODEL_PATH):
        return _MODEL_PATH
    os.makedirs(_MODEL_DIR, exist_ok=True)
    logger.info("얼굴 감지 모델 다운로드 중: %s", _MODEL_URL)
    import urllib.request
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    logger.info("모델 다운로드 완료: %s bytes", os.path.getsize(_MODEL_PATH))
    return _MODEL_PATH


def detect_and_crop_face(image: Image.Image, padding: float = 0.20) -> Image.Image:
    """
    입력 이미지에서 얼굴을 감지하고 패딩을 포함해 크롭하여 RGBA로 반환.

    Args:
        image: PIL Image (RGB 또는 RGBA)
        padding: 얼굴 bounding box 기준 여백 비율 (기본 20%)

    Returns:
        RGBA 크롭 이미지

    Raises:
        ValueError: 얼굴이 감지되지 않은 경우
    """
    import mediapipe as mp

    logger.debug("얼굴 감지 시작: 이미지 크기 %s", image.size)

    # RGBA → RGB 변환
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        rgb_image = background
    elif image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image

    img_array = np.array(rgb_image)
    h, w = img_array.shape[:2]

    # mediapipe Tasks API
    model_path = _ensure_model()
    BaseOptions = mp.tasks.BaseOptions
    FaceDetector = mp.tasks.vision.FaceDetector
    FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions

    options = FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        min_detection_confidence=0.5,
    )

    with FaceDetector.create_from_options(options) as detector:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_array)
        result = detector.detect(mp_image)

    if not result.detections:
        logger.warning("얼굴이 감지되지 않았습니다.")
        raise ValueError("이미지에서 얼굴을 찾을 수 없습니다.")

    # 신뢰도가 가장 높은 얼굴 선택
    best = max(result.detections, key=lambda d: d.categories[0].score)
    bbox = best.bounding_box

    logger.debug(
        "얼굴 감지 완료: score=%.3f, bbox=(%d, %d, %d, %d)",
        best.categories[0].score,
        bbox.origin_x, bbox.origin_y, bbox.width, bbox.height,
    )

    # 픽셀 좌표 (Tasks API는 이미 픽셀 단위)
    x1 = bbox.origin_x
    y1 = bbox.origin_y
    x2 = bbox.origin_x + bbox.width
    y2 = bbox.origin_y + bbox.height

    # 패딩 적용 (이미지 경계 클리핑)
    pad_x = int((x2 - x1) * padding)
    pad_y = int((y2 - y1) * padding)

    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    cropped = rgb_image.crop((x1, y1, x2, y2))
    cropped_rgba = cropped.convert("RGBA")

    logger.debug("크롭 완료: 크기 %s", cropped_rgba.size)
    return cropped_rgba


def get_face_landmarks(image: Image.Image) -> dict:
    """
    얼굴의 주요 랜드마크 좌표를 반환.
    FaceDetector keypoints 기반 (픽셀 좌표).

    Args:
        image: PIL Image

    Returns:
        {"right_eye": (x, y), "left_eye": (x, y), "nose_tip": (x, y), ...}
        — 감지 실패 시 빈 dict 반환
    """
    import mediapipe as mp

    logger.debug("랜드마크 추출 시작")

    if image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image

    img_array = np.array(rgb_image)
    h, w = img_array.shape[:2]

    model_path = _ensure_model()
    BaseOptions = mp.tasks.BaseOptions
    FaceDetector = mp.tasks.vision.FaceDetector
    FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions

    KP_NAMES = [
        "right_eye",
        "left_eye",
        "nose_tip",
        "mouth_center",
        "right_ear",
        "left_ear",
    ]

    options = FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        min_detection_confidence=0.5,
    )

    with FaceDetector.create_from_options(options) as detector:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_array)
        result = detector.detect(mp_image)

    if not result.detections:
        logger.warning("랜드마크 추출 실패: 얼굴 없음")
        return {}

    best = max(result.detections, key=lambda d: d.categories[0].score)
    keypoints = best.keypoints

    landmarks: dict = {}
    if keypoints:
        for idx, name in enumerate(KP_NAMES):
            if idx < len(keypoints):
                kp = keypoints[idx]
                landmarks[name] = (int(kp.x * w), int(kp.y * h))

    logger.debug("랜드마크 추출 완료: %s", landmarks)
    return landmarks
