"""
gif_generator.py — Slack 최적화 애니메이션 GIF 생성 모듈
Pillow 사용 / 128x128px, 최대 128KB 제약 준수
"""

import io
import logging
import os
from typing import List

from PIL import Image

logger = logging.getLogger(__name__)

# Slack 이모티콘 스펙
SLACK_SIZE = (128, 128)
SLACK_MAX_KB = 128
SLACK_MAX_BYTES = SLACK_MAX_KB * 1024


def _resize_frame(frame: Image.Image, size: tuple[int, int] = SLACK_SIZE) -> Image.Image:
    """
    프레임을 지정 크기로 리사이즈 (RGBA 유지, LANCZOS 보간).
    """
    if frame.size == size:
        return frame
    resized = frame.resize(size, Image.LANCZOS)
    if resized.mode != "RGBA":
        resized = resized.convert("RGBA")
    return resized


def _frame_to_p_mode(frame: Image.Image, colors: int = 256) -> Image.Image:
    """
    RGBA 프레임을 팔레트(P) 모드로 변환 (투명도 보존).
    GIF는 팔레트 모드만 지원.

    Args:
        frame: RGBA PIL Image
        colors: 팔레트 색상 수 (2~256)

    Returns:
        P 모드 PIL Image (투명도 포함)
    """
    # 알파 채널 분리
    alpha = frame.split()[3]

    # 색상 양자화 (RGBA → P)
    # RGBA는 MEDIANCUT 불가 → FASTOCTREE(method=2) 사용
    quantized = frame.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)

    # 투명 인덱스 처리: 알파 < 128인 픽셀을 투명 색상(255번 팔레트)으로 교체
    # Pillow의 quantize는 transparency 파라미터 미지원이므로 수동 처리
    mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)  # 투명 영역 마스크
    quantized_array = quantized.load()
    mask_array = mask.load()
    w, h = quantized.size

    # 투명 인덱스로 사용할 팔레트 슬롯 (마지막 슬롯)
    transparent_index = colors - 1

    for y in range(h):
        for x in range(w):
            if mask_array[x, y] == 255:
                quantized_array[x, y] = transparent_index

    quantized.info["transparency"] = transparent_index
    return quantized


def create_animated_gif(
    frames: List[Image.Image],
    duration_ms: int = 150,
    loop: int = 0,
) -> bytes:
    """
    PIL Image 프레임 목록으로 Slack 최적화 애니메이션 GIF를 생성.

    Args:
        frames: PIL Image 목록 (순서대로 재생)
        duration_ms: 각 프레임 표시 시간 (밀리초, 기본 150ms)
        loop: 반복 횟수 (0 = 무한 반복)

    Returns:
        GIF 파일 바이트 (최적화 완료)

    Raises:
        ValueError: 프레임 목록이 비어있는 경우
    """
    if not frames:
        raise ValueError("프레임 목록이 비어있습니다.")

    logger.debug("GIF 생성 시작: %d 프레임, duration=%dms", len(frames), duration_ms)

    # 1. 모든 프레임을 128x128 RGBA로 정규화
    normalized: List[Image.Image] = [_resize_frame(f) for f in frames]

    # 2. 첫 프레임 기준으로 GIF 생성
    gif_bytes = _encode_gif(normalized, duration_ms=duration_ms, loop=loop, colors=256)

    logger.debug("GIF 생성 완료: %d bytes (%.1f KB)", len(gif_bytes), len(gif_bytes) / 1024)

    # 3. 크기 초과 시 자동 최적화
    if len(gif_bytes) > SLACK_MAX_BYTES:
        logger.info(
            "GIF 크기 초과 (%.1f KB > %d KB), 최적화 시도...",
            len(gif_bytes) / 1024, SLACK_MAX_KB,
        )
        gif_bytes = optimize_gif_size(gif_bytes, max_size_kb=SLACK_MAX_KB, frames=normalized)

    return gif_bytes


def _encode_gif(
    frames: List[Image.Image],
    duration_ms: int,
    loop: int,
    colors: int,
) -> bytes:
    """
    RGBA 프레임 목록을 GIF 바이트로 인코딩 (내부 헬퍼).
    """
    p_frames = [_frame_to_p_mode(f, colors=colors) for f in frames]

    buf = io.BytesIO()
    p_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=p_frames[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
        disposal=2,  # 2 = 이전 프레임 지우기 (배경 투명 처리 핵심)
    )
    return buf.getvalue()


