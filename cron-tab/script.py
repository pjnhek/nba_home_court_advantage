import requests

API_BASE = "http://api-server:8000"
ENDPOINTS = [
    "/retrieve_nba_attendance_data_as_json_file",
    "/retrieve_seatgeek_api_data_as_json_file",
    "/retrieve_nba_game_ids_as_json_file",
    "/retrieve_all_nba_game_data_as_json_file",
]

def run_cron_jobs():
    for endpoint in ENDPOINTS:
        try:
            resp = requests.get(f"{API_BASE}{endpoint}")
            resp.raise_for_status()
            print(f"Success: {endpoint} ({resp.status_code})")
        except Exception as e:
            print(f"Failed: {endpoint} -> {e}")

if __name__ == "__main__":
    run_cron_jobs()
