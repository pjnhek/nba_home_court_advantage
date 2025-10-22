import io
import json
import pandas as pd


all_dfs = []
import pandas as pd

all_dfs = []
for year in range(2014, 2025):
    url = f"https://www.espn.com/nba/attendance/_/year/{year}"

    df = pd.read_html(url, header=1)[0]
    df = df[df["RK"] != "RK"]
    df["Year"] = year
    all_dfs.append(df)

final_df = pd.concat(all_dfs, ignore_index=True)

print(final_df.head())