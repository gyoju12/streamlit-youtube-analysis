import os
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Tuple

# 환경변수(.env) 로드
load_dotenv()

API_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"
CATEGORIES_ENDPOINT = "https://www.googleapis.com/youtube/v3/videoCategories"

# 지역 코드 → 지역명(한국어) 매핑
REGION_NAMES: Dict[str, str] = {
    "KR": "대한민국",
    "US": "미국",
    "JP": "일본",
    "GB": "영국",
    "DE": "독일",
    "FR": "프랑스",
    "IN": "인도",
    "ID": "인도네시아",
    "VN": "베트남",
    "TW": "대만",
    "TH": "태국",
    "PH": "필리핀",
    "CA": "캐나다",
    "AU": "호주",
    "BR": "브라질",
    "RU": "러시아",
    "TR": "튀르키예",
    "UA": "우크라이나",
    "SA": "사우디아라비아",
    "AE": "아랍에미리트",
}


def get_api_key() -> str:
    """배포 환경(Streamlit Cloud)과 로컬 환경 모두 대응하여 API 키를 조회합니다.
    우선순위: st.secrets → 환경변수(.env)
    예외: 키가 없으면 ValueError 발생
    """
    # 1) Streamlit Cloud / 로컬 secrets.toml
    try:
        if hasattr(st, "secrets") and st.secrets:
            if "YOUTUBE_API_KEY" in st.secrets:
                val = str(st.secrets["YOUTUBE_API_KEY"]).strip()
                if val:
                    return val
            # 선택: 중첩 구조 지원 (youtube.api_key)
            if "youtube" in st.secrets and isinstance(st.secrets["youtube"], dict):
                nested = st.secrets["youtube"].get("api_key")
                if nested:
                    return str(nested).strip()
    except Exception:
        # secrets 접근 에러 시 환경변수로 폴백
        pass

    # 2) 환경변수(.env)
    val = os.getenv("YOUTUBE_API_KEY", "").strip()
    if val:
        return val

    raise ValueError(
        "API 키가 설정되지 않았습니다. Streamlit Secrets 또는 .env의 YOUTUBE_API_KEY를 설정하세요."
    )


def humanize_count(count_str: str) -> str:
    """숫자(조회수/좋아요/댓글/구독자 등)를 한국어 기준으로 보기 좋게 포맷팅.
    단위(회/개/명)는 붙이지 않습니다.
    """
    try:
        n = int(count_str)
    except Exception:
        return count_str

    if n >= 1_0000_0000:  # 1억 이상
        return f"{n/1_0000_0000:.1f}억"
    if n >= 10_000:  # 1만 이상
        return f"{n/10_000:.1f}만"
    return f"{n:,}"


