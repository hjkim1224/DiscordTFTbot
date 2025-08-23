import requests
import urllib.parse
import time
from config import API_KEY

HEADERS = {"X-Riot-Token": API_KEY}

#PUUID와 Summoner Id를 가져옴
def get_player_ids(player_name, player_tag):

    encoded_name = urllib.parse.quote(player_name)
    encoded_tag = urllib.parse.quote(player_tag)
    
    account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    account_response = requests.get(account_url, headers=HEADERS)
    
    # PUUID
    if account_response.status_code != 200:
        print(f"**[오류]** PUUID를 가져올 수 없습니다. 닉네임/태그를 확인하세요.")
        print(f"오류 코드: {account_response.status_code}, 메시지: {account_response.text}")
        return None, None
    puuid = account_response.json()['puuid']
    
    summoner_url = f"https://kr.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    summoner_response = requests.get(summoner_url, headers=HEADERS)
    
    # Summoner ID
    if summoner_response.status_code != 200:
        print(f"**[오류]** Summoner ID를 가져올 수 없습니다. 이 계정이 한국 TFT 서버에 기록이 없거나 API 키가 만료되었을 수 있습니다.")
        print(f"오류 코드: {summoner_response.status_code}, 메시지: {summoner_response.text}")
        return puuid, None
        
    summoner_id = summoner_response.json()['puuid']
    return puuid, summoner_id

#해당 유저의 랭크 점수를 불러오고 (tier, rank, lp)순서로 반환함
def get_league_info(puuid):

    if not puuid: 
        return "Unranked", "IV", 0
    url = f"https://kr.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200 and response.json():
        league_data = response.json()[0]
        return league_data.get('tier', 'Unranked'), league_data.get('rank', 'I'), league_data.get('leaguePoints', 0)
    return "Unranked", "IV", 0

def get_master_list():
    url = "https://kr.api.riotgames.com//tft/league/v1/master"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200 and response.json():
        master_list = response.json()
        return master_list["entries"]

def get_grandmaster_list():
    url = "https://kr.api.riotgames.com//tft/league/v1/grandmaster"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200 and response.json():
        grandmaster_list = response.json()
        return grandmaster_list["entries"]
    
def get_challenger_list():
    url = "https://kr.api.riotgames.com//tft/league/v1/challenger"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200 and response.json():
        challenger_list = response.json()
        return challenger_list["entries"]

def get_merge_sort_ch_gm_m_list():
    master_list = get_master_list()
    grandmaster_list = get_grandmaster_list()
    challenger_list = get_challenger_list()

    merged_list = []

    for i in master_list:
        merged_list.append(i['leaguePoints'])    
    for i in grandmaster_list:
        merged_list.append(i['leaguePoints'])
    for i in challenger_list:
        merged_list.append(i['leaguePoints'])
    
    merged_list.sort(reverse=True)

    return merged_list
  

def get_grandmaster_cutline():
    ranking_list_for_cutline = get_merge_sort_ch_gm_m_list()
    return ranking_list_for_cutline[899]

def get_challenger_cutline():
    ranking_list_for_cutline = get_merge_sort_ch_gm_m_list()
    return ranking_list_for_cutline[299]


# 새로운 게임 시작 감지
def check_for_new_game(puuid):
    
    url = f"https://kr.api.riotgames.com/lol/spectator/tft/v5/active-games/by-puuid/{puuid}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None

# 게임 종료 후 상세 정보 가져옴
def get_match_details(match_id):

    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/{match_id}"
    for _ in range(15):
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        time.sleep(30)
    return None

# 가장 최근 매치의 ID를 가져옴
def get_last_match_id(puuid):

    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200 and response.json():
        return response.json()[0]
    return None