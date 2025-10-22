import json
import pandas as pd
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius (km)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


arena_csv = Path("stadiums.csv")
arena_df = pd.read_csv(arena_csv)

arena_df["Team"] = arena_df["Team"].str.strip()
arena_lookup = arena_df.set_index("Team")[["Latitude","Longitude"]].to_dict("index")

json_path = Path("nba_team_data_2013_2024_no_covid_years_.json")
with open(json_path, "r") as f:
    team_data = json.load(f)

new_data = {}
for home_team, games in team_data.items():
    home_lat = arena_lookup[home_team]["Latitude"]
    home_lon = arena_lookup[home_team]["Longitude"]

    updated_games = []
    for g in games:
        away_team = g.get("AwayTeam") 
        if away_team in arena_lookup:
            away_lat = arena_lookup[away_team]["Latitude"]
            away_lon = arena_lookup[away_team]["Longitude"]
            distance_km = haversine(home_lat, home_lon, away_lat, away_lon)
        else:
            distance_km = None

        g["away_team_travelled"] = distance_km
        updated_games.append(g)
    new_data[home_team] = updated_games


out_path = Path("nba_team_data_with_travel.json")
with open(out_path, "w") as f:
    json.dump(new_data, f, indent=2)

print(f"✅ New file saved: {out_path}")