def _ensure_session_keys():
    for k, v in {
        "oauth_state": None,
        "code_verifier": None,
        "user": None,
        "access_token": None,
        "id_token": None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

def render_auth_sidebar() -> bool:
    """사이드바에 임시 로그인/로그아웃 UI를 렌더링하고, 로그인 여부를 반환합니다.
    자격 증명은 st.secrets 또는 환경변수(TEMP_USERNAME, TEMP_PASSWORD)에서만 읽습니다.
    코드에 하드코딩된 기본값은 없습니다.
    """
    _ensure_session_keys()
    st.sidebar.subheader("인증")

    # 이미 로그인된 경우
    if st.session_state.get("user"):
        user = st.session_state["user"]
        st.sidebar.success(f"로그인: {user.get('name', user.get('username', 'user'))}")
        if st.sidebar.button("로그아웃"):
            for k in ["user", "access_token", "id_token", "oauth_state", "code_verifier"]:
                st.session_state[k] = None
            st.rerun()
        return True

    # 로그인 폼
    with st.sidebar.form("login_form", clear_on_submit=False):
        username = st.text_input("아이디", value="")
        password = st.text_input("비밀번호", type="password", value="")
        submitted = st.form_submit_button("로그인")

    if submitted:
        # st.secrets 우선, env 폴백
        expected_user = None
        expected_pass = None
        try:
            if hasattr(st, "secrets") and st.secrets:
                expected_user = st.secrets.get("TEMP_USERNAME", expected_user)
                expected_pass = st.secrets.get("TEMP_PASSWORD", expected_pass)
        except Exception:
            pass
        if expected_user is None:
            expected_user = os.getenv("TEMP_USERNAME")
        if expected_pass is None:
            expected_pass = os.getenv("TEMP_PASSWORD")

        if not expected_user or not expected_pass:
            st.sidebar.warning("로그인 자격 증명이 설정되지 않았습니다. TEMP_USERNAME/PASSWORD를 secrets 또는 .env에 설정하세요.")
            return False
        if username == expected_user and password == expected_pass:
            st.session_state["user"] = {"username": username, "name": "관리자"}
            st.success("로그인 성공")
            st.rerun()
        else:
            st.sidebar.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    return bool(st.session_state.get("user"))


def fetch_popular_videos(
    api_key: str,
    max_results: int = 30,
    region_code: str = "KR",
    video_category_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """YouTube Data API로 인기 동영상 목록을 가져옵니다.

    반환: 동영상 아이템 리스트 (snippet, statistics 포함)
    예외: 요청/API 오류 시 Exception 발생
    """
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "maxResults": max_results,
        "regionCode": region_code,
        "key": api_key,
    }
    if video_category_id and video_category_id != "0":
        params["videoCategoryId"] = video_category_id
    resp = requests.get(API_ENDPOINT, params=params, timeout=15)
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = {"message": resp.text[:200]}
        raise RuntimeError(f"YouTube API 오류 (status={resp.status_code}): {detail}")

    data = resp.json()
    if "items" not in data:
        raise RuntimeError("API 응답에 items가 없습니다. 쿼리 파라미터를 확인하세요.")

    return data["items"]


@st.cache_data(ttl=300, show_spinner=False)
def get_videos_cached(
    api_key: str, max_results: int, region_code: str, video_category_id: str
) -> List[Dict[str, Any]]:
    return fetch_popular_videos(
        api_key, max_results=max_results, region_code=region_code, video_category_id=video_category_id
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_categories_cached(api_key: str, region_code: str) -> List[Dict[str, str]]:
    """지역 코드 기준 카테고리 목록을 가져옵니다. 반환: [{id, title}] (assignable만).
    """
    params = {
        "part": "snippet",
        "regionCode": region_code,
        "key": api_key,
    }
    resp = requests.get(CATEGORIES_ENDPOINT, params=params, timeout=15)
    if resp.status_code != 200:
        return []
    data = resp.json()
    items = []
    for it in data.get("items", []):
        if not it.get("snippet", {}).get("assignable", False):
            continue
        cid = it.get("id")
        title = it.get("snippet", {}).get("title")
        if cid and title:
            items.append({"id": cid, "title": title})
    return items


@st.cache_data(ttl=300, show_spinner=False)
def get_subscribers_cached(api_key: str, channel_ids: Tuple[str, ...]) -> Dict[str, str]:
    """channels.list를 호출하여 채널 구독자 수를 가져옵니다. 반환: {channelId: subscriberCount}.
    최대 50개까지 한 번에 요청합니다.
    """
    result: Dict[str, str] = {}
    if not channel_ids:
        return result

    # YouTube API는 id 파라미터에 최대 50개 채널ID를 지원
    ids = list(dict.fromkeys([cid for cid in channel_ids if cid]))  # 순서 유지 + 중복 제거
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        params = {
            "part": "statistics",
            "id": ",".join(batch),
            "key": api_key,
            "maxResults": 50,
        }
        resp = requests.get(CHANNELS_ENDPOINT, params=params, timeout=15)
        if resp.status_code != 200:
            # 채널 정보 실패는 치명적이지 않으므로 continue 처리
            continue
        data = resp.json()
        for ch in data.get("items", []):
            ch_id = ch.get("id", "")
            stats = ch.get("statistics", {})
            subs = stats.get("subscriberCount")
            if ch_id and subs is not None:
                result[ch_id] = subs
    return result


def render_video_item(item: Dict[str, Any], subscribers: Dict[str, str]) -> None:
    """썸네일, 제목(링크), 채널명(+구독자), 조회수/좋아요/댓글을 두 컬럼으로 표시"""
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})

    title = snippet.get("title", "(제목 없음)")
    channel = snippet.get("channelTitle", "(채널 정보 없음)")
    channel_id = snippet.get("channelId", "")
    video_id = item.get("id", "")
    url = f"https://www.youtube.com/watch?v={video_id}" if video_id else "#"

    # 썸네일: 고화질 우선 선택
    thumbs = snippet.get("thumbnails", {})
    thumb_url: Optional[str] = None
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbs and "url" in thumbs[key]:
            thumb_url = thumbs[key]["url"]
            break

    view_count_fmt = humanize_count(statistics.get("viewCount", "0"))
    like_count_fmt = humanize_count(statistics.get("likeCount", "0"))
    comment_count_fmt = humanize_count(statistics.get("commentCount", "0"))
    subs_fmt = humanize_count(subscribers.get(channel_id, "0")) if channel_id in subscribers else "알수없음"

    col_img, col_meta = st.columns([1, 3], gap="small")
    with col_img:
        if thumb_url:
            st.image(thumb_url, use_container_width=True)
        else:
            st.write("(썸네일 없음)")

    with col_meta:
        st.markdown(f"**[{title}]({url})**")
        st.caption(f"채널: {channel} | 구독자: {subs_fmt if subs_fmt=='알수없음' else subs_fmt + '명'}")
        st.write(
            f"조회수: {view_count_fmt}회 · 좋아요: {like_count_fmt}개 · 댓글: {comment_count_fmt}개"
        )


