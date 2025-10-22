import json
import http.client
from server.define_variables import *


def call_seatgeek_api() -> dict:
    ''' 
    Calls SeatGeek API with client+secret ID and 
    retrieves all available performer/event data.
    Returns data as dictionary.
    '''
    conn = http.client.HTTPSConnection("api.seatgeek.com")
    headers = {'accept': "application/json"}
    conn.request("GET", F"/2/events?client_id={client_id}&client_secret={secret_id}&taxonomies.id=1030100", headers=headers)
    res = conn.getresponse()
    data = res.read()
    parsed_data = json.loads(data.decode("utf-8"))
    return parsed_data

def create_team_popularity_map(api_data: dict) -> dict:
    '''
    Creates a dictionary mapping each NBA Team to
    its popularity score.
    '''
    from collections import defaultdict
    team_popularity = defaultdict(list)
    for event in api_data["events"]:
        for performer in event.get("performers", []):
            team_popularity[performer["name"]].append(performer["popularity"])
    team_popularity = dict(team_popularity)
    team_popularity.pop("Hapoel Jerusalem B.C.", None)
    team_popularity.pop("Guangzhou Loong Lions", None)
    for team, popularity in team_popularity.items():
        if len(popularity) > 1:
            avg_popularity = sum(popularity) / len(popularity)
            team_popularity[team] = int(avg_popularity)
        else:
            team_popularity[team] = int(popularity[0])
    sorted_team_popularity = dict(sorted(team_popularity.items(),
                                  key=lambda x: x[1], reverse=True))
    return sorted_team_popularity

def create_team_popularity_json(team_dict: dict) -> None:
    '''
    Creates a json file from the popularity map.
    '''
    with open("nba_team_popularity_data.json", 'w') as f:
        json.dump(team_dict,f, indent=4)