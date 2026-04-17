import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import re

# 1. 페이지 설정
st.set_page_config(page_title="News Sentiment Dashboard", page_icon="📈", layout="centered")

# CSS 고도화
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #f0f2f6; }
    .news-card { padding: 24px; border-radius: 12px; background-color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border: 1px solid #f0f2f6; }
    .sentiment-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 10px; }
    .pos { background-color: #e6f4ea; color: #1e8e3e; }
    .neg { background-color: #fce8e6; color: #d93025; }
    .neu { background-color: #f1f3f4; color: #5f6368; }
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
    st.caption("AI 분석 모델: Llama 3.3-70B")

# 3. 메인 화면
st.title("📊 뉴스 감성 분석 대시보드")

col_search, col_period = st.columns([3, 1])
with col_search:
    keyword = st.text_input("분석할 키워드", value='"현대카드"')
with col_period:
    period = st.selectbox("기간", ["1d", "7d", "30d"], index=1)

def clean_summary(html_text, title):
    clean = re.sub('<[^<]+?>', '', html_text)
    if title in clean:
        clean = clean.replace(title, "").strip()
    return clean if clean else "요약 내용 없음"

def analyze_sentiment(title, snippet, client):
    prompt = f"경제 뉴스 분석가로서 아래 뉴스를 [긍정], [부정], [중립] 중 하나로 분류하고 이유를 한 문장으로 쓰세요.\n\n제목: {title}\n요약: {snippet}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return "[중립] 분석 실패"

# 4. 분석 실행
if st.button("실시간 분석 및 통계 산출", use_container_width=True):
    if not api_key:
        st.error("Groq API 키를 입력해주세요.")
    else:
        with st.spinner("최신 기사를 분석하고 통계를 생성하는 중입니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            if not search['entries']:
                st.warning("수집된 뉴스가 없습니다.")
            else:
                results = []
                pos_count, neg_count, neu_count = 0, 0, 0
                
                # 데이터 수집 및 분석
                for entry in search['entries'][:10]:
                    title = entry.title
                    summary = clean_summary(entry.summary, title)
                    analysis = analyze_sentiment(title, summary, client)
                    
                    # 감성 분류 카운트
                    if "[긍정]" in analysis: 
                        color_class = "pos"
                        pos_count += 1
                    elif "[부정]" in analysis: 
                        color_class = "neg"
                        neg_count += 1
                    else: 
                        color_class = "neu"
                        neu_count += 1
                    
                    results.append({
                        "title": title,
                        "summary": summary,
                        "analysis": analysis,
                        "color_class": color_class,
                        "published": entry.published,
                        "source": entry.source.title,
                        "link": entry.link
                    })
                
                # --- [통계 섹션 추가] ---
                total = len(results)
                st.subheader("📈 실시간 감성 분석 통계")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("총 검색 결과", f"{total}건")
                c2.metric("긍정", f"{pos_count}건", f"{(pos_count/total)*100:.1f}%")
                c3.metric("부정", f"{neg_count}건", f"-{(neg_count/total)*100:.1f}%", delta_color="inverse")
                c4.metric("중립", f"{neu_count}건", f"{(neu_count/total)*100:.1f}%", delta_color="off")
                st.divider()

                # --- [카드 출력 섹션] ---
                for res in results:
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="sentiment-tag {res['color_class']}">
                            {res['analysis'].split(']')[0][1:] if ']' in res['analysis'] else '중립'}
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
                            <div style="text-align: center; padding: 10px; border: 1px solid #007BFF; color: #007BFF; border-radius: 6px; font-weight: bold;">기사 원문 보기</div>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)