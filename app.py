"""
app.py — Slack 이모티콘 생성기 (Streamlit 메인 앱)

사용법:
    streamlit run app.py
"""

import io
import logging
import os
import tempfile
import zipfile
from typing import Optional

import streamlit as st
from PIL import Image

# 코어 모듈 임포트
from core.background_remover import remove_background
from core.face_detector import detect_and_crop_face
from core.template_engine import TemplateEngine
from core.emoji_set import (
    get_all_emoji_configs,
    get_emoji_by_category,
    get_emoji_by_id,
    generate_template_assets,
    generate_all_template_assets,
)
from core.gif_generator import create_animated_gif, optimize_gif_size

# ──────────────────────────────────────────────────────────────────────────────
# 상수 정의
# ──────────────────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# 카테고리 표시명 매핑
CATEGORY_LABELS: dict[str, str] = {
    "emotions": "감정",
    "work": "업무",
    "funny": "개그",
    "reaction": "리액션",
}

# 카테고리 순서
CATEGORY_ORDER = ["emotions", "work", "funny", "reaction"]

# 그리드 컬럼 수
GRID_COLUMNS = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Slack 이모티콘 생성기",
    page_icon="😄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    /* 헤더 */
    .main-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: #6B7280;
        font-size: 1.05rem;
    }

    /* 단계 헤더 */
    .step-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.8rem 0 0.8rem 0;
    }
    .step-badge {
        background: #4F46E5;
        color: white;
        border-radius: 50%;
        width: 2rem;
        height: 2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.9rem;
        flex-shrink: 0;
    }
    .step-title {
        font-size: 1.2rem;
        font-weight: 600;
    }

    /* 이모티콘 카드 */
    .emoji-card {
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 0.8rem;
        text-align: center;
        background: #FAFAFA;
        margin-bottom: 0.5rem;
    }
    .emoji-card:hover {
        border-color: #4F46E5;
        background: #F5F3FF;
    }
    .emoji-name {
        font-weight: 600;
        font-size: 0.85rem;
        margin-top: 0.4rem;
    }
    .emoji-desc {
        color: #6B7280;
        font-size: 0.75rem;
    }
    .emoji-id {
        color: #9CA3AF;
        font-size: 0.7rem;
        font-family: monospace;
    }

    /* Slack 가이드 박스 */
    .slack-guide {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }
    .slack-guide h4 {
        color: #1E40AF;
        margin-bottom: 0.5rem;
    }
    .slack-guide code {
        background: #DBEAFE;
        padding: 0.1rem 0.3rem;
        border-radius: 4px;
        font-size: 0.85rem;
    }

    /* 다운로드 버튼 그리드 */
    .download-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
    }

    /* 구분선 */
    .section-divider {
        border: none;
        border-top: 1px solid #E5E7EB;
        margin: 1.5rem 0;
    }

    /* 미리보기 이미지 */
    img.emoji-preview {
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }

    /* 성공 배지 */
    .success-badge {
        background: #D1FAE5;
        color: #065F46;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────────────────────────────────────

def init_session_state() -> None:
    """Streamlit 세션 상태 초기화"""
    defaults = {
        "face_image": None,          # PIL Image: 배경 제거 + 얼굴 크롭 완료 이미지
        "generated_emojis": {},      # dict[emoji_id, bytes]: 생성된 GIF 바이트
        "generation_done": False,    # 생성 완료 여부
        "last_uploaded_name": None,  # 중복 처리 방지용 업로드 파일명
        "selected_emojis": {},       # dict[emoji_id, bool]: 선택 상태
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────

def image_to_bytes(image: Image.Image, fmt: str = "PNG") -> bytes:
    """PIL Image → bytes 변환"""
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


def render_step_header(step_num: int, title: str) -> None:
    """단계 헤더 렌더링"""
    st.markdown(
        f"""
        <div class="step-header">
            <div class="step-badge">{step_num}</div>
            <div class="step-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_zip_archive(
    emojis: dict[str, bytes],
    username: str = "my",
) -> bytes:
    """
    생성된 GIF를 하나의 ZIP 파일로 묶어 반환.

    Args:
        emojis: {emoji_id: gif_bytes} 딕셔너리
        username: ZIP 파일 내 파일명 prefix (기본 "my")

    Returns:
        ZIP 파일 바이트
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # GIF 파일 추가
        for emoji_id, gif_bytes in emojis.items():
            filename = f"{username}_{emoji_id}.gif"
            zf.writestr(filename, gif_bytes)

        # README.txt 추가
        readme_content = _build_readme_txt(username, list(emojis.keys()))
        zf.writestr("README.txt", readme_content)

    buf.seek(0)
    return buf.getvalue()


def _build_readme_txt(username: str, emoji_ids: list[str]) -> str:
    """Slack 업로드 안내 README.txt 내용 생성"""
    lines = [
        "=" * 60,
        "  Slack 이모티콘 업로드 가이드",
        "=" * 60,
        "",
        "1. Slack 워크스페이스에서 '이모지 추가' 버튼을 클릭하세요.",
        "   (Slack 하단의 이모지 피커 → '이모지 추가')",
        "",
        "2. 각 GIF 파일을 업로드하고 아래 이름으로 등록하세요:",
        "",
    ]

    for emoji_id in emoji_ids:
        slack_name = f"{username}_{emoji_id}"
        lines.append(f"   파일: {username}_{emoji_id}.gif")
        lines.append(f"   이름: :{slack_name}:")
        lines.append("")

    lines += [
        "3. 사용 방법:",
        "   메시지 창에서 :이름: 형식으로 입력하면 이모티콘이 표시됩니다.",
        "",
        "   예시) :my_happy:  :my_spin:  :my_party:",
        "",
        "=" * 60,
        "  Slack Emoji 제약사항",
        "=" * 60,
        "  - 크기: 128 x 128 px",
        "  - 용량: 128 KB 이하",
        "  - 형식: GIF, PNG, JPG",
        "  - 이름: 소문자, 숫자, _, - 만 허용",
        "",
        "Generated by Slack 이모티콘 생성기",
    ]
    return "\n".join(lines)


def get_selected_emoji_configs() -> list[dict]:
    """선택된 이모티콘 설정만 반환"""
    all_configs = get_all_emoji_configs()
    selected = st.session_state.get("selected_emojis", {})
    return [cfg for cfg in all_configs if selected.get(cfg["id"], True)]


# ──────────────────────────────────────────────────────────────────────────────
# UI 섹션: 헤더
# ──────────────────────────────────────────────────────────────────────────────

def render_header() -> None:
    """앱 헤더 렌더링"""
    st.markdown(
        """
        <div class="main-header">
            <h1>😄 Slack 이모티콘 생성기</h1>
            <p>프로필 사진 한 장으로 나만의 움직이는 Slack 이모티콘 세트를 만들어보세요!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# UI 섹션: Step 1 — 사진 업로드
# ──────────────────────────────────────────────────────────────────────────────

def render_upload_section() -> None:
    """Step 1: 사진 업로드 UI"""
    render_step_header(1, "사진 업로드")

    col_upload, col_preview = st.columns([2, 1], gap="large")

    with col_upload:
        uploaded_file = st.file_uploader(
            "얼굴이 잘 보이는 사진을 업로드하세요",
            type=["jpg", "jpeg", "png"],
            help="JPG 또는 PNG 파일 (최대 10MB). 얼굴이 정면을 향한 사진이 가장 좋습니다.",
            key="photo_uploader",
        )

        st.caption(
            "💡 **팁**: 배경이 단순하고 얼굴이 크게 찍힌 사진일수록 품질이 좋습니다."
        )

    with col_preview:
        if uploaded_file is not None:
            _process_uploaded_file(uploaded_file)
        else:
            # 플레이스홀더
            st.markdown(
                """
                <div style="border: 2px dashed #D1D5DB; border-radius: 12px;
                            padding: 2rem; text-align: center; color: #9CA3AF;
                            min-height: 160px; display: flex; align-items: center;
                            justify-content: center; flex-direction: column;">
                    <div style="font-size: 2.5rem;">📷</div>
                    <div style="margin-top: 0.5rem; font-size: 0.9rem;">사진을 업로드하면<br>미리보기가 표시됩니다</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _process_uploaded_file(uploaded_file) -> None:
    """업로드된 파일을 처리하고 미리보기 표시"""
    # 파일 크기 체크
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        st.warning(
            f"파일 크기가 너무 큽니다. {MAX_FILE_SIZE_MB}MB 이하의 파일을 사용해주세요. "
            f"(현재: {uploaded_file.size / 1024 / 1024:.1f}MB)"
        )
        return

    # 새로운 파일이 업로드된 경우에만 재처리
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.last_uploaded_name != file_key:
        st.session_state.last_uploaded_name = file_key
        st.session_state.face_image = None
        st.session_state.generated_emojis = {}
        st.session_state.generation_done = False

        # 얼굴 처리 실행
        _extract_face(uploaded_file)

    # 미리보기 표시
    if st.session_state.face_image is not None:
        st.image(
            st.session_state.face_image,
            caption="감지된 얼굴",
            use_container_width=True,
        )
        st.markdown(
            "<div style='text-align:center'><span class='success-badge'>✓ 얼굴 감지 완료</span></div>",
            unsafe_allow_html=True,
        )
    else:
        # 원본 이미지라도 표시
        try:
            img = Image.open(uploaded_file)
            st.image(img, caption="업로드된 사진", use_container_width=True)
        except Exception:
            pass


def _extract_face(uploaded_file) -> None:
    """배경 제거 + 얼굴 감지 처리"""
    with st.spinner("🔍 얼굴을 감지하는 중..."):
        try:
            # 이미지 로드
            image_bytes = uploaded_file.read()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # 배경 제거
            with st.spinner("✂️ 배경을 제거하는 중... (처음 실행 시 모델 다운로드로 1~2분 소요)"):
                image_no_bg = remove_background(image)

            # 얼굴 감지 + 크롭
            face_image = detect_and_crop_face(image_no_bg)
            st.session_state.face_image = face_image

        except ValueError as e:
            # 얼굴 미감지
            st.warning(
                "얼굴을 찾을 수 없습니다. 다른 사진을 사용해주세요.\n\n"
                "💡 얼굴이 정면을 향하고, 충분히 밝은 환경에서 찍은 사진을 사용하세요."
            )
            logger.warning("얼굴 감지 실패: %s", e)

        except ImportError as e:
            st.error(
                f"필수 라이브러리가 설치되지 않았습니다.\n\n"
                f"`pip install -r requirements.txt` 를 실행해주세요.\n\n"
                f"상세: {e}"
            )
            logger.error("라이브러리 미설치: %s", e)

        except RuntimeError as e:
            st.error(f"배경 제거 중 오류가 발생했습니다: {e}")
            logger.error("배경 제거 오류: %s", e)

        except Exception as e:
            st.error(
                f"사진 처리 중 예상치 못한 오류가 발생했습니다: {e}\n\n"
                "다른 사진으로 다시 시도해주세요."
            )
            logger.exception("처리 중 예외 발생")


# ──────────────────────────────────────────────────────────────────────────────
# UI 섹션: Step 2 — 이모티콘 선택
# ──────────────────────────────────────────────────────────────────────────────

def render_emoji_selection_section() -> None:
    """Step 2: 이모티콘 선택 UI (카테고리 탭 + 체크박스 그리드)"""
    render_step_header(2, "이모티콘 선택")

    # 전체 선택/해제 버튼
    col_all, col_none, col_count = st.columns([1, 1, 3])
    with col_all:
        if st.button("전체 선택", use_container_width=True):
            all_configs = get_all_emoji_configs()
            for cfg in all_configs:
                st.session_state.selected_emojis[cfg["id"]] = True
            st.rerun()
    with col_none:
        if st.button("전체 해제", use_container_width=True):
            all_configs = get_all_emoji_configs()
            for cfg in all_configs:
                st.session_state.selected_emojis[cfg["id"]] = False
            st.rerun()
    with col_count:
        selected_count = sum(
            1 for v in st.session_state.selected_emojis.values() if v
        )
        total_count = len(get_all_emoji_configs())
        st.markdown(
            f"<div style='padding: 0.4rem 0; color: #4B5563;'>"
            f"선택: <strong>{selected_count}</strong> / {total_count}개"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

    # 카테고리 탭
    tab_labels = [CATEGORY_LABELS.get(cat, cat) for cat in CATEGORY_ORDER]
    tabs = st.tabs(tab_labels)

    for tab, category in zip(tabs, CATEGORY_ORDER):
        with tab:
            _render_category_grid(category)


def _render_category_grid(category: str) -> None:
    """카테고리별 이모티콘 체크박스 그리드 렌더링"""
    configs = get_emoji_by_category(category)

    if not configs:
        st.info(f"'{CATEGORY_LABELS.get(category, category)}' 카테고리에 이모티콘이 없습니다.")
        return

    # 기본값: 모두 선택
    for cfg in configs:
        if cfg["id"] not in st.session_state.selected_emojis:
            st.session_state.selected_emojis[cfg["id"]] = True

    # 4열 그리드 렌더링
    cols = st.columns(GRID_COLUMNS)
    for idx, cfg in enumerate(configs):
        col = cols[idx % GRID_COLUMNS]
        with col:
            emoji_id = cfg["id"]
            emoji_name = cfg.get("name", emoji_id)
            emoji_desc = cfg.get("description", "")
            emoji_icon = cfg.get("icon", "😄")

            # 체크박스 상태 관리
            current_state = st.session_state.selected_emojis.get(emoji_id, True)
            new_state = st.checkbox(
                label=f"{emoji_icon} {emoji_name}",
                value=current_state,
                key=f"check_{emoji_id}",
                help=emoji_desc,
            )
            st.session_state.selected_emojis[emoji_id] = new_state

            # 설명 표시
            if emoji_desc:
                st.markdown(
                    f"<div style='color: #9CA3AF; font-size: 0.72rem; "
                    f"margin-top: -0.5rem; margin-bottom: 0.3rem;'>{emoji_desc}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                f"<div style='color: #D1D5DB; font-size: 0.68rem; "
                f"font-family: monospace; margin-bottom: 0.8rem;'>:{emoji_id}:</div>",
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# UI 섹션: Step 3 — 생성
# ──────────────────────────────────────────────────────────────────────────────

def render_generation_section() -> None:
    """Step 3: 이모티콘 생성 UI"""
    render_step_header(3, "이모티콘 생성")

    face_ready = st.session_state.face_image is not None
    selected_configs = get_selected_emoji_configs()
    has_selection = len(selected_configs) > 0

    # 상태 안내
    if not face_ready:
        st.info("Step 1에서 사진을 먼저 업로드해주세요.")
    elif not has_selection:
        st.warning("Step 2에서 생성할 이모티콘을 하나 이상 선택해주세요.")

    # 생성 버튼
    generate_btn = st.button(
        f"🎨 이모티콘 생성하기 ({len(selected_configs)}개)",
        type="primary",
        disabled=not (face_ready and has_selection),
        use_container_width=True,
    )

    if generate_btn:
        _run_generation(selected_configs)

    # 생성 결과 미리보기
    if st.session_state.generation_done and st.session_state.generated_emojis:
        _render_generation_preview()


def _run_generation(selected_configs: list[dict]) -> None:
    """이모티콘 생성 실행"""
    face_image = st.session_state.face_image
    generated: dict[str, bytes] = {}

    progress_bar = st.progress(0, text="생성 준비 중...")
    status_text = st.empty()

    total = len(selected_configs)

    try:
        # 템플릿 엔진 초기화
        engine = TemplateEngine()

        # 템플릿 에셋을 임시 디렉토리에 일괄 생성
        templates_dir = os.path.join(tempfile.gettempdir(), "slack_emoji_templates")
        status_text.markdown("템플릿 에셋 생성 중...")
        generate_all_template_assets(templates_dir)

        for idx, cfg in enumerate(selected_configs):
            emoji_id = cfg["id"]
            emoji_name = cfg.get("name", emoji_id)
            category = cfg["category"]

            status_text.markdown(
                f"생성 중: **{emoji_name}** ({idx + 1}/{total})"
            )

            try:
                # 템플릿 로드
                template_dir = os.path.join(templates_dir, category, emoji_id)
                template = engine.load_template(template_dir)

                # 프레임 렌더링
                frames = engine.render_frames(template, face_image)

                # GIF 생성 (gif_generator가 128x128, 투명도 처리)
                gif_bytes = create_animated_gif(
                    frames=frames,
                    duration_ms=cfg.get("duration_ms", 150),
                    loop=0,
                )

                generated[emoji_id] = gif_bytes

            except Exception as e:
                logger.warning("이모티콘 생성 실패 (%s): %s", emoji_id, e)
                st.warning(f"'{emoji_name}' 생성 중 오류 발생, 건너뜁니다: {e}")

            # 진행률 업데이트
            progress_bar.progress(
                (idx + 1) / total,
                text=f"생성 완료: {idx + 1}/{total}",
            )

        # 완료 처리
        st.session_state.generated_emojis = generated
        st.session_state.generation_done = True

        progress_bar.progress(1.0, text="생성 완료!")
        status_text.empty()

        success_count = len(generated)
        fail_count = total - success_count

        if success_count > 0:
            st.success(
                f"✅ {success_count}개 이모티콘 생성 완료!"
                + (f" ({fail_count}개 실패)" if fail_count > 0 else "")
            )
        else:
            st.error("이모티콘 생성에 모두 실패했습니다. 다시 시도해주세요.")

    except ImportError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(
            f"필수 라이브러리가 없습니다: {e}\n\n"
            "`pip install -r requirements.txt` 를 실행해주세요."
        )

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"생성 중 예상치 못한 오류가 발생했습니다: {e}")
        logger.exception("생성 중 예외 발생")

        if st.button("다시 시도", key="retry_btn"):
            st.session_state.generation_done = False
            st.session_state.generated_emojis = {}
            st.rerun()


def _render_generation_preview() -> None:
    """생성된 이모티콘 GIF 미리보기 그리드"""
    generated = st.session_state.generated_emojis
    if not generated:
        return

    st.markdown(
        "<h4 style='margin-top: 1.2rem; margin-bottom: 0.6rem;'>미리보기</h4>",
        unsafe_allow_html=True,
    )

    emoji_items = list(generated.items())
    all_configs = {cfg["id"]: cfg for cfg in get_all_emoji_configs()}

    cols = st.columns(GRID_COLUMNS)
    for idx, (emoji_id, gif_bytes) in enumerate(emoji_items):
        col = cols[idx % GRID_COLUMNS]
        with col:
            cfg = all_configs.get(emoji_id, {})
            name = cfg.get("name", emoji_id)
            icon = cfg.get("icon", "")

            # GIF 이미지 표시 (애니메이션 재생)
            st.image(
                gif_bytes,
                caption=f"{icon} {name}",
                use_container_width=True,
                output_format="GIF",
            )
            size_kb = len(gif_bytes) / 1024
            st.markdown(
                f"<div style='text-align:center; color: #9CA3AF; font-size: 0.7rem; "
                f"margin-top: -0.5rem;'>{size_kb:.1f} KB</div>",
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# UI 섹션: Step 4 — 다운로드
# ──────────────────────────────────────────────────────────────────────────────

def render_download_section() -> None:
    """Step 4: 다운로드 UI"""
    if not st.session_state.generation_done or not st.session_state.generated_emojis:
        return

    render_step_header(4, "다운로드")

    generated = st.session_state.generated_emojis
    all_configs = {cfg["id"]: cfg for cfg in get_all_emoji_configs()}

    # 사용자명 입력 (파일명 prefix)
    col_name, col_help = st.columns([2, 3])
    with col_name:
        username = st.text_input(
            "이모티콘 이름 prefix",
            value="my",
            placeholder="my",
            help="Slack에 등록할 때 사용할 이름입니다. 소문자, 숫자, _만 사용하세요.",
            key="username_input",
        )
        # 유효성 검사: 소문자/숫자/_ 만 허용
        import re
        if username and not re.match(r'^[a-z0-9_]+$', username):
            st.warning("소문자, 숫자, _ 만 사용 가능합니다.")
            username = re.sub(r'[^a-z0-9_]', '_', username.lower())

    with col_help:
        st.markdown(
            f"<div style='padding: 0.4rem 0; color: #6B7280; font-size: 0.9rem;'>"
            f"예) prefix가 <code>{username or 'my'}</code>이면 → "
            f"<code>:{username or 'my'}_happy:</code>, <code>:{username or 'my'}_spin:</code>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

    # 전체 ZIP 다운로드 버튼 (상단 강조)
    safe_username = username if username else "my"
    zip_bytes = build_zip_archive(generated, username=safe_username)
    zip_filename = f"emoji_set_{safe_username}.zip"

    st.download_button(
        label=f"📦 전체 다운로드 (ZIP) — {len(generated)}개 이모티콘",
        data=zip_bytes,
        file_name=zip_filename,
        mime="application/zip",
        type="primary",
        use_container_width=True,
        key="zip_download_btn",
    )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 개별 다운로드 버튼 그리드
    st.markdown(
        "<h5 style='color: #6B7280; margin-bottom: 0.5rem;'>개별 다운로드</h5>",
        unsafe_allow_html=True,
    )

    emoji_items = list(generated.items())
    cols = st.columns(GRID_COLUMNS)
    for idx, (emoji_id, gif_bytes) in enumerate(emoji_items):
        col = cols[idx % GRID_COLUMNS]
        with col:
            cfg = all_configs.get(emoji_id, {})
            name = cfg.get("name", emoji_id)
            icon = cfg.get("icon", "")
            filename = f"{safe_username}_{emoji_id}.gif"

            st.download_button(
                label=f"{icon} {name}",
                data=gif_bytes,
                file_name=filename,
                mime="image/gif",
                use_container_width=True,
                key=f"dl_{emoji_id}",
                help=f"다운로드: {filename}",
            )

    # Slack 업로드 가이드
    _render_slack_guide(safe_username, list(generated.keys()))


def _render_slack_guide(username: str, emoji_ids: list[str]) -> None:
    """Slack 이모티콘 등록 가이드 렌더링"""
    example_ids = emoji_ids[:3]
    examples = " ".join(f"<code>:{username}_{eid}:</code>" for eid in example_ids)

    st.markdown(
        f"""
        <div class="slack-guide">
            <h4>📘 Slack 이모티콘 등록 방법</h4>
            <ol style="margin: 0; padding-left: 1.2rem; line-height: 1.8;">
                <li>Slack 앱 열기 → 이모지 피커(😊) → <strong>이모지 추가</strong> 클릭</li>
                <li>ZIP 파일 내 각 GIF 파일을 업로드</li>
                <li>이름 형식: <code>{username}_이모티콘ID</code> 로 등록</li>
                <li>메시지에서 <code>:{username}_happy:</code> 형식으로 사용</li>
            </ol>
            <div style="margin-top: 0.8rem;">
                예시: {examples}
            </div>
            <div style="margin-top: 0.6rem; font-size: 0.8rem; color: #3B82F6;">
                ⚠️ Slack 제약: 128×128px, 128KB 이하, 소문자·숫자·_·- 만 허용
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 메인 앱 진입점
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Streamlit 앱 메인 함수"""
    init_session_state()

    render_header()

    # Step 1: 사진 업로드
    render_upload_section()

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # Step 2: 이모티콘 선택 (사진 업로드 전에도 접근 가능)
    render_emoji_selection_section()

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # Step 3: 생성
    render_generation_section()

    # Step 4: 다운로드 (생성 완료 후 자동 표시)
    if st.session_state.generation_done and st.session_state.generated_emojis:
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        render_download_section()

    # 푸터
    st.markdown(
        """
        <div style="text-align: center; color: #D1D5DB; font-size: 0.75rem;
                    padding: 2rem 0 1rem 0; margin-top: 2rem;">
            Slack 이모티콘 생성기 — Powered by rembg · mediapipe · Pillow · Streamlit
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
