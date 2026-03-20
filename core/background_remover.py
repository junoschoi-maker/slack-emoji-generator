"""
background_remover.py — 배경 제거 모듈
rembg 라이브러리 사용
"""

import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def remove_background(
    image: Image.Image,
    model: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> Image.Image:
    """
    rembg를 사용해 이미지 배경을 제거하고 RGBA 이미지를 반환.

    Args:
        image: PIL Image (RGB 또는 RGBA)
        model: rembg 모델 이름 (기본: "u2net")
               옵션: "u2net", "u2netp", "u2net_human_seg", "silueta"
        alpha_matting: 알파 매팅 활성화 여부 (경계선 품질 향상, 느림)
        alpha_matting_foreground_threshold: 전경 임계값
        alpha_matting_background_threshold: 배경 임계값
        alpha_matting_erode_size: 침식 크기

    Returns:
        RGBA PIL Image (배경 투명)

    Raises:
        ImportError: rembg가 설치되지 않은 경우
        RuntimeError: 배경 제거 처리 실패 시
    """
    try:
        from rembg import remove, new_session
    except ImportError as e:
        raise ImportError(
            "rembg가 설치되어 있지 않습니다. `pip install rembg`를 실행하세요."
        ) from e

    logger.debug("배경 제거 시작: 이미지 크기 %s, 모드 %s", image.size, image.mode)

    # RGBA 입력은 RGB로 변환 후 처리 (rembg가 RGBA를 직접 받지 못하는 경우 대비)
    if image.mode == "RGBA":
        # 흰 배경에 합성하여 RGB로 변환
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        input_image = background
        logger.debug("RGBA → RGB 변환 완료")
    elif image.mode != "RGB":
        input_image = image.convert("RGB")
        logger.debug("이미지 모드 %s → RGB 변환", image.mode)
    else:
        input_image = image

    try:
        # 세션 생성 (모델 다운로드/캐시 처리)
        session = new_session(model)
        logger.debug("rembg 세션 생성: 모델=%s", model)

        result: Image.Image = remove(
            input_image,
            session=session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )
    except Exception as e:
        logger.error("배경 제거 실패: %s", e)
        raise RuntimeError(f"배경 제거 중 오류가 발생했습니다: {e}") from e

    # 결과가 RGBA인지 확인
    if result.mode != "RGBA":
        result = result.convert("RGBA")

    logger.debug("배경 제거 완료: 결과 크기 %s, 모드 %s", result.size, result.mode)
    return result


def remove_background_from_bytes(
    image_bytes: bytes,
    model: str = "u2net",
) -> Image.Image:
    """
    바이트 스트림에서 직접 배경을 제거.
    rembg의 native bytes 인터페이스를 활용하여 성능 최적화.

    Args:
        image_bytes: 원본 이미지 바이트 (JPEG, PNG 등)
        model: rembg 모델 이름

    Returns:
        RGBA PIL Image

    Raises:
        ImportError: rembg가 설치되지 않은 경우
    """
    try:
        from rembg import remove, new_session
    except ImportError as e:
        raise ImportError(
            "rembg가 설치되어 있지 않습니다. `pip install rembg`를 실행하세요."
        ) from e

    logger.debug("바이트 스트림에서 배경 제거 시작: %d bytes", len(image_bytes))

    session = new_session(model)
    result_bytes: bytes = remove(image_bytes, session=session)

    result_image = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    logger.debug("배경 제거 완료 (bytes): %d bytes → RGBA", len(result_bytes))
    return result_image
