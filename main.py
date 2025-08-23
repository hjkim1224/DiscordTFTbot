import time
import datetime
from config import PLAYER_NAME, PLAYER_TAG
import riot_api
import game_analyzer
from discord_webhook import send_discord_message

def main():
    player_puuid, _ = riot_api.get_player_ids(PLAYER_NAME, PLAYER_TAG)
    if not player_puuid:
        print("플레이어 ID를 얻지 못해 프로그램을 종료합니다.")
        return

    last_known_game_id = None
    print("TFT 전적 자동 분석 시작...")
    
    while True:
        current_game_info = riot_api.check_for_new_game(player_puuid)
        
        # 새 게임이 감지되었을 때
        if current_game_info and current_game_info.get('gameId') != last_known_game_id:
            game_id = current_game_info['gameId']
            match_id_str = f"KR_{game_id}"
            last_known_game_id = game_id
            print(f"새로운 게임 감지: {match_id_str}")

            # 게임 시작 정보 가져오기
            old_tier, old_rank, old_lp = riot_api.get_league_info(player_puuid)
            current_score = game_analyzer.convert_rank_to_score(old_tier, old_rank, old_lp)
            lobby_avg_score = game_analyzer.get_lobby_average_score(current_game_info)
            avg_tier_str, score = game_analyzer.convert_score_to_rank(lobby_avg_score) if lobby_avg_score else ("계산 불가", "")
            win_prob, expected_rank = game_analyzer.calculate_win_probability_and_rank(player_puuid, current_game_info)
            
            # 로비 분석 및 시작 메시지 전송
            lobby_analysis_msg = game_analyzer.analyze_lobby_decks(current_game_info, player_puuid)
            start_message = (
                f"**{PLAYER_NAME}** 님의 매칭이 감지되었습니다. (게임 ID: {match_id_str})\n"
                f"> 현재 티어: **{old_tier} {old_rank} {old_lp} LP**\n"
                f"> 로비 평균: **{avg_tier_str} {score}**\n"
                f"> 순방 확률: **{win_prob}%**\n"
                f"> 예상 등수: **{expected_rank}등**"
                f"{lobby_analysis_msg}"
            )
            send_discord_message(start_message)

            # 게임이 끝날 때까지 대기
            while riot_api.check_for_new_game(player_puuid):
                print("게임 진행 중... 30초 후 다시 확인합니다.")
                time.sleep(30)
            
            print("게임 종료. 결과 분석을 시작합니다.")
            
            # 게임 결과 분석 및 요약 메시지 전송
            match_details = riot_api.get_match_details(match_id_str)
            summary_message = game_analyzer.analyze_and_summarize(
                match_details,
                player_puuid,
                old_lp_info=(old_tier, old_rank, old_lp),
                expected_rank=expected_rank,
                game_id=match_id_str,
                lobby_avg_score=lobby_avg_score,
                current_score=current_score
            )
            send_discord_message(summary_message)
            print("결과 분석 및 전송 완료.")

        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] 게임을 찾을 수 없습니다. 15초 후 다시 탐색합니다.")
            time.sleep(15)

if __name__ == "__main__":
    main()