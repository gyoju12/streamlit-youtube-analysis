# YouTube 인기 동영상 Streamlit 앱

간단한 한 페이지 Streamlit 앱으로, YouTube Data API v3를 사용해 지역별/카테고리별 인기 동영상 Top N(기본 30)을 보여줍니다. 썸네일, 제목(YouTube 링크), 채널명, 조회수는 물론 좋아요 수, 댓글 수, 채널 구독자 수까지 제공합니다. 사이드바에서 지역 코드, 카테고리, 표시 개수를 조절할 수 있으며, 새로고침 버튼으로 캐시를 비우고 최신 데이터를 불러올 수 있습니다.

## 주요 기능
- 지역별 인기 동영상 조회 (KR/US/JP 등, 직접 입력 가능)
- 카테고리별 인기 동영상 조회 (기본값: 전체)
- 표시 개수 조절 (1~50개)
- 썸네일, 제목(클릭 시 YouTube로 이동), 채널명, 조회수 표기(한국어 단위: 만/억)
- 좋아요 수, 댓글 수 표시
- 채널 구독자 수 표시 (추가 API 호출 포함)
- 새로고침 버튼으로 데이터 캐시 초기화 후 재조회
- 에러 처리: 환경 설정 오류, 네트워크/타임아웃, API 오류(쿼터, 파라미터) 등 안내
- 임시 로그인 지원: 로그인 후 콘텐츠 접근(기본 계정 제공)

## 기술 스택
- Streamlit
- YouTube Data API v3
- requests, python-dotenv

## 디렉터리 구조
```
html_css_vibe/
├─ streamlit_app.py        # 메인 앱
├─ requirements.txt        # 의존성
├─ .env.example            # 환경변수 예시 (실제 키 없음)
├─ .env                    # 실제 환경변수(로컬, Git 추적 제외 권장)
└─ README.md               # 이 문서
```

## 사전 준비
1. Google Cloud Console에서 프로젝트 생성 후 "YouTube Data API v3" 활성화
2. API 키 발급 및 `.env` 파일에 설정

`.env` 파일 예시:
```dotenv
YOUTUBE_API_KEY=YOUR_YOUTUBE_DATA_API_KEY_HERE
```

주의: `.env`는 민감정보를 포함하므로 Git에 커밋하지 않는 것을 권장합니다.

## 설치 및 실행
1) 의존성 설치
```bash
pip install -r requirements.txt
```

2) 앱 실행
```bash
streamlit run streamlit_app.py
```

브라우저가 자동으로 열립니다. 사이드바에서 아래를 설정할 수 있습니다.
- 지역 코드: 기본 `KR`, 드롭다운 또는 직접 입력 가능
- 카테고리: 기본 `전체` (YouTube videoCategories.list 기반)
- 표시 개수: 1~50개 (기본 30)
- 새로고침: 캐시 초기화 후 재조회

데이터는 기본적으로 5분(ttl=300초) 동안 캐시됩니다.

## 배포 가이드 (Streamlit Cloud)
본 프로젝트는 배포 환경에서 API 키를 `st.secrets`로 우선 조회하고, 없을 경우 환경변수(`.env`)를 사용합니다.

우선순위: `st.secrets` → 환경변수(`.env`)

1) 비밀키 설정
- Streamlit Cloud 대시보드에서 앱 선택 → `Settings` → `Secrets`에 아래 중 하나의 형식으로 등록하세요.
  - 평면 구조
    ```toml
    YOUTUBE_API_KEY = "YOUR_YOUTUBE_DATA_API_KEY_HERE"
    ```
  - 중첩 구조
    ```toml
    [youtube]
    api_key = "YOUR_YOUTUBE_DATA_API_KEY_HERE"
    ```
- 로컬 개발 시에는 `html_css_vibe/.streamlit/secrets.toml`를 생성해 위 내용을 넣고 사용하세요. 예시는 `/.streamlit/secrets.toml.example`를 참고하세요.

