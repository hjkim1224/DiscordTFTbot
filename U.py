
import requests
import time
import urllib.parse
import json
import os

# --------------------------------------------------------------------------------

API_KEY = "RGAPI-468eb91c-dc4f-4bd4-bea8-5e89e38a6991"
PLAYER_NAME = "이해과정1"
PLAYER_TAG = "KR1"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1408280389679714437/XviftwzTxxbm07_LPErfuljTDyKU0bBCMdi07hyaHBRZmy1rmAW0sKJ5G8kJqG-KgVyw"
STREAK_FILE = "streak_data.json"


encoded_name = urllib.parse.quote(PLAYER_NAME)
encoded_tag = urllib.parse.quote(PLAYER_TAG)
    
    # 1. PUUID 가져오기
account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
headers = {"X-Riot-Token": API_KEY}
account_response = requests.get(account_url, headers=headers)

if account_response.status_code != 200:
    print(f"**[오류]** PUUID를 가져올 수 없습니다. 닉네임/태그가 올바른지 확인하세요.")
    print(f"오류 코드: {account_response.status_code}, 메시지: {account_response.text}")
    return None, None
puuid = account_response.json()['id']


print(f"puuid")