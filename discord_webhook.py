import requests
from config import DISCORD_WEBHOOK_URL, PLAYER_NAME

def send_discord_message(message):
    if not DISCORD_WEBHOOK_URL:
        print("디스코드 웹훅 URL이 설정되지 않았습니다.")
        return
    
    payload = {"content": message, "username": f"{PLAYER_NAME} 엿보기"}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"디스코드 메시지 전송 실패: {e}")