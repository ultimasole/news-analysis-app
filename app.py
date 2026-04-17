import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import re

# 1. 페이지 설정
st.set_page_config(page_title="AI PR Monitor", page_icon="📈", layout="centered")

# CSS 고도화 (글자 겹침 방지 및 박스 디자인 개선)
st.markdown("""
    <style>
    .news-card { padding: 24px; border-radius: 12px; background-color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border: 1px solid #f0f2f6; }
    .sentiment-tag { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 10px; }
    .pos { background-color: #e6f4ea; color: #1e8e3e; }
    .neg { background-color: #fce8e6; color: #d93025; }
    .neu { background-color: #f1f3f4; color: #5f6368; }
    .section-label { font-size: 0.75em; font-weight: bold; color: #007BFF; text-transform: uppercase; margin-bottom: 3px; letter-spacing: 0.5px; }
    .content-text { font-size: 1.05em; color: #1a1a1a; margin-bottom: 15px; line-height: 1.5; word-break: keep-all; }
    .reason-box { padding: 15px; border-radius: 8px; font-size: 0.95em; line-height: 1.6; border-left: 5px solid #007BFF; background-color: #f0f7ff; color: #333; }
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
    max_results = st.slider("분석 기사 개수", 5, 50, 15)

# 3. 메인 화면
st.title("🌐 실시간 뉴스 감성 분석")

col_search, col_time = st.columns([3, 1])
with col_search:
    keyword = st.text_input("분석 키워드", value='"현대카드"')
with col_time:
    period = st.selectbox("기간", ["1d", "7d", "30d"], index=1)

# 세션 상태 유지
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = []
if 'filter_emotion' not in st.session_state: st.session_state.filter_emotion = "전체"

def clean_summary(html_text, title):
    # 1. HTML 태그 제거 및 공백 정제
    clean = re.sub('<[^<]+?>', '', html_text).strip()
    clean = clean.replace('&nbsp;', ' ')
    
    # 2. '제목'과 '요약'의 중복 제거 (가장 중요한 부분)
    # 제목이 요약의 앞부분에 포함되어 있다면 그 부분만 삭제
    if clean.startswith(title):
        clean = clean[len(title):].strip()
    
    # 3. 언론사 이름이 반복되는 경우도 삭제 (예: "- 조선일보")
    # 보통 RSS 끝에 ' - 매체명'이 붙는 경우가 많음
    clean = re.split(r' - \w+', clean)[0].strip()

    # 4. 만약 다 지우고 났더니 남은 게 없거나 너무 짧다면?
    if len(clean) < 5:
        return "해당 매체에서 본문 요약을 제공하지 않습니다. 원문을 통해 상세 내용을 확인하세요."
        
    return clean

def analyze_sentiment(title, snippet, client):
    # AI에게 형식을 엄격하게 요구하는 프롬프트
    prompt = f"""당신은 현대카드 소속 PR 전문가입니다. 다음 뉴스를 분석해 현대카드에게 [긍정], [부정], [중립] 중 어느 감성에 해당하는지 분류하고 이유를 설명하세요.
    해당 감성이 현대카드와 관련한 것인지, 경쟁사에 대한 것인지를 구분한 뒤, [분류]는 현대카드를 기준으로 답하세요.
    반드시 첫 단어를 [분류]로 시작하세요. 예: [긍정] 실적 발표 수치가 시장 기대치를 상회함.
    
    뉴스 제목: {title}
    뉴스 요약: {snippet}"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 # 일관성을 위해 낮은 창의성 설정
        )
        return completion.choices[0].message.content
    except:
        return "[중립] AI 분석 서버 통신 오류"

# 4. 분석 실행
if st.button("🚀 뉴스 분석 및 통계 산출", use_container_width=True):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    else:
        with st.spinner("최신 데이터를 정밀 분석 중입니다..."):
            client = Groq(api_key=api_key)
            gn = GoogleNews(lang=config['lang'], country=config['country'])
            search = gn.search(keyword, when=period)
            
            articles = search['entries'][:max_results]
            temp_results = []
            
            for entry in articles:
                title = entry.title
                summary = clean_summary(entry.summary, title)
                raw_analysis = analyze_sentiment(title, summary, client)
                
                # 분석 텍스트 파싱 로직 강화
                if "]" in raw_analysis:
                    emotion_tag = raw_analysis.split("]")[0].replace("[", "").strip()
                    reason_text = raw_analysis.split("]")[1].strip()
                else:
                    emotion_tag = "중립"
                    reason_text = raw_analysis
                
                emotion = "중립"
                if "긍정" in emotion_tag: emotion = "긍정"
                elif "부정" in emotion_tag: emotion = "부정"
                
                temp_results.append({
                    "title": title,
                    "summary": summary,
                    "reason": reason_text,
                    "emotion": emotion,
                    "published": entry.published,
                    "source": entry.source.title,
                    "link": entry.link
                })
            st.session_state.analysis_results = temp_results
            st.session_state.filter_emotion = "전체"

# 5. 통계 및 필터링
if st.session_state.analysis_results:
    res_df = pd.DataFrame(st.session_state.analysis_results)
    total = len(res_df)
    pos_n = len(res_df[res_df['emotion'] == '긍정'])
    neg_n = len(res_df[res_df['emotion'] == '부정'])
    neu_n = len(res_df[res_df['emotion'] == '중립'])

    st.subheader("📈 실시간 여론 지표")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button(f"전체\n{total}건"): st.session_state.filter_emotion = "전체"
    if c2.button(f"🟢 긍정\n{pos_n}건"): st.session_state.filter_emotion = "긍정"
    if c3.button(f"🔴 부정\n{neg_n}건"): st.session_state.filter_emotion = "부정"
    if c4.button(f"⚪ 중립\n{neu_n}건"): st.session_state.filter_emotion = "중립"

    st.divider()
    
    # 필터링 적용 리스트
    display_data = st.session_state.analysis_results
    if st.session_state.filter_emotion != "전체":
        display_data = [r for r in display_data if r['emotion'] == st.session_state.filter_emotion]

    for res in display_data:
        tag_class = "pos" if res['emotion'] == "긍정" else "neg" if res['emotion'] == "부정" else "neu"
        st.markdown(f"""
        <div class="news-card">
            <div class="sentiment-tag {tag_class}">{res['emotion']}</div>
            <div class="section-label">원본 기사 제목</div>
            <div class="content-text"><b>{res['title']}</b></div>
            <div class="section-label">핵심 요약 (Snippet)</div>
            <div class="content-text" style="font-size: 0.95em; color: #555;">{res['summary']}</div>
            <div class="section-label">AI 감성 분석 근거</div>
            <div class="reason-box">{res['reason']}</div>
            <div style="margin-top: 15px; font-size: 0.8em; color: #888;">
                📅 {res['published']} | 🏢 {res['source']}
            </div>
            <br>
            <a href="{res['link']}" target="_blank" style="text-decoration: none;">
                <div style="text-align: center; padding: 10px; border: 1px solid #007BFF; color: #007BFF; border-radius: 8px; font-weight: bold; background-color: white;">기사 원문 읽기</div>
            </a>
        </div>
        """, unsafe_allow_html=True)