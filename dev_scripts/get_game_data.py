from nba_api.stats.endpoints import teamgamelogs
import pandas as pd
import time
from tqdm import tqdm  


useful_stats = ['TEAM_ID','SEASON_WINRATE', 'HOME_WINRATE', 'GAME_ID','FGM','FGA','FG_PCT','FG3M','FG3A','FG3_PCT','FTM','FTA','FT_PCT',
                'OREB','DREB','REB','AST','STL','BLK','TOV','PF', 'EFGP','TOVP','FTR', 'OPP']

name_to_id = {
    'Atlanta Hawks': 1610612737,
    'Boston Celtics': 1610612738,
    'Brooklyn Nets': 1610612751,
    'Charlotte Hornets': 1610612766,
    'Chicago Bulls': 1610612741,
    'Cleveland Cavaliers': 1610612739,
    'Dallas Mavericks': 1610612742,
    'Denver Nuggets': 1610612743,
    'Detroit Pistons': 1610612765,
    'Golden State Warriors': 1610612744,
    'Houston Rockets': 1610612745,
    'Indiana Pacers': 1610612754,
    'Los Angeles Clippers': 1610612746,
    'Los Angeles Lakers': 1610612747,
    'Memphis Grizzlies': 1610612763,
    'Miami Heat': 1610612748,
    'Milwaukee Bucks': 1610612749,
    'Minnesota Timberwolves': 1610612750,
    'New Orleans Pelicans': 1610612740,
    'New York Knicks': 1610612752,
    'Oklahoma City Thunder': 1610612760,
    'Orlando Magic': 1610612753,
    'Philadelphia 76ers': 1610612755,
    'Phoenix Suns': 1610612756,
    'Portland Trail Blazers': 1610612757,
    'Sacramento Kings': 1610612758,
    'San Antonio Spurs': 1610612759,
    'Toronto Raptors': 1610612761,
    'Utah Jazz': 1610612762,
    'Washington Wizards': 1610612764
}

def get_team_game_logs(team_id, season="2020-21", season_type="Regular Season"):
    """
    Get all home games for a specific team in a season
    """
    try:
        game_logs = teamgamelogs.TeamGameLogs(
        team_id_nullable=team_id,
        season_nullable=season,
        season_type_nullable=season_type
    )

        df = game_logs.get_data_frames()[0]
        df['SEASON_WINRATE'] = round((df['WL']=='W').mean(), 3)
        df['WIN'] = (df['WL']=='W').astype('int64')
        df['HOME'] = df['MATCHUP'].str.contains('vs.', na=False)
        df["OPP"] = df["MATCHUP"].str[-3:]
        df['EFGP'] = (df['FGM'] + 0.5 * df['FG3M']) / df['FGA']
        df['TOVP'] = df['TOV'] / (df['FGA'] + 0.44 * df['FTA'] + df['TOV'])
        df['FTR'] = df['FTA'] / df['FGA']
        home = df[df['HOME']].copy()
        home['HOME_WINRATE'] = round(home['WIN'].mean(), 3)
        away = df[~df['HOME']].copy()
        away['AWAY_WINRATE'] = round(away['WIN'].mean(), 3)
        return home, away

        
    except Exception as e:
        print(f"Error fetching data for team {team_id} season {season}: {e}")
        return None, None

def get_useful_stats(year_range:list, name_to_id_dict: dict, save=False) -> pd.DataFrame:
    home_df, away_df = [], []

    total_iterations = len(name_to_id_dict) * len(year_range)

    with tqdm(total=total_iterations, desc="Fetching NBA Game Logs") as pbar:
        for team_id in name_to_id_dict.values():
            for year in year_range:
                df1, df2 = get_team_game_logs(team_id, season=year)
                if df1 is not None and not df1.empty and df2 is not None and not df2.empty:
                    home_df.append(df1)
                    away_df.append(df2)
                time.sleep(.5)
                pbar.update(1)
    home = pd.concat(home_df, ignore_index=True)
    away = pd.concat(away_df, ignore_index=True)
    if save:
        home.to_csv("HOME_GAMES.csv", index=False)
        away.to_csv("AWAY_GAMES.csv", index=False)
        print(f"Saved {len(home)} total games to HOME_GAMES.csv")
        print(f"Saved {len(away)} total games to AWAY_GAMES.csv")
        return None
    else:
        return home_df, away_df

if __name__ == "__main__":
    years = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", 
         "2020-21", "2021-22", "2022-23", "2023-24"]
    get_useful_stats(years, name_to_id, save=True)
