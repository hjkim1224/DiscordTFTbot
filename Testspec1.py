import requests
import time
import urllib.parse
import json
import os
import math
import pandas as pd
import datetime
import json
import collections


# --------------------------------------------------------------------------------

API_KEY = "RGAPI-b37b8cf9-4576-42be-80c9-920a0c2feac3" #API 24시간마다초기화잊지않기기기기
PLAYER_NAME = "현실회피장치"
PLAYER_TAG = "LOL"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1408331948346179704/1ZQfxKsEiKwX13Ta1fV9iKUC-JXqskG6tqcKfiGC_-ase0RVFN3FtSP1hRA9nH7Qp-cx"
STREAK_FILE = "streak_data.json" #외부파일따로
TRANS_FILE = "trait_ko.json"


# 번역용.
try:
    with open(TRANS_FILE, 'r', encoding='utf-8') as f:
        trait_translations = json.load(f)
except FileNotFoundError:
    print("번역 파일(trait_ko.json)을 찾을 수 없습니다.")
    trait_translations = {} 
# -------------------------------------------------------
#외부파일연승연패
def load_streak_data():
    if os.path.exists(STREAK_FILE):
        with open(STREAK_FILE, 'r') as f:
            return json.load(f)
    return {"streak_type": "None", "streak_count": 0}

def save_streak_data(data):
    with open(STREAK_FILE, 'w') as f:
        json.dump(data, f)

# -----------------------------------
# --------------------------------------------------------------------------------------------------

def get_player_ids():
    """닉네임과 태그로 PUUID와 암호화된 Summoner ID를 모두 가져오는 함수"""
    encoded_name = urllib.parse.quote(PLAYER_NAME)
    encoded_tag = urllib.parse.quote(PLAYER_TAG)
    
    # PUUID 구하기
    account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    headers = {"X-Riot-Token": API_KEY}
    account_response = requests.get(account_url, headers=headers)

    if account_response.status_code != 200:
        print(f"**[오류]** PUUID를 가져올 수 없습니다. 닉네임/태그가 올바른지 확인하세요.")
        print(f"오류 코드: {account_response.status_code}, 메시지: {account_response.text}")
        return None, None
    puuid = account_response.json()['puuid']
    
    #  Summoner ID 구하기
    summoner_url = f"https://kr.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    summoner_response = requests.get(summoner_url, headers=headers)
    
    if summoner_response.status_code != 200:
        print(f"**[오류]** Summoner ID를 가져올 수 없습니다. 이 계정이 한국 TFT 서버에 기록이 없거나 API 키가 만료되었을 수 있습니다.")
        print(f"오류 코드: {summoner_response.status_code}, 메시지: {summoner_response.text}")
        return puuid, None
    
    summoner_id = summoner_response.json()['puuid']
    #---------------------------------------------------------------------------------------------
    
    return puuid, summoner_id


def get_league_info(puuid):
    if not puuid: return "Unranked", "IV", 0
    url = f"https://kr.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        league_data = response.json()[0]
        tier = league_data['tier']
        rank = league_data.get('rank', 'I') # Master 이상은 rank 정보가 없는듯
        lp = league_data['leaguePoints']
        return tier, rank, lp
    return "Unranked", "IV", 0

