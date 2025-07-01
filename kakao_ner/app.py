# app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Home page is working!"

@app.route('/kakao/ner', methods=['POST'])
def kakao_ner_service():
    # 모든 복잡한 로직을 제거하고, 간단한 JSON만 응답
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "Test response from /kakao/ner"
                    }
                }
            ]
        }
    }
