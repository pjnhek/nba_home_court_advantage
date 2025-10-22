import json
import asyncio
from nba_api.stats.endpoints import leaguegamefinder
from tqdm.asyncio import tqdm_asyncio


name_to_id = {
    'Atlanta Hawks': 1610612737,
    'Boston Celtics': 1610612738,
    'Cleveland Cavaliers': 1610612739,
    'New Orleans Pelicans': 1610612740,
    'Chicago Bulls': 1610612741,
    'Dallas Mavericks': 1610612742,
    'Denver Nuggets': 1610612743,
    'Golden State Warriors': 1610612744,
    'Houston Rockets': 1610612745,
    'Los Angeles Clippers': 1610612746,
    'Los Angeles Lakers': 1610612747,
    'Miami Heat': 1610612748,
    'Milwaukee Bucks': 1610612749,
    'Minnesota Timberwolves': 1610612750,
    'Brooklyn Nets': 1610612751,
    'New York Knicks': 1610612752,
    'Orlando Magic': 1610612753,
    'Indiana Pacers': 1610612754,
    'Philadelphia 76ers': 1610612755,
    'Phoenix Suns': 1610612756,
    'Portland Trail Blazers': 1610612757,
    'Sacramento Kings': 1610612758,
    'San Antonio Spurs': 1610612759,
    'Oklahoma City Thunder': 1610612760,
    'Toronto Raptors': 1610612761,
    'Utah Jazz': 1610612762,
    'Memphis Grizzlies': 1610612763,
    'Washington Wizards': 1610612764,
    'Detroit Pistons': 1610612765,
    'Charlotte Hornets': 1610612766,
    'Charlotte Bobcats': 1610612766
}

def get_team_games_lookup(team_id):
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id)
    games_df = gamefinder.get_data_frames()[0]
    return dict(zip(games_df['GAME_DATE'], games_df['GAME_ID']))


async def fetch_team_lookup(team_name, team_id, semaphore, retries=3):
    async with semaphore:
        for attempt in range(retries):
            try:
                return team_id, await asyncio.to_thread(get_team_games_lookup, team_id)
            except Exception as e:
                print(f"Error fetching {team_name} (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    print(f"Failed to fetch {team_name} after {retries} attempts")
                    return team_id, {}

async def get_game_id_from_json_async(json_filepath: str, name_to_id_dict: dict):
    print("Fetching game lookups for all teams...")
    semaphore = asyncio.Semaphore(5)

    tasks = [
        fetch_team_lookup(team_name, team_id, semaphore)
        for team_name, team_id in name_to_id_dict.items()
    ]

    game_logs_list = await tqdm_asyncio.gather(*tasks, desc="Fetching team games")
    game_logs = dict(game_logs_list)

    print("Loading existing JSON data")
    with open(json_filepath, "r", encoding="utf-8") as f:
        games_data = json.load(f)

    print("Adding GameIDs to entries")
    for team_name, games in games_data.items():
        team_id = name_to_id_dict.get(team_name)
        if not team_id:
            print(f"Skipping unknown team: {team_name}")
            continue

        team_lookup = game_logs.get(team_id, {})
        for game in games:
            game_date = game['Date']
            game_id = team_lookup.get(game_date)
            if game_id:
                game['GameID'] = str(game_id)
            else:
                print(f"No GameID found for {team_name} on {game_date}")

    print("Saving updated JSON")
    with open("games_with_gameids.json", "w", encoding="utf-8") as f:
        json.dump(games_data, f, indent=2, ensure_ascii=False)
    print("Done! Updated data saved to 'games_with_gameids.json'")

if __name__ == "__main__":
    asyncio.run(get_game_id_from_json_async("nba_attendance_data.json", name_to_id))