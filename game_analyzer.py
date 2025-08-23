import time
import math
import collections
import riot_api
from data_manager import load_streak_data, save_streak_data, load_trait_translations
from config import PLAYER_NAME

trait_translations = load_trait_translations()

#랭크를 점수로 변환
def convert_rank_to_score(tier, rank, lp):
    tier_base_scores = {"IRON": 0, "BRONZE": 400, "SILVER": 800, "GOLD": 1200, "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400, "MASTER": 2800, "GRANDMASTER": 2800, "CHALLENGER": 2800}
    rank_scores = {"IV": 0, "III": 100, "II": 200, "I": 300}
    
    if tier == "Unranked": return 800
    
    base_score = tier_base_scores.get(tier, 0)
    if tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return base_score + lp
    else:
        rank_score = rank_scores.get(rank, 0)
        return base_score + rank_score + lp

#점수를 랭크로 변환
def convert_score_to_rank(score):
    if score >= 2800:
        score -= 2800
        if score >= riot_api.get_challenger_cutline():
            return "Challenger", f"{score} LP"
        elif score >= riot_api.get_grandmaster_cutline():
            return "GrandMaster", f"{score} LP"
        else:
            return "Master", f"{score} LP"
        
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

#로비 평균 티어 계산
def get_lobby_average_score(current_game_info):

    if not current_game_info or 'participants' not in current_game_info: return None
    
    total_score, player_count = 0, 0
    all_puuids = [p["puuid"] for p in current_game_info["participants"]]

    for puuid in all_puuids:
        try:
            tier, rank, lp = riot_api.get_league_info(puuid)
            score = convert_rank_to_score(tier, rank, lp)
            total_score += score
            player_count += 1
            time.sleep(1.2)  # API 속도 제한 준수
        except Exception as e:
            print(f"플레이어 티어 조회 중 오류: {e}")
            time.sleep(1.2)
        
    return round(total_score / player_count) if player_count > 0 else None

# 로비 티어와 등수 별 가중치로 퍼포먼수 점수 계산
def calculate_performance_info(placement, average_lobby_score):

    placement_adjustments = {1: 300, 2: 200, 3: 100, 4: 50, 5: -50, 6: -100, 7: -200, 8: -300}
    adjustment = placement_adjustments.get(placement, 0)
    performance_score = average_lobby_score + adjustment
    performance_tier, _ = convert_score_to_rank(performance_score)
    return performance_tier, performance_score

#현재 점수와 퍼포먼스 점수를 바탕으로 향후 티어 예측
def predict_future_rank(current_tier_name, current_score, performance_score):
    
    tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER"]
    tier_base_scores = {"BRONZE": 400, "SILVER": 800, "GOLD": 1200, "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400, "MASTER": 2800}
    
    score_delta = performance_score - current_score
    if abs(score_delta) < 1:
        return "이번 게임은 현재 티어에 맞는 플레이를 수행했습니다."
    if current_tier_name in ["MASTER", "GRANDMASTER", "CHALLENGER"]: 
        return "마스터 이상 티어에서는 예측이 무의미합니다."

    # 승급 예측
    if score_delta > 0:
        try:
            current_tier_index = tier_order.index(current_tier_name)
            if current_tier_index + 1 < len(tier_order):
                next_tier_name = tier_order[current_tier_index + 1]
                target_score = tier_base_scores.get(next_tier_name)
                points_to_climb = target_score - current_score
                games_needed = math.ceil(points_to_climb / score_delta)
                if 1 <= games_needed <= 50:
                    return f"> 이대로 플레이한다면, 약 **{games_needed}**판 뒤 **{next_tier_name} IV** 티어에 도달합니다."
        except (ValueError, IndexError): pass

    # 강등 예측
    else:
        target_score = tier_base_scores.get(current_tier_name)
        points_to_drop = current_score - target_score
        if points_to_drop > 0:
            games_needed = math.ceil(points_to_drop / abs(score_delta))
            if 1 <= games_needed <= 50:
                return f"> 이런 플레이가 반복되면, 약 **{games_needed}**판 뒤 강등될 수 있습니다."
    return ""

#로비 정보를 바탕으로 순방 확률과 예상 등수 계산
def calculate_win_probability_and_rank(my_puuid, current_game_info):

    if not current_game_info or "participants" not in current_game_info: return "계산 불가", "계산 불가"
    
    all_puuids = [p["puuid"] for p in current_game_info["participants"]]
    total_score, player_count, my_score = 0, 0, None

    for puuid in all_puuids:
        try:
            tier, rank, lp = riot_api.get_league_info(puuid)
            score = convert_rank_to_score(tier, rank, lp)
            if puuid == my_puuid: my_score = score
            total_score += score
            player_count += 1
            time.sleep(1.2)
        except Exception as e:
            print(f"플레이어 티어 조회 중 오류: {e}")
            time.sleep(1.2)

    if player_count == 0 or my_score is None: return "계산 불가", "계산 불가"

    avg_score = total_score / player_count
    win_prob = 1 / (1 + math.pow(10, (avg_score - my_score) / 400))
    expected_rank = round(1 + (player_count - 1) * (1 - win_prob))
    return f"{win_prob * 100:.2f}", expected_rank

#로비 플레이어의 직전 게임 덱을 분석한 후 겹칠 확률이 높은 덱 제공
def analyze_lobby_decks(current_game_info, my_puuid):

    if not current_game_info or 'participants' not in current_game_info: return ""

    other_players_puuids = [p['puuid'] for p in current_game_info['participants'] if p['puuid'] != my_puuid]
    top_placer_traits = collections.Counter()
    print("로비 분석 시작...")

    for i, puuid in enumerate(other_players_puuids, 1):
        print(f"({i}/{len(other_players_puuids)}) 다른 플레이어 분석 중...")
        last_match_id = riot_api.get_last_match_id(puuid)
        time.sleep(1.2)
        if not last_match_id: continue

        match_details = riot_api.get_match_details(last_match_id)
        time.sleep(1.2)
        if not match_details: continue
            
        participant_info = next((p for p in match_details['info']['participants'] if p.get('puuid') == puuid), None)
        
        if participant_info and participant_info['placement'] <= 4:
            for trait in participant_info.get('traits', []):
                if trait.get('style', 0) > 2 and trait.get('num_units', 0) > 1:
                    korean_name = trait_translations.get(trait['name'], trait['name'])
                    top_placer_traits[korean_name] += 1
    
    if not top_placer_traits: return "\n> 로비 유저들의 이전 덱 정보를 분석할 수 없었습니다."

    advice_message = "\n\n**로비 유저 최근 순방 덱**\n"
    for trait_name, count in top_placer_traits.most_common():
        if count >= 2:
            advice_message += f"> **{trait_name}**: {count}명 사용\n"
            
    if len(advice_message) > 30: # 메시지가 생성되었을 경우에만 꼬리말 추가
        advice_message += "*겹칠 확률이 높은 덱은 후순위로 고려하는 것이 좋습니다.*"
        return advice_message
    return ""

#게임 결과 분석 후 요약 메시지 생성
def analyze_and_summarize(match_data, puuid, old_lp_info=None, expected_rank=None, game_id=None, lobby_avg_score=None, current_score=None):
    
    if not match_data: return "게임 데이터를 분석할 수 없습니다."
    
    my_participant = next((p for p in match_data['info']['participants'] if p.get('puuid') == puuid), None)
    if not my_participant: return "참가자 정보를 찾을 수 없습니다."

    placement = my_participant['placement']
    new_tier, new_rank, new_lp = riot_api.get_league_info(puuid)

    lp_change_str = ""
    if old_lp_info:
        old_score = convert_rank_to_score(old_lp_info[0], old_lp_info[1], old_lp_info[2])
        new_score = convert_rank_to_score(new_tier, new_rank, new_lp)
        lp_change = new_score - old_score
        lp_change_str = f"> 포인트 증감: **{lp_change:+} LP**\n"

    # 연승/연패 기록
    streak_data = load_streak_data()
    current_result = 'Top4' if placement <= 4 else 'Bottom4'
    if streak_data['streak_type'] == current_result:
        streak_data['streak_count'] += 1
    else:
        streak_data['streak_type'] = current_result
        streak_data['streak_count'] = 1
    save_streak_data(streak_data)
    streak_message = f"**{streak_data['streak_count']}연속 {('순방' if current_result == 'Top4' else '순방 실패')}**"

    # 특이사항 기록
    special_notes = [streak_message]
    if any(u['tier'] == 3 for u in my_participant.get('units', [])): special_notes.append("**3성 유닛 보유**")
    for trait in my_participant.get('traits', []):
        if trait.get('style', 0) >= 4:
            korean_name = trait_translations.get(trait['name'], trait['name'])
            special_notes.append(f"**{korean_name} (프리즘/골드)**")
    if my_participant.get('players_eliminated', 0) >= 3: special_notes.append(f"**{my_participant['players_eliminated']}명 탈락시킴**")
    if my_participant.get('level', 0) >= 9: special_notes.append(f"**{my_participant['level']}레벨 달성**")

    # 메시지 조합
    rank_comparison_str = f"> 예상: **{expected_rank}등** | 실제: **{placement}등**\n" if expected_rank else ""
    performance_str, prediction_str = "", ""
    if lobby_avg_score is not None:
        performance_tier, performance_score = calculate_performance_info(placement, lobby_avg_score)
        performance_str = f"> 이번 게임 : **{performance_tier}** 수준의 플레이\n"
        if current_score and old_lp_info:
            prediction_str = predict_future_rank(old_lp_info[0], current_score, performance_score)

    message = (
        f"**{PLAYER_NAME}** 님의 매치 결과입니다. (게임 ID: {game_id})\n"
        f"{rank_comparison_str}"
        f"{lp_change_str}"
        f"> 현재 티어: **{new_tier} {new_rank} {new_lp} LP**\n"
        f"{performance_str}"
        f"> 특이점: {', '.join(special_notes)}\n\n"
        f"{prediction_str}" 
    )
    return message