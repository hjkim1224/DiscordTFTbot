import os
import json
from config import STREAK_FILE, TRANS_TRAIT_FILE

#연승 지표 파일 존재시 load 없다면 0으로 초기화
def load_streak_data():
    if os.path.exists(STREAK_FILE):
        with open(STREAK_FILE, 'r') as f:
            return json.load(f)
    return {"streak_type": "None", "streak_count": 0}

#연승 데이터를 다시 파일에 저장
def save_streak_data(data):
    with open(STREAK_FILE, 'w') as f:
        json.dump(data, f)

#특성 번역 파일 로드
def load_trait_translations():
    try:
        with open(TRANS_TRAIT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"번역 파일({TRANS_TRAIT_FILE})을 찾을 수 없습니다.")
        return {}