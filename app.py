import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import re

# 1. 페이지 설정
st.set_page_config(page_title="Global News AI Dashboard", page_icon="📈", layout="centered")

# CSS 고도화 (카드 디자인 및 애니메이션)
st.markdown("""
    <style>
    .news-card {
        padding: 24px;
        border-radius: 12px;
        background-color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border: 1px solid #f0f2f6;
    }
    .sentiment-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .pos { background-color: #e6f4ea; color: #1e8e3e; } /* 긍정: 초록 */
    .neg { background-color: #fce8e6; color: #d93025; } /* 부정: 빨강 */
    .neu { background-color: #f1f3f4; color: #5f6368; } /* 중립: 회색 */
    
    .news-title { font-size: 1.4em; font-weight: 700; color: #1a1a1a; margin-bottom: 8px; line-height: 1.3; }
    .news-meta { color: #70757a; font-size: 0.85em; margin-bottom: 15px; }
    .news-summary { font-size: 0.95em; color: #3c4043; line-height: 1.6; margin-bottom: 18px; padding-left: 10px; border-left: 3px solid #dee2e6; }
    .analysis-box { padding: 15px; border-radius: 8px; font-size: 0.95em; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Groq API Key", type="password")
    
    lang_options = {
        "한국어 (KR)": {"lang": "ko", "country": "KR"},
        "영어 (US)": {"lang": "en", "country": "US"},
        "일본어 (JP)": {"lang": "ja", "country": "JP"},
        "중국어 (CN)": {"lang": "zh-CN", "country": "CN"}
    }
    selected_lang = st.selectbox("검색 국가/언어", list(lang_options.keys()))
    config = lang_options[selected_lang]
    st.divider()
    st.caption("AI 분석 결과는 Llama 3.3 모델을 기반으로 생성됩니다.")

# 3. 메인 화면
st.title("📊 뉴스 감성 대시보드")

col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("분석할 키워드를 입력하세요", value='"현대카드"')
with col2:
    period = st.selectbox("기간", ["1d", "7d", "30d"], index=1)

# HTML 태그 제거 및 요약 정제 함수
def clean_summary(html_text, title):
    # HTML 태그 제거
    clean = re.sub('<[^<]+?>', '', html_text)
    # 제목과 내용이 겹치면 요약 부분만 추출 (Google News 특성 대응)
    if title in clean:
        clean = clean.replace(title, "").strip()
    return clean if clean else "요약 내용 없음"

# AI 감성 분석 함수 (포맷 강제)
def analyze_sentiment(title, snippet, client):
    prompt = f"""
    당신은 경제 뉴스 분석 전문가입니다. 아래 뉴스를 분석하여 긍정, 부정, 중립 중 하나로 분류하고 이유를 설명하세요.
    반드시 첫 단어에 [긍정], [부정], [중립] 중 하나를 적으세요.
    
    제목: {title}
    요약: {snippet}
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return "[중립] 분석을 수행할 수 없습니다."

# 4. 분석 시작
if st.button("실시간 분석 실행", use_container_width=True):
    if not api_key:
        st.error("Groq API 키를 입력해주세요.")
    else:
        with st.spinner("최신 기사를 분석하고 있습니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            if not search['entries']:
                st.warning("수집된 뉴스가 없습니다.")
            else:
                for entry in search['entries'][:10]:
                    title = entry.title
                    # 요약 내용 정제
                    summary = clean_summary(entry.summary, title)
                    analysis = analyze_sentiment(title, summary, client)
                    
                    # 감성에 따른 색상 클래스 결정
                    color_class = "neu"
                    if "[긍정]" in analysis: color_class = "pos"
                    elif "[부정]" in analysis: color_class = "neg"
                    
                    # 카드 출력
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="sentiment-tag {color_class}">
                            {analysis.split(']')[0][1:] if ']' in analysis else '중립'}
                        </div>
                        <div class="news-title">{title}</div>
                        <div class="news-meta">📅 {entry.published} | 🏢 {entry.source.title}</div>
                        <div class="news-summary">
                            <b>Summary:</b> {summary}
                        </div>
                        <div class="analysis-box" style="background-color: {'#f1f8e9' if color_class=='pos' else '#fff5f5' if color_class=='neg' else '#f8f9fa'};">
                            <b>🤖 AI Insights:</b><br>{analysis.split(']')[-1].strip() if ']' in analysis else analysis}
                        </div>
                        <br>
                        <a href="{entry.link}" target="_blank" style="text-decoration: none;">
                            <div style="text-align: center; padding: 10px; border: 1px solid #007BFF; color: #007BFF; border-radius: 6px; font-weight: bold;">기사 원문 보기</div>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)