def main() -> None:
    st.set_page_config(page_title="인기 YouTube 동영상", page_icon="📺", layout="wide")
    st.title("📺 YouTube 인기 동영상")
    st.caption("지역 선택 가능 | 표시 개수 조절 | 5분 캐시 | 새로고침으로 최신화")

    # 사이드바: 인증 섹션 (임시 로그인)
    is_authed = render_auth_sidebar()

    # 사이드바 컨트롤
    st.sidebar.header("옵션")
    common_regions = [
        "KR", "US", "JP", "GB", "DE", "FR", "IN", "ID", "VN", "TW",
        "TH", "PH", "CA", "AU", "BR", "RU", "TR", "UA", "SA", "AE",
    ]
    region_options = [("직접 입력", "__CUSTOM__")] + [
        (f"{REGION_NAMES.get(code, code)} ({code})", code) for code in common_regions
    ]
    region_labels = [label for label, _ in region_options]
    default_index = 1 + common_regions.index("KR")  # "대한민국 (KR)" 기본 선택
    selected_label = st.sidebar.selectbox("지역 선택", options=region_labels, index=default_index)
    selected_value = dict(region_options)[selected_label]
    if selected_value == "__CUSTOM__":
        region_code = st.sidebar.text_input("지역 코드 직접 입력 (예: KR)", value="KR").strip().upper()
    else:
        region_code = selected_value

    max_results = st.sidebar.slider("표시 개수", min_value=1, max_value=50, value=30, step=1)

    # 카테고리 목록 불러오기 및 선택
    categories = get_categories_cached(get_api_key(), region_code)
    category_options = [("전체", "0")] + [(c["title"], c["id"]) for c in categories]
    cat_labels = [label for label, _ in category_options]
    cat_index = 0  # 기본 전체
    selected_label = st.sidebar.selectbox("카테고리", options=cat_labels, index=cat_index)
    selected_category_id = dict(category_options)[selected_label]
    refresh = st.sidebar.button("🔄 새로고침", help="캐시를 비우고 최신 데이터를 가져옵니다.")

    try:
        api_key = get_api_key()
        if not is_authed:
            st.info("로그인 후 인기 동영상을 확인할 수 있습니다.")
            return
        if refresh:
            # 캐시 초기화 (동영상/채널 구독자 모두)
            get_videos_cached.clear()
            get_subscribers_cached.clear()
            get_categories_cached.clear()
        with st.spinner("인기 동영상을 불러오는 중..."):
            items = get_videos_cached(
                api_key, max_results=max_results, region_code=region_code, video_category_id=selected_category_id
            )

        if not items:
            st.info("표시할 동영상이 없습니다.")
            return

        # 채널 구독자 수 조회 (캐시 활용)
        channel_ids = tuple(
            [it.get("snippet", {}).get("channelId", "") for it in items]
        )
        subscribers = get_subscribers_cached(api_key, channel_ids)

        st.caption(f"지역: {region_code} | 카테고리: {selected_label} | 표시 개수: {len(items)}")

        # 리스트 렌더링
        for idx, item in enumerate(items, start=1):
            render_video_item(item, subscribers)
            if idx < len(items):
                st.divider()

    except ValueError as ve:
        st.error(f"설정 오류: {ve}")
        st.stop()
    except requests.Timeout:
        st.error("요청이 시간 초과되었습니다. 네트워크 상태를 확인하고 다시 시도하세요.")
    except requests.RequestException as re:
        st.error(f"네트워크 오류가 발생했습니다: {re}")
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
