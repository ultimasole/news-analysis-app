import streamlit as st
import pandas as pd
from pygooglenews import GoogleNews
from groq import Groq
import os

# 1. 앱이 돌아가는지 확인하기 위한 테스트 문구 추가
st.write("✅ 앱이 정상적으로 실행되었습니다!")

# 1. 환경 변수에서 API 키 가져오기 (배포 시 Secrets 활용)
# 로컬 테스트 시에는 직접 입력하거나 환경 변수에 설정하세요.
api_key = st.sidebar.text_input("Groq API Key", type="password")

def analyze_sentiment(title, snippet, client):
    prompt = f"다음 뉴스의 감성을 '긍정', '부정', '중립' 중 하나로 분류하고 짧은 이유를 쓰세요.\n제목: {title}\n요약: {snippet}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except:
        return "분석 실패"

# UI 구성
st.title("글로벌 뉴스 감성 분석기 📊")
keyword = st.text_input("검색어", value='"현대카드"')
period = st.selectbox("기간", ["1d", "7d", "30d"])

if st.button("뉴스 수집 및 분석"):
    if not api_key:
        st.error("사이드바에 Groq API 키를 입력해주세요.")
    else:
        client = Groq(api_key=api_key)
        gn = GoogleNews(lang='ko', country='KR')
        search = gn.search(keyword, when=period)
        
        data = []
        for entry in search['entries'][:10]: # 테스트용 10개
            res = analyze_sentiment(entry.title, entry.summary, client)
            data.append({
                "날짜": entry.published,
                "제목": entry.title,
                "AI 분석": res,
                "링크": entry.link
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, column_config={"링크": st.column_config.LinkColumn()})