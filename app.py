import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import re

# 1. 페이지 설정 및 레이아웃
st.set_page_config(page_title="Global News AI Monitoring", page_icon="📊", layout="centered")

# 전문적인 UI를 위한 CSS 커스텀
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #f0f2f6; }
    .news-card { padding: 24px; border-radius: 12px; background-color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border: 1px solid #f0f2f6; }
    .sentiment-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 10px; }
    .pos { background-color: #e6f4ea; color: #1e8e3e; } /* 긍정 */
    .neg { background-color: #fce8e6; color: #d93025; } /* 부정 */
    .neu { background-color: #f1f3f4; color: #5f6368; } /* 중립 */
    .news-title { font-size: 1.4em; font-weight: 700; color: #1a1a1a; margin-bottom: 8px; line-height: 1.3; }
    .news-meta { color: #70757a; font-size: 0.85em; margin-bottom: 15px; }
    .news-summary { font-size: 0.95em; color: #3c4043; line-height: 1.6; margin-bottom: 18px; padding-left: 10px; border-left: 3px solid #dee2e6; }
    .analysis-box { padding: 15px; border-radius: 8px; font-size: 0.95em; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바: 설정 컨트롤러
with st.sidebar:
    st.header("⚙️ 분석 설정")
    api_key = st.text_input("Groq API Key", type="password", help="Groq 클라우드에서 발급받은 API 키를 입력하세요.")
    
    st.divider()
    
    # 국가/언어 설정
    lang_options = {
        "한국어 (KR)": {"lang": "ko", "country": "KR"},
        "영어 (US)": {"lang": "en", "country": "US"},
        "일본어 (JP)": {"lang": "ja", "country": "JP"},
        "중국어 (CN)": {"lang": "zh-CN", "country": "CN"}
    }
    selected_lang = st.selectbox("검색 국가/언어 선택", list(lang_options.keys()))
    config = lang_options[selected_lang]
    
    # 기사 개수 조절 슬라이더
    max_results = st.slider("분석할 기사 개수", min_value=5, max_value=100, value=20, step=5)
    
    st.divider()
    st.caption("AI Model: Llama-3.3-70B-Versatile")

# 3. 메인 화면 상단
st.title("🌐 실시간 글로벌 뉴스 분석기")

col_keyword, col_time = st.columns([3, 1])
with col_keyword:
    keyword = st.text_input("검색 키워드 (정확한 검색은 따옴표 사용)", value='"현대카드"')
with col_time:
    period = st.selectbox("분석 기간", ["1d", "7d", "30d"], index=1)

# 유틸리티 함수: 요약 내용 정제
def clean_summary(html_text, title):
    clean = re.sub('<[^<]+?>', '', html_text) # HTML 태그 제거
    if title in clean:
        clean = clean.replace(title, "").strip() # 제목 중복 제거
    return clean if clean else "본문 요약 내용을 가져올 수 없습니다."

# 유틸리티 함수: AI 감성 분석
def analyze_sentiment(title, snippet, client):
    prompt = f"경제 뉴스 전문가로서 다음 뉴스를 [긍정], [부정], [중립] 중 하나로 분류하고 이유를 한 문장으로 설명하세요.\n\n제목: {title}\n요약: {snippet}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception:
        return "[중립] API 호출 오류로 분석을 완료하지 못했습니다."

# 4. 분석 로직 실행
if st.button("🚀 실시간 뉴스 분석 및 통계 산출", use_container_width=True):
    if not api_key:
        st.error("사이드바에서 Groq API 키를 먼저 입력해주세요!")
    else:
        with st.spinner(f"'{keyword}'에 대한 최신 뉴스 {max_results}건을 분석 중입니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            # 슬라이더로 설정한 개수만큼 기사 추출
            articles = search['entries'][:max_results]
            
            if not articles:
                st.warning("검색 결과가 없습니다. 키워드나 기간을 변경해 보세요.")
            else:
                results = []
                pos_c, neg_c, neu_c = 0, 0, 0
                
                # 진행 상태 바 표시
                progress_bar = st.progress(0)
                
                for i, entry in enumerate(articles):
                    title = entry.title
                    summary = clean_summary(entry.summary, title)
                    analysis = analyze_sentiment(title, summary, client)
                    
                    # 감성 분류에 따른 카운트 및 색상 지정
                    if "[긍정]" in analysis:
                        color_class, emotion = "pos", "긍정"
                        pos_c += 1
                    elif "[부정]" in analysis:
                        color_class, emotion = "neg", "부정"
                        neg_c += 1
                    else:
                        color_class, emotion = "neu", "중립"
                        neu_c += 1
                    
                    results.append({
                        "title": title,
                        "summary": summary,
                        "analysis": analysis,
                        "color_class": color_class,
                        "emotion": emotion,
                        "published": entry.published,
                        "source": entry.source.title,
                        "link": entry.link
                    })
                    progress_bar.progress((i + 1) / len(articles))
                
                # --- [1단계: 통계 대시보드 출력] ---
                total = len(results)
                st.subheader("📈 실시간 감성 지표")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("총 분석 건수", f"{total}건")
                c2.metric("긍정", f"{pos_c}건", f"{(pos_c/total)*100:.1f}%")
                c3.metric("부정", f"{neg_c}건", f"-{(neg_c/total)*100:.1f}%", delta_color="inverse")
                c4.metric("중립", f"{neu_c}건", f"{(neu_c/total)*100:.1f}%", delta_color="off")
                st.divider()

                # --- [2단계: 카드형 뉴스 리스트 출력] ---
                for res in results:
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="sentiment-tag {res['color_class']}">
                            {res['emotion']}
                        </div>
                        <div class="news-title">{res['title']}</div>
                        <div class="news-meta">📅 {res['published']} | 🏢 {res['source']}</div>
                        <div class="news-summary">
                            <b>제목:</b> {res['summary']}
                        </div>
                        <div class="analysis-box" style="background-color: {'#f1f8e9' if res['color_class']=='pos' else '#fff5f5' if res['color_class']=='neg' else '#f8f9fa'};">
                            <b>🤖 AI Insights:</b><br>{res['analysis'].split(']')[-1].strip() if ']' in res['analysis'] else res['analysis']}
                        </div>
                        <br>
                        <a href="{res['link']}" target="_blank" style="text-decoration: none;">
                            <div style="text-align: center; padding: 12px; border: 1px solid #007BFF; color: #007BFF; border-radius: 8px; font-weight: bold; background-color: white;">기사 원문 읽기</div>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)

st.divider()
st.caption("© 2026 AI News Analyzer | Hyundai Card Global PR Support Tool")