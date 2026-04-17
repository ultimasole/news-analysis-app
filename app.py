import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import re

# 1. 페이지 설정
st.set_page_config(page_title="AI PR Monitor", page_icon="📈", layout="centered")

# CSS 고도화 (카드 디자인 및 필터 버튼 스타일)
st.markdown("""
    <style>
    .news-card { padding: 24px; border-radius: 12px; background-color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border: 1px solid #f0f2f6; }
    .sentiment-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 10px; }
    .pos { background-color: #e6f4ea; color: #1e8e3e; }
    .neg { background-color: #fce8e6; color: #d93025; }
    .neu { background-color: #f1f3f4; color: #5f6368; }
    .section-label { font-size: 0.8em; font-weight: bold; color: #007BFF; text-transform: uppercase; margin-bottom: 5px; }
    .content-text { font-size: 1.1em; color: #1a1a1a; margin-bottom: 15px; line-height: 1.4; }
    .reason-box { padding: 15px; border-radius: 8px; font-size: 0.95em; line-height: 1.5; border-left: 5px solid #dee2e6; background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Groq API Key", type="password")
    lang_options = {
        "한국어 (KR)": {"lang": "ko", "country": "KR"},
        "영어 (US)": {"lang": "en", "country": "US"},
        "일본어 (JP)": {"lang": "ja", "country": "JP"}
    }
    selected_lang = st.selectbox("검색 국가/언어", list(lang_options.keys()))
    config = lang_options[selected_lang]
    max_results = st.slider("분석 기사 개수", 5, 50, 20)

# 3. 메인 화면 및 검색
st.title("🌐 실시간 뉴스 감성 분석")

col_search, col_time = st.columns([3, 1])
with col_search:
    keyword = st.text_input("분석 키워드", value='"현대카드"')
with col_time:
    period = st.selectbox("기간", ["1d", "7d", "30d"], index=1)

# 세션 상태 초기화 (결과 저장용)
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []
if 'filter_emotion' not in st.session_state:
    st.session_state.filter_emotion = "전체"

# 유틸리티 함수
def clean_summary(html_text, title):
    clean = re.sub('<[^<]+?>', '', html_text)
    if title in clean: clean = clean.replace(title, "").strip()
    return clean if clean else "요약 내용 없음"

def analyze_sentiment(title, snippet, client):
    prompt = f"경제 전문가로서 다음 뉴스를 분석해 [긍정], [부정], [중립] 중 하나로 분류하고 그 이유를 설명하세요.\n\n제목: {title}\n요약: {snippet}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return "[중립] 분석 실패"

# 4. 분석 실행 버튼
if st.button("🚀 뉴스 분석 및 통계 산출", use_container_width=True):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    else:
        with st.spinner("데이터를 분석 중입니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            articles = search['entries'][:max_results]
            temp_results = []
            
            for i, entry in enumerate(articles):
                title = entry.title
                summary = clean_summary(entry.summary, title)
                analysis = analyze_sentiment(title, summary, client)
                
                emotion = "중립"
                if "[긍정]" in analysis: emotion = "긍정"
                elif "[부정]" in analysis: emotion = "부정"
                
                temp_results.append({
                    "title": title,
                    "summary": summary,
                    "analysis_text": analysis.split(']')[-1].strip() if ']' in analysis else analysis,
                    "emotion": emotion,
                    "published": entry.published,
                    "source": entry.source.title,
                    "link": entry.link
                })
            st.session_state.analysis_results = temp_results
            st.session_state.filter_emotion = "전체"

# 5. 통계 대시보드 및 필터 버튼
if st.session_state.analysis_results:
    res_df = pd.DataFrame(st.session_state.analysis_results)
    total = len(res_df)
    pos_n = len(res_df[res_df['emotion'] == '긍정'])
    neg_n = len(res_df[res_df['emotion'] == '부정'])
    neu_n = len(res_df[res_df['emotion'] == '중립'])

    st.subheader("📈 감성 통계 (클릭하여 필터링)")
    c1, c2, c3, c4 = st.columns(4)
    
    if c1.button(f"전체\n{total}건"): st.session_state.filter_emotion = "전체"
    if c2.button(f"🟢 긍정\n{pos_n}건 ({(pos_n/total)*100:.0f}%)"): st.session_state.filter_emotion = "긍정"
    if c3.button(f"🔴 부정\n{neg_n}건 ({(neg_n/total)*100:.0f}%)"): st.session_state.filter_emotion = "부정"
    if c4.button(f"⚪ 중립\n{neu_n}건 ({(neu_n/total)*100:.0f}%)"): st.session_state.filter_emotion = "중립"

    st.divider()
    st.info(f"현재 보기: **{st.session_state.filter_emotion}** 기사")

    # 필터링 적용
    filtered_data = st.session_state.analysis_results
    if st.session_state.filter_emotion != "전체":
        filtered_data = [r for r in st.session_state.analysis_results if r['emotion'] == st.session_state.filter_emotion]

    # 6. 카드형 뉴스 리스트 출력
    for res in filtered_data:
        color_class = "pos" if res['emotion'] == "긍정" else "neg" if res['emotion'] == "부정" else "neu"
        st.markdown(f"""
        <div class="news-card">
            <div class="sentiment-tag {color_class}">{res['emotion']}</div>
            
            <div class="section-label">기사 제목</div>
            <div class="content-text"><b>{res['title']}</b></div>
            
            <div class="section-label">핵심 요약 (Snippet)</div>
            <div class="content-text" style="font-size: 0.95em; color: #444;">{res['summary']}</div>
            
            <div class="section-label">AI 감성 분석 근거</div>
            <div class="reason-box">
                {res['analysis_text']}
            </div>
            
            <div style="margin-top: 15px; font-size: 0.8em; color: #777;">
                📅 {res['published']} | 🏢 {res['source']}
            </div>
            <br>
            <a href="{res['link']}" target="_blank" style="text-decoration: none;">
                <div style="text-align: center; padding: 10px; border: 1px solid #007BFF; color: #007BFF; border-radius: 8px; font-weight: bold;">기사 원문 읽기</div>
            </a>
        </div>
        """, unsafe_allow_html=True)