2) 코드 변경 없이 배포
- 리포지터리를 Streamlit Cloud에 연결한 뒤, 메인 파일을 `html_css_vibe/streamlit_app.py`로 지정하면 됩니다.

3) 보안 유의사항
- `.env` 및 `.streamlit/secrets.toml`에는 민감정보가 포함되므로 절대 커밋하지 마세요.
- 이미 키가 노출되었을 가능성이 있다면, Google Cloud Console에서 즉시 키를 재발급(rotate)하고 노출된 키는 폐기하세요.

## 로그인 사용 방법(임시)
앱은 임시 계정 기반 로그인을 사용합니다. 로그인 후에 메인 콘텐츠가 표시됩니다.

- 기본 계정
  - 아이디: `admin12`
  - 비밀번호: `admin12!@`
- 환경변수로 오버라이드 가능
  - `TEMP_USERNAME`
  - `TEMP_PASSWORD`
  - 예시(.env):
    ```dotenv
    TEMP_USERNAME=admin12
    TEMP_PASSWORD=admin12!@
    ```

## 설정 변경(선택)
- 지역 코드와 표시 개수는 사이드바에서 변경 가능합니다(코드 수정 불필요).
- 필요 시 기본값을 바꾸려면 `streamlit_app.py`의 사이드바 위젯 초기값을 조정하세요.

## 트러블슈팅
- 403/`quotaExceeded`: API 사용량 초과 또는 API 미활성화. 콘솔의 쿼터 상태 및 API 활성화 확인.
- 400/`invalidParameter`: `part`, `chart`, `regionCode`, `maxResults` 등의 파라미터 확인.
- 네트워크/타임아웃: 네트워크 연결 확인 후 재시도.
- 환경변수 누락: `.env`의 `YOUTUBE_API_KEY` 설정 확인.
- 구독자 수 미표시: `channels.list` 호출이 실패한 경우 일부 채널의 구독자 수가 표시되지 않을 수 있습니다(치명적 오류는 아님).
- 카테고리 목록 비어있음: `videoCategories.list` 호출 실패 시 전체(기본)로 조회됩니다.

## 개발 가이드
- 코드 구조는 단일 페이지 앱으로 단순화를 유지합니다.
- 조회수 포맷은 한국어 표기를 기준으로 `만/억` 단위를 사용합니다.
- 썸네일은 `maxres → standard → high → medium → default` 우선순위로 선택합니다.
- 캐싱은 `st.cache_data`를 사용하며, 새로고침 버튼 클릭 시 캐시를 초기화합니다. 채널 구독자 수 조회도 캐시됩니다.

## 작업 내역(Changelog) 및 계획
아래 표 또는 체크리스트를 사용해 작업을 관리하세요.

### 변경 로그 템플릿
| 날짜(YYYY-MM-DD) | 버전 | 변경 내용 | 작성자 |
|---|---|---|---|
| 2025-09-17 | 0.3.0 | 카테고리 선택 추가(기본 전체), README 갱신 | |
| 2025-09-17 | 0.2.0 | 지역 코드/표시 개수 UI 추가, 좋아요/댓글/구독자 수 표시, README 갱신 | |
| 2025-09-17 | 0.1.0 | 초기 프로젝트 생성: Streamlit 앱, 의존성, .env 예시, README 추가 | |

### 작업 체크리스트(예시)
- [x] 기본 앱 구조 구성 (Top 30, 썸네일/제목/채널/조회수)
- [x] 새로고침 버튼 및 캐시 초기화
- [x] 에러 처리(환경, 네트워크, API)
- [x] 지역/개수 UI 옵션화
- [x] 좋아요/댓글 수 표시
- [x] 채널 구독자 수 표시
- [x] 카테고리 선택 추가
- [ ] 무한 스크롤 또는 페이지네이션 (선택)
- [ ] 검색/필터 기능 (선택)
- [ ] 테스트 추가 및 린트 설정 (선택)

## 참고 자료
- YouTube Data API v3 문서: https://developers.google.com/youtube/v3/docs?hl=ko
- Streamlit 문서: https://docs.streamlit.io/
