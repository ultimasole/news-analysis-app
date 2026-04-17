import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import os

# 1. 페이지 설정 (아이콘 및 레이아웃)
st.set_page_config(page_title="Global News AI Analyzer", page_icon="🌐", layout="centered")

# CSS 커스텀 스타일 (폰트 및 간격 조정)
st.markdown("""
    <style>
    .reportview-container { background: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007BFF; color: white; }
    .news-card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e6e9ef;
        background-color: white;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .sentiment-box {
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바: 설정 및 언어 선택
with st.sidebar:
    st.header("⚙️ 검색 및 AI 설정")
    api_key = st.text_input("Groq API Key", type="password")
    
    # 국가/언어 프리셋 설정
    lang_options = {
        "한국어 (KR)": {"lang": "ko", "country": "KR"},
        "영어 (US)": {"lang": "en", "country": "US"},
        "일본어 (JP)": {"lang": "ja", "country": "JP"},
        "중국어 (CN)": {"lang": "zh-CN", "country": "CN"}
    }
    selected_lang_label = st.selectbox("검색 언어/국가 선택", list(lang_options.keys()))
    config = lang_options[selected_lang_label]
    
    st.divider()
    st.info("검색 대상 국가와 언어에 따라 Google News의 결과가 달라집니다.")

# 3. 메인 화면 헤더
st.title("🌐 글로벌 뉴스 AI 모니터링")
st.caption(f"현재 설정: {selected_lang_label} | AI 분석 모델: Llama 3.3")

col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("검색 키워드", value='"현대카드"')
with col2:
    period = st.selectbox("기간", ["1d", "7d", "30d"], index=1)

# 감성 분석 함수 (결과값 정제 추가)
def analyze_sentiment(title, snippet, client):
    prompt = f"""
    당신은 글로벌 경제 뉴스 분석가입니다. 아래 뉴스의 제목과 내용을 바탕으로 감성을 분석하세요.
    결과는 반드시 '[감성: 긍정/부정/중립] - 이유' 형식으로 한 문장으로만 답변하세요.
    
    제목: {title}
    내용: {snippet}
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"분석 실패: {str(e)}"

# 4. 분석 실행 및 결과 출력
if st.button("실시간 뉴스 분석 시작"):
    if not api_key:
        st.error("먼저 왼쪽 사이드바에 Groq API 키를 입력해주세요.")
    else:
        with st.spinner(f"'{selected_lang_label}' 기사를 수집하고 분석 중입니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            articles = search['entries'][:10]
            
            if not articles:
                st.warning("검색 결과가 없습니다.")
            else:
                for entry in articles:
                    # AI 분석 실행
                    analysis_res = analyze_sentiment(entry.title, entry.summary, client)
                    
                    # 카드형 UI 출력
                    with st.container():
                        st.markdown(f"""
                        <div class="news-card">
                            <h3 style='margin-bottom: 5px;'>{entry.title}</h3>
                            <p style='color: gray; font-size: 0.9em;'>📅 {entry.published} | 🏢 {entry.source.title}</p>
                            <hr style='margin: 10px 0;'>
                            <p><b>📝 요약:</b> {entry.summary}</p>
                            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 5px solid #007BFF;'>
                                <b>🤖 AI 감성 분석:</b><br>{analysis_res}
                            </div>
                            <br>
                            <a href="{entry.link}" target="_blank" style="text-decoration: none;">
                                <button style="width: 100%; padding: 10px; background-color: white; border: 1px solid #007BFF; color: #007BFF; cursor: pointer; border-radius: 5px;">기사 원문 읽기</button>
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

st.divider()
st.caption("© 2026 Global PR Monitoring Tool | Powered by Streamlit & Groq")