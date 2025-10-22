import io
import pandas as pd
import requests
import time

months = ["october","november","december","january","february","march","april","may","june"]

all_years_df = []

for year in range(2014, 2025):
    all_months_df = []
    for month in months:
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html"
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"Request failed for {url}: {e}")
            continue

        time.sleep(10)

        if resp.status_code == 404:
            print(f"Skipping {year} {month}: 404")
            continue
        if resp.status_code != 200:
            print(f"Skipping {year} {month}: status {resp.status_code}")
            continue

        try:
            tables = pd.read_html(io.StringIO(resp.text), attrs={"id": "schedule"})
            if not tables:
                print(f"No schedule table for {year} {month}")
                continue
            dfm = tables[0]
        except ValueError:
            print(f"read_html failed for {year} {month}")
            continue
        dfm = dfm[dfm["Date"] != "Date"]
        dfm = dfm[dfm["Date"] != "Playoffs"]

        for c in ["PTS", "PTS.1", "Attend."]:
            if c in dfm.columns:
                dfm[c] = pd.to_numeric(dfm[c], errors="coerce")

        dfm["Date"] = pd.to_datetime(dfm["Date"], errors="coerce")
        dfm = dfm.dropna(subset=["Date"])

        dfm = dfm.dropna(subset=["PTS", "PTS.1"])

        keep_cols = ["Date", "Home/Neutral", "PTS.1", "PTS", "Attend."]
        existing_keep = [c for c in keep_cols if c in dfm.columns]
        dfm = dfm[existing_keep].copy()

        dfm["Home_Win"] = dfm["PTS.1"] > dfm["PTS"]

        dfm["Date"] = dfm["Date"].dt.strftime("%m-%d-%Y")

        all_months_df.append(dfm)

    if all_months_df:
        df_single_year = pd.concat(all_months_df, ignore_index=True)
        all_years_df.append(df_single_year)

df = pd.concat(all_years_df, ignore_index=True)

nba_team_dict = {}
for _, row in df.iterrows():
    team = row["Home/Neutral"]
    date = row["Date"]
    attend = int(row["Attend."]) if pd.notna(row.get("Attend.", None)) else None
    pts_home = int(row["PTS.1"]) if pd.notna(row.get("PTS.1", None)) else None
    home_win = bool(row["Home_Win"]) if pd.notna(row.get("Home_Win", None)) else None

    nba_team_dict.setdefault(team, {})
    nba_team_dict[team][date] = {
        "Attendance": attend,
        "Points": pts_home,
        "HomeWin": home_win,
    }

print(nba_team_dict)