def convert_rank_to_score(tier, rank, lp):           #랭크를점수로
    tier_base_scores = {"IRON": 0, "BRONZE": 400, "SILVER": 800, "GOLD": 1200, "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400, "MASTER": 2800, "GRANDMASTER": 2800, "CHALLENGER": 2800}
    rank_scores = {"IV": 0, "III": 100, "II": 200, "I": 300}
    
    if tier == "Unranked":
        return 800 # 언랭은실버
    
    
    base_score = tier_base_scores.get(tier, 0)
    rank_score = rank_scores.get(rank, 0)
    
    # Master 이상 티어는 LP를 그대로 더함
    if tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return base_score + lp
    else:
        return base_score + rank_score + lp

def convert_score_to_rank(score):         #점수를랭크로
    if score >= 2800: # Master+
        lp = score - 2800
        # 마스터 이상은 2800으로퉁
        return "Master", f"{lp} LP"
        
    tiers = [("DIAMOND", 2400), ("EMERALD", 2000), ("PLATINUM", 1600), ("GOLD", 1200), ("SILVER", 800), ("BRONZE", 400), ("IRON", 0)]
    ranks = [("I", 300), ("II", 200), ("III", 100), ("IV", 0)]
    
    for tier_name, base_score in tiers:
        if score >= base_score:
            tier_lp = score - base_score
            for rank_name, rank_score in ranks:
                if tier_lp >= rank_score:
                    lp = tier_lp - rank_score
                    return f"{tier_name} {rank_name}", f"{lp} LP"
    return "Unknown", ""

def get_lobby_average_tier(CurrentGameInfo):  #로비티어평균
    if not CurrentGameInfo or 'participants' not in CurrentGameInfo:
        return "계산 불가"
    
    total_score, player_count = 0, 0
    
   
    try:
        all_puuids = [p["puuid"] for p in CurrentGameInfo["participants"]]
    except (KeyError, IndexError):
        print("오류: 'puuid' 키가 존재하지 않거나 participants가 비어 있습니다.")
        return "계산 불가"

    for puuid in all_puuids:
        try:
            tier, rank, leaguePoints = get_league_info(puuid)
            score = convert_rank_to_score(tier, rank, leaguePoints)
            total_score += score
            player_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"플레이어 티어 조회 중 오류: {e}")
            time.sleep(1)
            
    if player_count > 0:
        average_score = round(total_score / player_count)
        avg_tier, avg_lp = convert_score_to_rank(average_score)
        return f"{avg_tier} {avg_lp}"
    return "계산 불가"

def get_lobby_average_score(CurrentGameInfo):  # 로비 티어 평균 '점수' 반환
    if not CurrentGameInfo or 'participants' not in CurrentGameInfo:
        return None
    
    total_score, player_count = 0, 0
    
    try:
        all_puuids = [p["puuid"] for p in CurrentGameInfo["participants"]]
    except (KeyError, IndexError):
        print("오류: 'puuid' 키가 존재하지 않거나 participants가 비어 있습니다.")
        return None

    for puuid in all_puuids:
        try:
            tier, rank, leaguePoints = get_league_info(puuid)
            score = convert_rank_to_score(tier, rank, leaguePoints)
            total_score += score
            player_count += 1
            time.sleep(1) # Riot API 정책 준수를 위한 딜레이
        except Exception as e:
            print(f"플레이어 티어 조회 중 오류: {e}")
            time.sleep(1)
            
    if player_count > 0:
        return round(total_score / player_count)
    return None

def calculate_performance_info(placement, average_lobby_score):
    #퍼포먼스 티어와 퍼포먼스 점수 지표 도입
    # 등수별 점수 보정치 (ELO 기반)
    placement_adjustments = {
        1: 300, 2: 200, 3: 100, 4: 50,
        5: -50, 6: -100, 7: -200, 8: -300
    }
    
    adjustment = placement_adjustments.get(placement, 0)
    performance_score = average_lobby_score + adjustment
    performance_tier, _ = convert_score_to_rank(performance_score)
    
    return performance_tier, performance_score

