"""
core/template_engine.py
템플릿 합성 엔진 — 사용자 얼굴을 템플릿 프레임에 합성하여 애니메이션 GIF를 생성한다.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

CANVAS_SIZE = 128  # Slack 이모티콘 권장 크기


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class FacePlacement:
    """단일 프레임에서 얼굴 이미지를 배치할 위치/크기/변환 정보."""
    frame: int
    x: int
    y: int
    w: int
    h: int
    rotation: float = 0.0
    opacity: int = 255

    @classmethod
    def from_dict(cls, d: dict) -> "FacePlacement":
        return cls(
            frame=d["frame"],
            x=d["x"],
            y=d["y"],
            w=d["w"],
            h=d["h"],
            rotation=d.get("rotation", 0.0),
            opacity=d.get("opacity", 255),
        )


@dataclass
class LayerConfig:
    """레이어 하나의 설정 (background / face / overlay)."""
    type: str           # "background" | "face" | "overlay"
    z_order: int = 0
    color: Optional[str] = None        # background 레이어용 RGBA hex
    file: Optional[str] = None         # overlay 레이어용 파일 패턴 (e.g. "overlay_{frame}.png")

    @classmethod
    def from_dict(cls, d: dict) -> "LayerConfig":
        return cls(
            type=d["type"],
            z_order=d.get("z_order", 0),
            color=d.get("color"),
            file=d.get("file"),
        )


@dataclass
class Template:
    """로드된 템플릿 — config + 프레임 에셋."""
    id: str
    name: str
    category: str
    frames: int
    duration_ms: int
    animation_type: str
    face_placements: list[FacePlacement]
    layers: list[LayerConfig]
    # 프레임 번호(1-indexed) → overlay PIL.Image (없으면 None)
    overlay_images: dict[int, Optional[Image.Image]] = field(default_factory=dict)
    template_dir: str = ""

    def get_placement(self, frame_no: int) -> Optional[FacePlacement]:
        """1-indexed 프레임 번호로 FacePlacement를 반환한다."""
        for p in self.face_placements:
            if p.frame == frame_no:
                return p
        return None

    def get_background_color(self) -> tuple[int, int, int, int]:
        """background 레이어의 색상을 RGBA 튜플로 반환한다. 기본값: 완전 투명."""
        for layer in sorted(self.layers, key=lambda l: l.z_order):
            if layer.type == "background" and layer.color:
                color_hex = layer.color.lstrip("#")
                if len(color_hex) == 8:
                    r, g, b, a = (int(color_hex[i:i+2], 16) for i in (0, 2, 4, 6))
                    return (r, g, b, a)
                elif len(color_hex) == 6:
                    r, g, b = (int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                    return (r, g, b, 255)
        return (0, 0, 0, 0)  # 투명


# ---------------------------------------------------------------------------
# 템플릿 엔진
# ---------------------------------------------------------------------------

class TemplateEngine:
    """
    템플릿 디렉토리를 로드하고, 얼굴 이미지를 합성하여 GIF를 생성한다.

    사용 예::

        engine = TemplateEngine()
        template = engine.load_template("templates/emotions/happy")
        gif_bytes = engine.render_emoji(template, face_image)
    """

    # ------------------------------------------------------------------
    # 템플릿 로드
    # ------------------------------------------------------------------

    def load_template(self, template_dir: str) -> Template:
        """
        template_dir 내의 config.json을 파싱하고 overlay 이미지를 로드한다.

        Parameters
        ----------
        template_dir:
            config.json 및 프레임 에셋이 위치한 디렉토리 경로.

        Returns
        -------
        Template
            로드된 Template 객체.
        """
        config_path = os.path.join(template_dir, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        face_placements = [FacePlacement.from_dict(p) for p in cfg.get("face_placements", [])]
        layers = sorted(
            [LayerConfig.from_dict(l) for l in cfg.get("layers", [])],
            key=lambda l: l.z_order,
        )

        template = Template(
            id=cfg["id"],
            name=cfg["name"],
            category=cfg["category"],
            frames=cfg["frames"],
            duration_ms=cfg.get("duration_ms", 150),
            animation_type=cfg.get("animation_type", "bounce"),
            face_placements=face_placements,
            layers=layers,
            template_dir=template_dir,
        )

        # overlay 이미지 로드
        for layer in layers:
            if layer.type == "overlay" and layer.file:
                for frame_no in range(1, template.frames + 1):
                    filename = layer.file.replace("{frame}", str(frame_no))
                    overlay_path = os.path.join(template_dir, filename)
                    if os.path.exists(overlay_path):
                        try:
                            img = Image.open(overlay_path).convert("RGBA")
                            img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
                            template.overlay_images[frame_no] = img
                        except Exception as e:
                            logger.warning("overlay 로드 실패 %s: %s", overlay_path, e)
                            template.overlay_images[frame_no] = None
                    else:
                        template.overlay_images[frame_no] = None

        return template

    # ------------------------------------------------------------------
    # 프레임 렌더링
    # ------------------------------------------------------------------

    def render_frames(self, template: Template, face_image: Image.Image) -> list[Image.Image]:
        """
        템플릿의 모든 프레임을 렌더링하여 PIL.Image 리스트로 반환한다.

        Parameters
        ----------
        template:
            로드된 Template 객체.
        face_image:
            RGBA 모드의 얼굴 이미지 (배경 제거된 상태 권장).

        Returns
        -------
        list[PIL.Image]
            128x128 RGBA 이미지 리스트 (frame 수만큼).
        """
        face_rgba = face_image.convert("RGBA")
        rendered: list[Image.Image] = []

        for frame_no in range(1, template.frames + 1):
            canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))

            # 레이어 순서대로 합성
            for layer in sorted(template.layers, key=lambda l: l.z_order):
                if layer.type == "background":
                    bg_color = template.get_background_color()
                    bg = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), bg_color)
                    canvas = Image.alpha_composite(canvas, bg)

                elif layer.type == "face":
                    placement = template.get_placement(frame_no)
                    if placement:
                        face_frame = self._render_face(face_rgba, placement)
                        canvas = Image.alpha_composite(canvas, face_frame)

                elif layer.type == "overlay":
                    overlay = template.overlay_images.get(frame_no)
                    if overlay:
                        canvas = Image.alpha_composite(canvas, overlay)

            rendered.append(canvas)

        return rendered

    def _render_face(self, face_rgba: Image.Image, placement: FacePlacement) -> Image.Image:
        """
        얼굴 이미지를 placement에 따라 크기 조정, 회전, 불투명도 적용 후
        128x128 캔버스에 배치한 이미지를 반환한다.
        """
        # 크기 조정
        resized = face_rgba.resize((placement.w, placement.h), Image.LANCZOS)

        # 회전 (rotate는 원본 크기 유지, expand=True로 잘림 방지)
        if placement.rotation != 0:
            resized = resized.rotate(
                -placement.rotation,  # PIL은 반시계 방향 양수 → 시계 방향 음수 변환
                resample=Image.BICUBIC,
                expand=True,
            )
            # expand 후 다시 w x h로 크롭/리사이즈
            resized = resized.resize((placement.w, placement.h), Image.LANCZOS)

        # 불투명도 조정
        if placement.opacity < 255:
            r, g, b, a = resized.split()
            a = a.point(lambda v: int(v * placement.opacity / 255))
            resized = Image.merge("RGBA", (r, g, b, a))

        # 캔버스에 배치
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
        canvas.paste(resized, (placement.x, placement.y), resized)
        return canvas

    # ------------------------------------------------------------------
    # 애니메이션 오버라이드 (animation_type 기반 동적 placement 생성)
    # ------------------------------------------------------------------

    def _apply_animation(
        self,
        template: Template,
        face_image: Image.Image,
    ) -> list[Image.Image]:
        """
        config의 face_placements 대신 animation_type에 따라 동적으로
        placement를 계산하여 프레임을 렌더링한다.
        config에 face_placements가 정의되어 있으면 그것을 우선 사용한다.
        """
        # config에 face_placements가 있으면 기본 렌더러 사용
        if template.face_placements:
            return self.render_frames(template, face_image)

        atype = template.animation_type
        n = template.frames
        # 기본 얼굴 위치: 중앙 64x64
        cx, cy, fw, fh = 32, 32, 64, 64

        placements: list[FacePlacement] = []
        for i in range(n):
            t = i / max(n - 1, 1)  # 0.0 ~ 1.0

            dx, dy, rot, op = 0, 0, 0.0, 255

            if atype == "bounce":
                dy = int(-8 * math.sin(t * math.pi))
            elif atype == "shake":
                dx = int(8 * math.sin(t * 2 * math.pi))
            elif atype == "spin":
                rot = 360 * t
            elif atype == "pulse":
                scale = 1.0 + 0.2 * math.sin(t * math.pi)
                fw2 = int(fw * scale)
                fh2 = int(fh * scale)
                offset_x = (fw - fw2) // 2
                offset_y = (fh - fh2) // 2
                placements.append(FacePlacement(
                    frame=i + 1,
                    x=cx + offset_x,
                    y=cy + offset_y,
                    w=fw2,
                    h=fh2,
                ))
                continue
            elif atype == "fade_in":
                op = int(255 * t)
            elif atype == "fade_out":
                op = int(255 * (1 - t))
            elif atype == "vibrate":
                dx = random.randint(-4, 4)
                dy = random.randint(-4, 4)

            placements.append(FacePlacement(
                frame=i + 1,
                x=cx + dx,
                y=cy + dy,
                w=fw,
                h=fh,
                rotation=rot,
                opacity=op,
            ))

        # 임시로 template의 placements를 교체하여 렌더링
        original = template.face_placements
        template.face_placements = placements
        frames = self.render_frames(template, face_image)
        template.face_placements = original
        return frames

    # ------------------------------------------------------------------
    # GIF 생성
    # ------------------------------------------------------------------

    def render_emoji(self, template: Template, face_image: Image.Image) -> bytes:
        """
        템플릿과 얼굴 이미지로 애니메이션 GIF를 생성하여 bytes로 반환한다.

        Parameters
        ----------
        template:
            로드된 Template 객체.
        face_image:
            얼굴 이미지 (배경 제거 권장).

        Returns
        -------
        bytes
            GIF 파일의 바이너리 데이터.
        """
        frames = self._apply_animation(template, face_image)
        return self._frames_to_gif(frames, template.duration_ms)

    @staticmethod
    def _frames_to_gif(frames: list[Image.Image], duration_ms: int) -> bytes:
        """
        RGBA PIL Image 리스트를 팔레트 기반 GIF bytes로 변환한다.
        투명도를 최대한 보존하기 위해 P 모드 변환 시 transparency 처리를 수행한다.
        """
        if not frames:
            raise ValueError("프레임이 없습니다.")

        # GIF는 RGBA를 직접 지원하지 않으므로 팔레트 변환 필요
        # 흰 배경 합성 후 P 모드 변환 (투명 GIF 대신 단순 방식)
        palette_frames: list[Image.Image] = []
        for frame in frames:
            # 흰 배경에 RGBA 합성
            bg = Image.new("RGBA", frame.size, (255, 255, 255, 255))
            composite = Image.alpha_composite(bg, frame)
            # RGB로 변환 후 팔레트 양자화
            rgb = composite.convert("RGB")
            quantized = rgb.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
            palette_frames.append(quantized)

        buf = io.BytesIO()
        palette_frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=palette_frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return buf.getvalue()

    # ------------------------------------------------------------------
    # 유틸리티
    # ------------------------------------------------------------------

    def render_preview(self, template: Template, face_image: Image.Image) -> Image.Image:
        """첫 번째 프레임만 렌더링하여 미리보기 이미지를 반환한다."""
        frames = self._apply_animation(template, face_image)
        return frames[0] if frames else Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE))