def optimize_gif_size(
    gif_bytes: bytes,
    max_size_kb: int = 128,
    frames: List[Image.Image] | None = None,
) -> bytes:
    """
    GIF가 max_size_kb를 초과할 경우 단계적으로 크기를 축소.

    최적화 순서:
      1. 색상 수 축소: 256 → 128 → 64 → 32
      2. 프레임 수 축소: 홀수 프레임 제거
      3. 해상도 축소: 128x128 → 96x96 → 64x64

    Args:
        gif_bytes: 원본 GIF 바이트
        max_size_kb: 허용 최대 크기 (KB)
        frames: 원본 RGBA 프레임 목록 (제공 시 재인코딩으로 품질 향상)

    Returns:
        최적화된 GIF 바이트 (목표 미달성 시 최선의 결과 반환)
    """
    max_bytes = max_size_kb * 1024
    current_bytes = gif_bytes

    if len(current_bytes) <= max_bytes:
        return current_bytes

    # 원본 프레임이 없으면 GIF에서 추출
    if frames is None:
        frames = _extract_frames_from_gif(gif_bytes)

    if not frames:
        logger.warning("프레임 추출 실패, 원본 GIF 반환")
        return gif_bytes

    current_frames = list(frames)
    # GIF 메타에서 duration 읽기
    try:
        original_gif = Image.open(io.BytesIO(gif_bytes))
        duration_ms = original_gif.info.get("duration", 150)
    except Exception:
        duration_ms = 150

    # ── 단계 1: 색상 수 축소 ──────────────────────────────────────────────
    for colors in [128, 64, 32]:
        candidate = _encode_gif(current_frames, duration_ms=duration_ms, loop=0, colors=colors)
        logger.debug("색상 축소 %d: %.1f KB", colors, len(candidate) / 1024)
        if len(candidate) <= max_bytes:
            logger.info("색상 %d로 최적화 완료: %.1f KB", colors, len(candidate) / 1024)
            return candidate
        current_bytes = candidate  # 최선 후보 갱신

    # ── 단계 2: 프레임 수 축소 ───────────────────────────────────────────
    # 홀수 인덱스 프레임 제거로 프레임 수를 절반으로
    while len(current_frames) > 1:
        current_frames = current_frames[::2]  # 짝수 인덱스만 유지
        # 애니메이션 속도 유지를 위해 duration 조정
        adjusted_duration = max(duration_ms, 100)

        for colors in [128, 64, 32]:
            candidate = _encode_gif(
                current_frames,
                duration_ms=adjusted_duration,
                loop=0,
                colors=colors,
            )
            logger.debug(
                "프레임 %d, 색상 %d: %.1f KB",
                len(current_frames), colors, len(candidate) / 1024,
            )
            if len(candidate) <= max_bytes:
                logger.info(
                    "프레임 %d, 색상 %d로 최적화 완료: %.1f KB",
                    len(current_frames), colors, len(candidate) / 1024,
                )
                return candidate
            current_bytes = candidate

        if len(current_frames) <= 1:
            break

    # ── 단계 3: 해상도 축소 ──────────────────────────────────────────────
    for size in [(96, 96), (64, 64)]:
        downscaled = [f.resize(size, Image.LANCZOS) for f in current_frames]

        for colors in [128, 64, 32]:
            candidate = _encode_gif(
                downscaled,
                duration_ms=duration_ms,
                loop=0,
                colors=colors,
            )
            logger.debug(
                "해상도 %s, 색상 %d: %.1f KB",
                size, colors, len(candidate) / 1024,
            )
            if len(candidate) <= max_bytes:
                logger.info(
                    "해상도 %s, 색상 %d로 최적화 완료: %.1f KB",
                    size, colors, len(candidate) / 1024,
                )
                return candidate
            current_bytes = candidate

    # 모든 단계 실패 — 최선의 결과 반환
    logger.warning(
        "목표 크기 달성 실패. 최선 결과: %.1f KB (목표: %d KB)",
        len(current_bytes) / 1024, max_size_kb,
    )
    return current_bytes


def _extract_frames_from_gif(gif_bytes: bytes) -> List[Image.Image]:
    """
    GIF 바이트에서 RGBA 프레임 목록을 추출.
    """
    frames: List[Image.Image] = []
    try:
        gif = Image.open(io.BytesIO(gif_bytes))
        for i in range(getattr(gif, "n_frames", 1)):
            gif.seek(i)
            frames.append(gif.copy().convert("RGBA"))
    except Exception as e:
        logger.error("GIF 프레임 추출 실패: %s", e)
    return frames


def save_gif(gif_bytes: bytes, output_path: str) -> str:
    """
    GIF 바이트를 파일로 저장.

    Args:
        gif_bytes: GIF 파일 바이트
        output_path: 저장 경로 (파일명 포함)

    Returns:
        저장된 파일의 절대 경로

    Raises:
        OSError: 파일 저장 실패 시
    """
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, "wb") as f:
            f.write(gif_bytes)
        logger.info(
            "GIF 저장 완료: %s (%.1f KB)",
            output_path, len(gif_bytes) / 1024,
        )
    except OSError as e:
        logger.error("GIF 저장 실패: %s — %s", output_path, e)
        raise

    return output_path
