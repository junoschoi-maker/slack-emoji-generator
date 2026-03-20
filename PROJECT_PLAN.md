# Slack 이모티콘 생성기 (Slack Emoji Generator)

## 프로젝트 개요

프로필 사진 한 장을 업로드하면, 사전 제작된 템플릿에 얼굴을 합성하여
**움직이는 GIF 이모티콘 세트**를 자동 생성하는 도구.

생성된 이모티콘을 Slack에 등록하여 팀원들이 소통에 활용한다.

### 레퍼런스
- [makeemoji.com](https://makeemoji.com/) — 사진 업로드 → 애니메이션 효과 적용 → GIF 이모티콘 생성

---

## 핵심 플로우

```
사진 업로드 (Web UI)
    ↓
배경 제거 (rembg)
    ↓
얼굴 감지 + 크롭 (mediapipe / face_recognition)
    ↓
템플릿 합성 엔진 (Pillow)
├─ 감정 템플릿 (기쁨/슬픔/화남/놀람...)
├─ 업무 템플릿 (퇴근/야근/회의중/배포...)
├─ 개그 템플릿 (불타는눈/파티/스핀...)
└─ 리액션 템플릿 (OK/NO/박수...)
    ↓
애니메이션 GIF 생성 (2~4프레임, 심플)
    ↓
GIF 최적화 (128x128px, <128KB)
    ↓
ZIP 다운로드 / 미리보기
```

---

## 기술 아키텍처

### 기술 스택

| 레이어 | 기술 | 용도 |
|---|---|---|
| **Web UI** | Streamlit | 사진 업로드, 미리보기, 다운로드 |
| **이미지 처리** | Pillow (PIL) | 이미지 합성, GIF 생성 |
| **배경 제거** | rembg | 사진 배경 자동 제거 |
| **얼굴 감지** | mediapipe | 얼굴 위치/크기 감지, 랜드마크 |
| **GIF 최적화** | gifsicle (optional) | 128KB 이하로 압축 |
| **패키지 관리** | pip + requirements.txt | 의존성 관리 |
| **실행 환경** | 로컬 (Python 3.11+) | 개인 PC |

### 디렉토리 구조

```
slack_con_generator/
├── PROJECT_PLAN.md          # 이 문서
├── CLAUDE.md                # Claude Code 프로젝트 지침
├── requirements.txt         # Python 의존성
├── .env.example             # 환경변수 템플릿
├── .gitignore
│
├── app.py                   # Streamlit 메인 앱
├── core/
│   ├── __init__.py
│   ├── face_detector.py     # 얼굴 감지 + 크롭
│   ├── background_remover.py # 배경 제거
│   ├── template_engine.py   # 템플릿 합성 엔진
│   ├── gif_generator.py     # GIF 생성 + 최적화
│   └── emoji_set.py         # 이모티콘 세트 정의
│
├── templates/               # 템플릿 에셋
│   ├── template_schema.json # 템플릿 메타데이터 스키마
│   ├── emotions/            # 감정 템플릿
│   │   ├── happy/
│   │   │   ├── frame_01.png
│   │   │   ├── frame_02.png
│   │   │   └── config.json  # 얼굴 위치, 크기, 애니메이션 설정
│   │   ├── sad/
│   │   ├── angry/
│   │   └── ...
│   ├── work/                # 업무 상황 템플릿
│   ├── funny/               # 개그 템플릿
│   └── reaction/            # 리액션 템플릿
│
├── output/                  # 생성된 이모티콘 출력
│   └── .gitkeep
│
└── tests/
    ├── test_face_detector.py
    ├── test_template_engine.py
    └── test_gif_generator.py
```

---

## 이모티콘 세트 구성 (v1.0 — 24개)

### 감정 (6개)
| ID | 이름 | 애니메이션 | 설명 |
|---|---|---|---|
| happy | 기쁨 | 바운스 ↕ | 위아래로 통통 |
| sad | 슬픔 | 좌우 흔들기 | 고개 좌우로 |
| angry | 화남 | 떨림(진동) | 부들부들 |
| surprised | 놀람 | 확대→원래 | 깜짝! |
| love | 하트 | 하트 이펙트 | 주변에 하트 날림 |
| laugh | 웃음 | 바운스 + 눈물 | 빵 터짐 |

### 업무 상황 (7개)
| ID | 이름 | 애니메이션 | 설명 |
|---|---|---|---|
| goHome | 퇴근 | 달리기 → 사라짐 | 문 밖으로 |
| overtime | 야근 | 느린 떨림 | 모니터 앞 좀비 |
| meeting | 회의중 | 고개 끄덕 | zzz 이펙트 |
| deploy | 배포 | 로켓 이펙트 | 🚀 발사 |
| bug | 버그 | 깜빡임 | 벌레 이펙트 |
| lgtm | LGTM | 엄지척 | 반짝 이펙트 |
| coffee | 커피타임 | 김 모락모락 | 커피잔 + 얼굴 |

### 개그/밈 (6개)
| ID | 이름 | 애니메이션 | 설명 |
|---|---|---|---|
| fire | 불타는 눈 | 불꽃 이펙트 | 눈에서 불 |
| party | 파티 | 컨페티 날림 | 축하 |
| spin | 스핀 | 360도 회전 | 빙글빙글 |
| rainbow | 무지개 | 색상 변환 | 무지개빛 |
| thug | 선글라스 | 위에서 내려옴 | deal with it |
| cockroach | 바퀴벌레 | 기어다니기 | 얼굴 합성된 바퀴벌레 (버그 용도) |
| rip | RIP | 페이드아웃 | 서서히 사라짐 |

### 리액션 (5개)
| ID | 이름 | 애니메이션 | 설명 |
|---|---|---|---|
| ok | OK | 엄지 바운스 | 확인 |
| no | NO | 좌우 흔들기 | 거절 |
| question | 물음표 | 물음표 팝업 | ? 이펙트 |
| exclaim | 느낌표 | 느낌표 팝업 | ! 이펙트 |
| clap | 박수 | 손뼉 이펙트 | 짝짝짝 |

---

## 템플릿 시스템

### 템플릿 구조 (config.json)

```json
{
  "id": "happy",
  "name": "기쁨",
  "category": "emotions",
  "frames": 3,
  "animation": {
    "type": "bounce",
    "duration_ms": 500,
    "loop": true
  },
  "face_placement": [
    {"frame": 1, "x": 32, "y": 20, "width": 64, "height": 64, "rotation": 0},
    {"frame": 2, "x": 32, "y": 14, "width": 64, "height": 64, "rotation": 0},
    {"frame": 3, "x": 32, "y": 20, "width": 64, "height": 64, "rotation": 0}
  ],
  "layers": [
    {"type": "background", "file": "bg.png"},
    {"type": "face", "order": 1},
    {"type": "overlay", "file": "effect.png", "order": 2}
  ],
  "output_size": [128, 128]
}
```

### 에셋 소싱 전략

1. **1차: 오픈소스 에셋** — OpenMoji, Twemoji 등에서 장식/이펙트 소스 확보
2. **2차: 코드 생성** — Pillow로 기하학적 이펙트 직접 그리기 (하트, 별, 불꽃 등)
3. **3차: AI 보조** — 부족한 특수 에셋은 DALL-E/Stable Diffusion으로 생성

---

## Agent Teams 구성

### 역할 분담

```
┌──────────────────────────────────────────┐
│          Orchestrator (Opus)              │
│  기획/설계/코드리뷰/통합/품질관리           │
└────────┬────────┬────────┬───────────────┘
         │        │        │
    ┌────▼──┐ ┌──▼────┐ ┌▼──────────┐
    │Agent 1│ │Agent 2│ │Agent 3    │
    │Core   │ │Tmpl   │ │Web UI     │
    │Engine │ │System │ │& Output   │
    │Sonnet │ │Sonnet │ │Sonnet     │
    └───────┘ └───────┘ └───────────┘
```

### Agent 1: Core Engine (Sonnet)
**담당 파일**: `core/face_detector.py`, `core/background_remover.py`, `core/gif_generator.py`

- 배경 제거 (rembg 래핑)
- 얼굴 감지 + 크롭 (mediapipe)
- GIF 합성 + 최적화 (Pillow, 128x128, <128KB)
- 단위 테스트

### Agent 2: Template System (Sonnet)
**담당 파일**: `core/template_engine.py`, `core/emoji_set.py`, `templates/`

- 템플릿 스키마 정의 (config.json 구조)
- 템플릿 합성 로직 (레이어 순서대로 합성)
- 프레임별 얼굴 배치 로직
- 초기 템플릿 에셋 (코드로 생성 가능한 심플 에셋부터)
- 단위 테스트

### Agent 3: Web UI & Output (Sonnet)
**담당 파일**: `app.py`, `output/`

- Streamlit 앱 (업로드 → 미리보기 → 다운로드)
- 이모티콘 세트 선택 UI
- GIF 미리보기 그리드
- ZIP 다운로드 기능
- Slack 이모티콘 네이밍 가이드 (`:이름_happy:` 형식)

### Orchestrator (Opus) — 나
- 전체 설계 및 인터페이스 정의
- Agent 간 의존성 관리
- 코드리뷰 및 통합
- 품질 검증 (Slack 사이즈 제약 충족 여부)

---

## 구현 로드맵

### Phase 1: MVP (Core + 3개 템플릿)
1. Core Engine 구현 (배경 제거, 얼굴 감지, GIF 생성)
2. 템플릿 시스템 구현 (스키마 + 합성 엔진)
3. 심플 템플릿 3개 제작 (happy, sad, spin — 코드 기반 에셋)
4. Streamlit 기본 UI
5. End-to-end 테스트

### Phase 2: 풀 세트 (24개 템플릿)
6. 오픈소스 에셋 수집 + 가공
7. 전체 24개 템플릿 제작
8. GIF 품질 최적화 튜닝
9. UI 개선 (카테고리별 필터, 미리보기 개선)

### Phase 3: Slack 통합 (선택)
10. Slack App 개발 (Bot + Slash Command)
11. 이모티콘 자동 등록 API 연동
12. 팀 배포

---

## Slack 이모티콘 제약사항

| 항목 | 제약 |
|---|---|
| 포맷 | GIF, PNG, JPG |
| 크기 | 128x128px (권장) |
| 용량 | 128KB 이하 |
| 네이밍 | 소문자, 숫자, _, - 만 허용 |
| 애니메이션 | GIF 지원, 자동 재생 |

---

## 실행 방법 (목표)

```bash
# 설치
pip install -r requirements.txt

# 실행
streamlit run app.py

# 브라우저에서 사진 업로드 → 이모티콘 세트 생성 → ZIP 다운로드
```