def predict_future_rank(current_tier_name, current_score, performance_score):
    # 티어 인덱스
    tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    tier_base_scores = {"IRON": 0, "BRONZE": 400, "SILVER": 800, "GOLD": 1200, "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400, "MASTER": 2800}

    score_delta = performance_score - current_score

    # 점수 변동이 거의 없을 경우
    if abs(score_delta) < 1:
        return "> 이번 게임은 현재 티어에 맞는 플레이를 수행했습니다."

    # 마스터 이상 티어는 강등도 없고 승급도 없어서 의미 X
    if current_tier_name in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return "> 마스터 이상 티어에서는 예측이 무의미합니다"
        
    # 긍정적 피드백 퍼포먼스 ::::::승급예측
    if score_delta > 0:
        try:
            current_tier_index = tier_order.index(current_tier_name)
            # 다음 티어가 존재할 경우
            if current_tier_index + 1 < len(tier_order):
                next_tier_name = tier_order[current_tier_index + 1]
                target_score = tier_base_scores.get(next_tier_name)
                
                if target_score is not None:
                    points_to_climb = target_score - current_score
                    games_needed = math.ceil(points_to_climb / score_delta)
                    if games_needed <= 50: # 최대 50판까지만 예측
                        return f"> 이대로 플레이한다면, 약 **{games_needed}**판 뒤 **{next_tier_name} IV** 티어에 도달합니다"
                    else:
                        return "> 플레이스타일이 완벽합니다 "
        except (ValueError, IndexError):
            return "" # 예외 발생 시 빈 문자열 반환
            
    # 부정적 퍼포먼스: 강등 예측
    else:
        target_score = tier_base_scores.get(current_tier_name)
        if target_score is not None:
            points_to_drop = current_score - target_score
            # 이미 4티어 0점 근처가 아니면서, 강등 위험이 있을 때만 메시지 표시
            if points_to_drop > 0:
                games_needed = math.ceil(points_to_drop / abs(score_delta))
                if games_needed <= 50: # 최대 50판까지만 예측
                    return f"> 이런 플레이가 반복되면, 약 **{games_needed}**판 뒤 **{current_tier_name} IV**로 강등됩니다. "
                else:
                    return "> 플레이스타일 변경이 필요합니다. "
    return "" # 기본적으로 빈 문자열 반환


def check_for_new_game(puuid):       # 새계임시작탐지
    url = f"https://kr.api.riotgames.com/lol/spectator/tft/v5/active-games/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200: return response.json()
    return None

def get_match_details(match_id):            # 게임종료후 디테일
    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    for _ in range(15):
        response = requests.get(url, headers=headers)
        if response.status_code == 200: return response.json()
        time.sleep(30)
    return None
def calculate_win_probability_and_rank(my_puuid, CurrentGameInfo):  #내점수 로비평균점수 괴리로 승리확률과 예상등수
    if not CurrentGameInfo or "participants" not in CurrentGameInfo:
        return "계산 불가", "계산 불가"

    try:
        all_puuids = [p["puuid"] for p in CurrentGameInfo["participants"]]
    except (KeyError, IndexError):
        print("오류: 'puuid' 키가 존재하지 않거나 participants가 비어 있습니다.")
        return "계산 불가", "계산 불가"

    total_score, player_count = 0, 0
    my_score = None

    for puuid in all_puuids:
        try:
            tier, rank, leaguePoints = get_league_info(puuid)
            score = convert_rank_to_score(tier, rank, leaguePoints)

            if puuid == my_puuid:
                my_score = score

            total_score += score
            player_count += 1
            time.sleep(1)

        except Exception as e:
            print(f"플레이어 티어 조회 중 오류: {e}")
            time.sleep(1)

    if player_count == 0 or my_score is None:
        return "계산 불가", "계산 불가"

    avg_score = total_score / player_count

    # Elo Rating 사용 승률 가중치
    win_prob = 1 / (1 + math.pow(10, (avg_score - my_score) / 400))       # 가중치 400
    win_prob_percent = round(win_prob * 100, 2)

    # 1에서8사이 등수예상
    expected_ran = 1 + (player_count - 1) * (1 - win_prob)
    expected_rank = round(expected_ran)

    return win_prob_percent, expected_rank
    
def get_last_match_id(puuid): # 마지막매치호출
    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count=1"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        return response.json()[0]
    return None
  
#
def analyze_lobby_decks(current_game_info, my_puuid): # 로비 이전 덱 분석
    """현재 로비에 있는 다른 플레이어들의 직전 게임 덱을 분석하여 조언을 반환합니다."""
    if not current_game_info or 'participants' not in current_game_info:
        return ""

    other_players_puuids = [p['puuid'] for p in current_game_info['participants'] if p['puuid'] != my_puuid]
    
    # 순방유저덱세기
    top_placer_traits = collections.Counter()
    print("로비 분석 시작...")

    for i, puuid in enumerate(other_players_puuids):
        print(f"({i+1}/{len(other_players_puuids)}) 다른 플레이어의 이전 게임 분석 중...")
        last_match_id = get_last_match_id(puuid)
        time.sleep(1.2)  # 딜레이

        if not last_match_id:
            continue

        match_details = get_match_details(last_match_id)
        time.sleep(1.2)  # 딜레이

        if not match_details:
            continue
            
        participant_info = next((p for p in match_details['info']['participants'] if p.get('puuid') == puuid), None)
        
        if participant_info and participant_info['placement'] <= 8:
            # 순방시 특성 (style > 2, 즉 골드 이상)을 집계
            for trait in participant_info['traits']:
                if trait['style'] > 2 and trait['num_units'] > 2:
                    korean_name = trait_translations.get(trait['name'], trait['name'])
                    top_placer_traits[korean_name] += 1
    
    if not top_placer_traits:
        return "\n> 로비 유저들의 이전 덱 정보를 분석할 수 없었습니다."

    advice_message = "\n\n**로비 유저 최근 순방 덱**\n"
 
    for trait_name, count in top_placer_traits.most_common():
        # 사용 횟수(count)가 2 이상인 경우에만 메시지에 추가합니다.
        if count >= 2:
            advice_message += f"> **{trait_name}**: {count}명 사용\n"
            
    advice_message += "*겹칠 확률이 높은 덱입니다. 해당 덱을 후순위 고려해야 합니다.*"
    
    print("로비 분석 완료.")
    return advice_message
   # ================
# ===================================================
def analyze_and_summarize(match_data, puuid, old_lp=None, expected_rank=None, game_id=None, lobby_avg_score=None, current_score=None): # 분석 요약 oldLP 없으면 LP 증감표시하지않기
    if not match_data: return "게임 데이터를 분석할 수 없습니다."
    info = match_data.get('info', {})
    my_participant = next((p for p in info.get('participants', []) if p.get('puuid') == puuid), None)
    if not my_participant: return "참가자 정보를 찾을 수 없습니다."

    placement = my_participant['placement']
    _, summoner_id = get_player_ids() # 현재티어조회용 서머너ID
    new_tier, new_rank, new_lp = get_league_info(summoner_id)

    lp_change_str = ""
    if old_lp:
        old_score = convert_rank_to_score(old_lp[0], old_lp[1], old_lp[2])
        new_score = convert_rank_to_score(new_tier, new_rank, new_lp)
        lp_change = new_score - old_score
        lp_change_str = f"> 포인트 증감: **{lp_change:+} LP**\n"

    #연승연패---------------------------------

    streak_data = load_streak_data()
    is_top4 = placement <= 4
    if is_top4:
        if streak_data['streak_type'] == 'Top4': streak_data['streak_count'] += 1
        else: streak_data.update({'streak_type': 'Top4', 'streak_count': 1})
        streak_message = f"**{streak_data['streak_count']}연속 순방**"
    else:
        if streak_data['streak_type'] == 'Bottom4': streak_data['streak_count'] += 1
        else: streak_data.update({'streak_type': 'Bottom4', 'streak_count': 1})
        streak_message = f"**{streak_data['streak_count']}연속 순방 실패**"
    save_streak_data(streak_data)
    #특이점---------------------------

    special_notes = [streak_message]
    three_star_unit = next((u for u in my_participant['units'] if u['rarity'] >= 2 and u['tier'] == 3), None)
    if three_star_unit:
        unit_name = '_'.join(three_star_unit['character_id'].split('_')[1:])
        special_notes.append(f" **{unit_name} 3성**")
    for trait in my_participant['traits']:
     
        english_name = trait['name']
    
   
        korean_name = trait_translations.get(english_name, english_name)

        if  trait['style'] == 4:
            special_notes.append(f" **{trait['num_units']}{korean_name} **")
        elif trait['style'] == 5:
            special_notes.append(f" **프리즘 {trait['num_units']}{korean_name} !!!!!!!!!!!!!!!!!!!!**")
    if my_participant['players_eliminated'] >= 3:
        special_notes.append(f" **{my_participant['players_eliminated']}명 탈락시킴**")
    if my_participant['level'] == 9:
        special_notes.append(" **9레벨 달성**")
    elif my_participant['level'] >= 10:
        special_notes.append(" **10레벨 달성**")
    if my_participant['gold_left'] >= 40 and placement <= 4:
        special_notes.append(f" **{my_participant['gold_left']}골드 보유 순방**")

    notes_str = ", ".join(special_notes) if special_notes else "특별한 기록 없음"
    notes_str = ", ".join(special_notes) if special_notes else "특별한 기록 없음"
    rank_comparison_str = ""
    if expected_rank:
        rank_comparison_str = f"> 예상: **{expected_rank}등** | 실제: **{placement}등**\n"

    performance_str = ""
    prediction_str = ""                     # 예측 메시지
    if lobby_avg_score is not None:
                # 퍼포먼스 티어, 퍼포먼스점수
        performance_tier, performance_score = calculate_performance_info(placement, lobby_avg_score)
        performance_str = f"> 이번 게임 : **{performance_tier}** 수준의 플레이\n"

                                                         # current_score가 있으면 미래 티어 예측
        if current_score is not None:
                            # old_lp[0]은 게임 시작 전 티어 이름 "다이아,골드 등"
            prediction_str = predict_future_rank(old_lp[0], current_score, performance_score)

    message = (
        f"**{PLAYER_NAME}** 님의 매치 결과입니다. (게임 ID: {game_id})\n"
        f"{rank_comparison_str}"
        f"{lp_change_str}"
        f"> 현재 티어: **{new_tier} {new_rank} {new_lp} LP**\n"
        f"{performance_str}"
        f"> 특이점: {notes_str}\n\n"
        f"{prediction_str}" 
    )
    return message

def send_discord_message(message):
    payload = {"content": message, "username": "문대환 엿보기"}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

# ---------------------------
                                                 #본체
# ------------------------------------------------------------------
if __name__ == "__main__":
    player_puuid, player_summoner_id = get_player_ids()
    if not player_puuid or not player_summoner_id:
        print("플레이어 ID를 얻지 못해 프로그램을 종료합니다.")
    else:
        last_known_game_id = None
        last_summarized_match_id = None  # 마지막으로 요약한 게임 ID를 추적
        while True:
            current_game_info = check_for_new_game(player_puuid)
            if current_game_info and current_game_info['gameId'] != last_known_game_id:
                game_id = current_game_info['gameId']
                match_id_str = f"KR_{game_id}" # game_id 저장
                last_known_game_id = game_id

                current_tier, current_rank, current_lp = get_league_info(player_summoner_id)
                current_score = convert_rank_to_score(current_tier, current_rank, current_lp)
                lobby_avg_tier_str = get_lobby_average_tier(current_game_info)
                lobby_avg_score = get_lobby_average_score(current_game_info) 
                win_prob_percent, expected_rank = calculate_win_probability_and_rank(player_puuid, current_game_info) # expected_rank 저장
                
                lobby_analysis_message = analyze_lobby_decks(current_game_info, player_puuid)
           
                match_detected_message = (
                    f"**{PLAYER_NAME}** 님의 매칭이 감지되었습니다. (게임 ID: {match_id_str})\n" # 게임 ID 추가
                    f"> 현재 티어: **{current_tier} {current_rank} {current_lp} LP**\n"
                    f"> 로비 평균: **{lobby_avg_tier_str}**\n"
                    f"> 순방 확률: **{win_prob_percent}%**\n"
                    f"> 예상 등수: **{expected_rank}등**"
                    f"{lobby_analysis_message}" 
                )
                send_discord_message(match_detected_message)
                
                while check_for_new_game(player_puuid):
                    time.sleep(10)
                    
                match_details = get_match_details(f"KR_{game_id}")
                # OLDLP 게임종료후요약문
                summary_message = analyze_and_summarize(
                    match_details,
                    player_puuid,
                    old_lp=(current_tier, current_rank, current_lp),
                    expected_rank=expected_rank, # 예상 등수 전달
                    game_id=match_id_str # 게임 ID 전달
                )
                send_discord_message(summary_message)
                last_summarized_match_id = f"KR_{game_id}" # 요약 게임 ID저장

            else:
                # 게임중이아닐때만실행용
                latest_match_id = get_last_match_id(player_puuid)
                if latest_match_id and latest_match_id != last_summarized_match_id:
                    # 가장최근게임인데 호출한적없음
                    print(f"새로운 과거 게임 발견: {latest_match_id}")
                    match_details = get_match_details(latest_match_id)
                    if match_details:
                       # 'oldLp없을떄요약 함수 호출
                       summary_message = analyze_and_summarize(match_details, player_puuid)
                       send_discord_message(summary_message)
                       last_summarized_match_id = latest_match_id # 요약된 게임 ID기록

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] 게임중이 아니거나 인식 불가 - 10초 후 재탐색")
                time.sleep(10)