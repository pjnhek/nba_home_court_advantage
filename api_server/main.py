import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from server.get_nba_attendance_v2 import *
from server.seatgeek_api_data import *
from server.get_game_data import *
from server.async_get_game_id import *
from server.get_game_id_api_mod import *
from server.define_variables import *
from google.oauth2 import service_account
from google.cloud import storage

app = FastAPI()

class GcsStringUpload(BaseModel):
    service_account_key: str
    project_id: str
    bucket_name: str
    file_name: str
    data: str


@app.get("/")
def root():
    return {"Hi, Welcome to our NBA Data Scraper API! "
            "Read the docs and submit a request for the data you want."}


@app.get("/retrieve_nba_attendance_data_as_json_file")
def get_nba_attendance_data_as_json(crontab = False):
    '''
    Gets NBA attendance data and returns a json. Saves
    json into GCS bucket as well.
    '''
    team_dict = create_team_dictionary_from_web()
    json_response = JSONResponse(
        content=team_dict,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=nba_attendance_data.json"})
    try:
        gcs_info = {"service_account_key": service_account_file_path,
                    "project_id": project_id,
                    "bucket_name": bucket_name,
                    "file_name": "nba_attendance_data.json",
                    "data": json.dumps(team_dict)}
        save_to_gcs(GcsStringUpload(**gcs_info))
    except Exception as e:
        print("GCS upload failed:", e)
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")
    if crontab:
        return None
    return json_response
    

@app.get("/retrieve_seatgeek_api_data_as_json_file")
def get_seatgeek_api_data(crontab = False):
    '''
    Gets team popularity info from Seatgeek API
    and returns a map as a json. Saves file
    into GCS bucket as well.
    '''
    try:
        data = call_seatgeek_api()
        team_popularity_map = create_team_popularity_map(data)
    except Exception as e:
        print("SeatGeek API Error, "
              "check .env variables and authentication with SeatGeek.")
        raise HTTPException(status_code=500,
                            detail=f"Something went wrong: {str(e)}")
    json_response = JSONResponse(
        content=team_popularity_map,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=seatgeek_api_data.json"})
    try:
        gcs_info = {"service_account_key": service_account_file_path,
                    "project_id": project_id,
                    "bucket_name": bucket_name,
                    "file_name": "seatgeek_api_data.json",
                    "data": json.dumps(team_popularity_map)}
        save_to_gcs(GcsStringUpload(**gcs_info))
    except Exception as e:
        print("GCS upload failed:", str(e))
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")
    if crontab:
        return None
    return json_response

@app.get("/retrieve_all_nba_game_data_as_csv")
def get_nba_game_data_csv(crontab: bool = False):
    """
    Fetches all NBA game data and uploads CSVs to GCS directly.
    """
    try:
        years = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18",
                 "2018-19", "2019-20", "2020-21", "2021-22", "2022-23",
                 "2023-24"]
        home_df, away_df, _, _ = get_useful_stats(years, name_to_id, save=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {e}")

    try:
        gcs_info_home = {
            "service_account_key": service_account_file_path,
            "project_id": project_id,
            "bucket_name": bucket_name,
            "file_name": "all_nba_game_data_home.csv",
            "data": home_df.to_csv(index=False)
        }
        save_to_gcs(GcsStringUpload(**gcs_info_home))

        gcs_info_away = {
            "service_account_key": service_account_file_path,
            "project_id": project_id,
            "bucket_name": bucket_name,
            "file_name": "all_nba_game_data_away.csv",
            "data": away_df.to_csv(index=False)
        }
        save_to_gcs(GcsStringUpload(**gcs_info_away))
    except Exception as e:
        print("GCS upload failed:", str(e))
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")

    if crontab:
        return None

    return {
        "home_csv": "all_nba_game_data_home.csv",
        "away_csv": "all_nba_game_data_away.csv",
        "message": f"Uploaded {len(home_df)} home games and {len(away_df)} away games to GCS"
    }

    
@app.get("/retrieve_nba_game_ids_as_json_file")
def get_game_ids(crontab = False):
    '''
    Gets NBA game ids and returns a json. Saves
    json into GCS bucket as well.
    '''
    try:
        team_dict = create_team_dictionary_from_web()
        combined_games_id_dict = get_game_id_from_json(json.dumps(team_dict), name_to_id)
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Something went wrong: {str(e)}")
    json_response = JSONResponse(
            content=combined_games_id_dict,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=get_game_ids.json"})
    try:
        gcs_info = {"service_account_key": service_account_file_path,
                    "project_id": project_id,
                    "bucket_name": bucket_name,
                    "file_name": "get_game_ids.json",
                    "data": json.dumps(combined_games_id_dict)}
        save_to_gcs(GcsStringUpload(**gcs_info))
    except Exception as e:
        print("GCS upload failed:", str(e))
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")
    if crontab:
        return None
    return json_response

    
def create_team_dictionary_from_web():
    '''
    Creates a dictionary mapping teams to their attendance data
    from basketball-reference.
    '''
    try:
        df_scraped = scrape_nba_attendance_data()
        df_cleaned = clean_nba_attendance_data(df_scraped)
        team_dict = create_nba_team_dictionary(df_cleaned)
    except Exception as e:
        print("Scrape Failed! Error: " + str(e))
        raise HTTPException(status_code=500, detail=
                            f"Something went wrong: {str(e)}")
    return team_dict


def save_to_gcs(gcs_upload_param: GcsStringUpload):
    """
    Access the bucket with service_account_key, and upload the object(blob)
    the the storage. Code adapted from MSDS691 class.
    """
    credentials = service_account.Credentials.\
        from_service_account_file(gcs_upload_param.service_account_key)
    client = storage.Client(project=gcs_upload_param.project_id,
                            credentials=credentials)
    bucket = client.bucket(gcs_upload_param.bucket_name)
    file = bucket.blob(gcs_upload_param.file_name)
    blob_data = gcs_upload_param.data
    file.upload_from_string(blob_data,
                            content_type="application/json")
    return {
        "message": f"file {gcs_upload_param.file_name} has been uploaded "
                   f"to {gcs_upload_param.bucket_name} successfully."
        }
