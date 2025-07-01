import os
from flask import Flask, request, jsonify
import openai
import google.generativeai as genai

# --- Flask 앱 초기화 ---
app = Flask(__name__)

# --- 1. Streamlit 앱에서 핵심 로직 가져오기 ---

# API 키는 환경 변수에서 불러옵니다.
# 서버 배포 시 이 환경 변수들을 설정해야 합니다.
# 예: export OPENAI_API_KEY='your_openai_key'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# NER 서비스의 핵심 두뇌인 시스템 프롬프트를 그대로 가져옵니다.
SYSTEM_PROMPT = """
당신은 의사와 환자의 대화록을 분석하여, 임상적으로 유의미한 정보를 구조화하는 고도로 전문화된 의료 AI 어시스턴트입니다. 당신의 임무는 대화의 맥락과 시간의 흐름을 정확히 파악하여 정보를 추출하는 것입니다.
(이하 생략 - 제공해주신 프롬프트 내용 전체를 여기에 복사)
...
## 출력 형식
- 추출된 정보는 `개체명: 값` 형식으로, 한 줄에 하나씩 나열합니다.
- 오직 값이 존재하는 (Y, N, 또는 텍스트) 개체명만 출력합니다.
"""

# API 호출 함수들을 약간 수정하여 가져옵니다. (is_comparison 등 불필요한 인자 제거)
def call_openai_api(api_key, user_prompt):
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    client = openai.OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0, # 일관된 결과를 위해 0으로 설정
    )
    return response.choices[0].message.content

def call_google_api(api_key, user_prompt):
    if not api_key:
        raise ValueError("Google API 키가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-1.5-flash-latest',
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(user_prompt)
    return response.text


# --- 2. 카카오톡 연동을 위한 Webhook 엔드포인트 생성 ---

@app.route('/kakao/ner', methods=['POST'])
def kakao_ner_service():
    try:
        # 카카오 챗봇 플랫폼이 보내는 요청(SkillRequest)을 받습니다.
        req = request.get_json()
        
        # 사용자가 보낸 대화록 텍스트를 추출합니다.
        user_text = req['userRequest']['utterance']

        # (선택) 어떤 API를 사용할지 결정합니다. 여기서는 OpenAI를 기본으로 사용합니다.
        # 필요하다면 사용자의 입력에 따라 동적으로 바꿀 수도 있습니다.
        # 예: 'gemini로 분석해줘' 라는 텍스트가 포함되면 Gemini 사용
        api_to_use = "openai" 
        
        # LLM을 호출하여 NER 분석을 수행합니다.
        if api_to_use == "openai":
            ner_result = call_openai_api(OPENAI_API_KEY, user_text)
        else: # "google"
            ner_result = call_google_api(GOOGLE_API_KEY, user_text)

        # --- 3. 분석 결과를 카카오톡 메시지 형식(SkillResponse)으로 만듭니다. ---
        
        # 방법 1: 간단한 텍스트로 응답
        # response_text = f"✅ 대화록 분석 결과:\n\n{ner_result}"

        # 방법 2: 더 보기 좋은 TextCard로 응답 (추천)
        res = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "textCard": {
                            "title": "🩺 AI 대화록 분석 결과",
                            "description": ner_result,
                            "buttons": [
                                {
                                    "action": "webLink",
                                    "label": "서비스 더 알아보기",
                                    "webLinkUrl": "https://your-service-homepage.com" # 필요시 웹사이트 링크 추가
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        return jsonify(res)

    except Exception as e:
        print(f"Error: {e}")
        # 오류 발생 시 사용자에게 보낼 비상 메시지
        res = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "죄송합니다. 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                        }
                    }
                ]
            }
        }
        return jsonify(res)

if __name__ == '__main__':
    # 서버 실행 (개발/테스트용)
    # 실제 배포 시에는 Gunicorn, uWSGI 같은 WSGI 서버를 사용해야 합니다.
    app.run(host='0.0.0.0', port=8000)