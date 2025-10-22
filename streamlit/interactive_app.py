import json
from pathlib import Path
from google.oauth2 import service_account
from google.cloud import storage
import pandas as pd
import numpy as np
import streamlit as st
import statsmodels.formula.api as smf

from plotnine import (
    ggplot, aes, geom_point, geom_smooth, geom_col, geom_text,
    labs, theme_minimal, theme, scale_y_continuous, scale_size_continuous,
    element_text, geom_line, scale_x_continuous, scale_fill_manual,
    scale_color_brewer, scale_fill_brewer, element_rect, element_line
)
import io
import matplotlib.pyplot as plt

from mizani.formatters import percent_format
from define_variables import *

def retrieve_data_from_gcs(service_account_key: str,
                           project_id: str,
                           bucket_name: str,
                           file_name: str
                           ) -> dict:
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id,
                            credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    content = blob.download_as_text()
    return content


TEAM_META = {
    #Atlantic
    "Boston Celtics": {"Conference": "Eastern", "Division": "Atlantic"},
    "Brooklyn Nets": {"Conference": "Eastern", "Division": "Atlantic"},
    "New York Knicks": {"Conference": "Eastern", "Division": "Atlantic"},
    "Philadelphia 76ers": {"Conference": "Eastern", "Division": "Atlantic"},
    "Toronto Raptors": {"Conference": "Eastern", "Division": "Atlantic"},
    #Central
    "Chicago Bulls": {"Conference": "Eastern", "Division": "Central"},
    "Cleveland Cavaliers": {"Conference": "Eastern", "Division": "Central"},
    "Detroit Pistons": {"Conference": "Eastern", "Division": "Central"},
    "Indiana Pacers": {"Conference": "Eastern", "Division": "Central"},
    "Milwaukee Bucks": {"Conference": "Eastern", "Division": "Central"},
    #Southeast
    "Atlanta Hawks": {"Conference": "Eastern", "Division": "Southeast"},
    "Charlotte Hornets": {"Conference": "Eastern", "Division": "Southeast"},
    "Miami Heat": {"Conference": "Eastern", "Division": "Southeast"},
    "Orlando Magic": {"Conference": "Eastern", "Division": "Southeast"},
    "Washington Wizards": {"Conference": "Eastern", "Division": "Southeast"},
    #Northwest
    "Denver Nuggets": {"Conference": "Western", "Division": "Northwest"},
    "Minnesota Timberwolves": {"Conference": "Western", "Division": "Northwest"},
    "Oklahoma City Thunder": {"Conference": "Western", "Division": "Northwest"},
    "Portland Trail Blazers": {"Conference": "Western", "Division": "Northwest"},
    "Utah Jazz": {"Conference": "Western", "Division": "Northwest"},
    #Pacific
    "Golden State Warriors": {"Conference": "Western", "Division": "Pacific"},
    "Los Angeles Clippers": {"Conference": "Western", "Division": "Pacific"},
    "Los Angeles Lakers": {"Conference": "Western", "Division": "Pacific"},
    "Phoenix Suns": {"Conference": "Western", "Division": "Pacific"},
    "Sacramento Kings": {"Conference": "Western", "Division": "Pacific"},
    #Southwest
    "Dallas Mavericks": {"Conference": "Western", "Division": "Southwest"},
    "Houston Rockets": {"Conference": "Western", "Division": "Southwest"},
    "Memphis Grizzlies": {"Conference": "Western", "Division": "Southwest"},
    "New Orleans Pelicans": {"Conference": "Western", "Division": "Southwest"},
    "San Antonio Spurs": {"Conference": "Western", "Division": "Southwest"},
}

# Aliases
ALIASES = {
    "LA Clippers": "Los Angeles Clippers",
    "Charlotte Bobcats": "Charlotte Hornets",       # old → current
    "New Orleans Hornets": "New Orleans Pelicans",  # old → current
    # add any others you see in your JSON…
}

# Canonical map (canonical->canonical + alias->canonical)
TEAM_CANON_MAP = {**{t: t for t in TEAM_META.keys()}, **ALIASES}
def canonize(name: str) -> str:
    return TEAM_CANON_MAP.get(name, name)


@st.cache_data
def load_team_game_data(path: Path) -> pd.DataFrame:
    """
    JSON structure: { "Team A": [ {Date, Attendance, Points, HomeWin}, ... ], "Team B": [...] }
    Returns long DataFrame with columns: Team, Date, Attendance, Points, HomeWin
    """
    raw = json.loads(path)
    rows = []
    for team, games in raw.items():
        for g in games:
            # Some dates are strings like "2013-10-29"
            d = pd.to_datetime(g.get("Date"), errors="coerce")
            rows.append({
                "Team": team,
                "Date": d,
                "Attendance": g.get("Attendance"),
                "Points": g.get("Points"),
                "HomeWin": g.get("HomeWin")
            })
    df = pd.DataFrame(rows).dropna(subset=["Date"])
    # useful extras
    df["Season"] = df["Date"].dt.year.where(df["Date"].dt.month >= 7, df["Date"].dt.year - 1)
    return df

@st.cache_data
def load_popularity_data(path: Path) -> pd.DataFrame:
    """
    JSON structure: { "Team": score, ... }
    """
    raw = json.loads(path)
    df = pd.DataFrame(list(raw.items()), columns=["Team", "Popularity"])
    return df.sort_values("Popularity", ascending=False)


if __name__ == "__main__":

    TEAM_DATA_PATH = retrieve_data_from_gcs(service_account_file_path,
                                        project_id,
                                        bucket_name,
                                        'nba_attendance_data.json')
    POPULARITY_DATA_PATH = retrieve_data_from_gcs(service_account_file_path,
                                        project_id,
                                        bucket_name,
                                        'seatgeek_api_data.json')
    HOME_CSV = retrieve_data_from_gcs(service_account_file_path,
                                        project_id,
                                        bucket_name, 
                                        "all_nba_game_data_home.csv")
    
    
    AWAY_CSV = retrieve_data_from_gcs(service_account_file_path,
                                        project_id,
                                        bucket_name,
                                        "all_nba_game_data_away.csv")

    st.set_page_config(
        page_title="NBA Home Court Advantage Analysis",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    games_df = load_team_game_data(TEAM_DATA_PATH)
    pop_df   = load_popularity_data(POPULARITY_DATA_PATH)


    # Canonicalize team names
    games_df["TeamCanonical"] = games_df["Team"].map(canonize)

    # Add Conference/Division to games
    games_df["Conference"] = games_df["TeamCanonical"].map(lambda t: TEAM_META.get(t, {}).get("Conference"))
    games_df["Division"]   = games_df["TeamCanonical"].map(lambda t: TEAM_META.get(t, {}).get("Division"))

    # Canonicalize popularity for safer merges
    if "Team" in pop_df.columns:
        pop_df["TeamCanonical"] = pop_df["Team"].map(canonize)
    else:
        pop_df = pop_df.rename(columns={"Team": "TeamCanonical"})
        pop_df["TeamCanonical"] = pop_df["TeamCanonical"].map(canonize)


    TEAM_COL = "TeamCanonical" if "TeamCanonical" in games_df.columns else "Team"
    ALL_TEAMS = sorted(games_df[TEAM_COL].dropna().unique().tolist())


    # Sidebar
    st.sidebar.title("Filter Options")
    st.sidebar.markdown("Customize your analysis by selecting teams, conferences, and date ranges.")

    # Helpful notice if any team didn’t map
    unmapped = sorted(games_df.loc[games_df["Conference"].isna(), "Team"].dropna().unique())
    if unmapped:
        st.sidebar.info(f"Unmapped teams (add to ALIASES/TEAM_META if needed): {', '.join(unmapped)}")

    # New conference/division filters
    conf_opts = sorted(games_df["Conference"].dropna().unique().tolist())
    div_opts  = sorted(games_df["Division"].dropna().unique().tolist())

    conf_sel = st.sidebar.multiselect("Conference", options=conf_opts)
    div_sel  = st.sidebar.multiselect("Division", options=div_opts)

    # Teams
    teams_sel = st.sidebar.multiselect("Teams", options=ALL_TEAMS, default=[])

    min_date = games_df["Date"].min().date()
    max_date = games_df["Date"].max().date()
    date_range = st.sidebar.date_input("Game date range", (min_date, max_date), min_value=min_date, max_value=max_date, format="MM/DD/YYYY",)

    min_att = int(st.sidebar.number_input("Minimum attendance", value=0, min_value=0, step=100))

    # Filter games_df

    if teams_sel:
        gmask = games_df[TEAM_COL].isin(teams_sel)
    else:
        # No teams selected -> show nothing
        gmask = pd.Series(False, index=games_df.index)

    meta_mask = pd.Series(True, index=games_df.index)
    if conf_sel:
        meta_mask &= games_df["Conference"].isin(conf_sel)
    if div_sel:
        meta_mask &= games_df["Division"].isin(div_sel)

    teams_from_meta = set(games_df.loc[meta_mask, TEAM_COL].dropna().unique())

    if teams_sel:
        teams_effective = set(teams_sel)
        if conf_sel or div_sel:
            teams_effective &= teams_from_meta
    else:
        teams_effective = teams_from_meta if (conf_sel or div_sel) else set()

    gmask = games_df[TEAM_COL].isin(list(teams_effective)) if teams_effective else pd.Series(False, index=games_df.index)



    games_f = games_df.loc[gmask].copy()



    # Header
    st.title("NBA Home Court Advantage Analysis")
    st.markdown("""
    Investigating the Impact of Home Court Advantage in Modern Basketball
    Explore how attendance, crowd size, and venue affect team performance across NBA seasons.
    """)
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Home vs Away Advantage",
        "Crowd Size Effects",
        "Popularity & Arenas",
        "Statistical Analysis"
    ])

    with tab1:
        st.subheader("Home vs Away Win Rates")
        st.markdown("Analyze how teams perform at home versus away games across different seasons.")

        if games_f.empty:
            st.warning("No games match the current filters. Please adjust your selections.")
        else:
            hw_team_season = (
                games_f.groupby(["Season", "TeamCanonical"])["HomeWin"]
                .mean()
                .reset_index(name="HomeWinRate")
                .rename(columns={"TeamCanonical": "Team"})
            )
            hw_team_season["SeasonInt"] = hw_team_season["Season"].astype(int)

            # ggplot season trend

            p_season = (
                ggplot(hw_team_season, aes(x="SeasonInt", y="HomeWinRate", color="Team"))
                + geom_line(size=1.2, alpha=0.8)
                + scale_y_continuous(labels=percent_format())
                + scale_x_continuous(
                    breaks=sorted(hw_team_season["SeasonInt"].unique()),
                    labels=lambda xs: [str(int(x)) for x in xs]
                )
                + scale_color_brewer(type='qual', palette='Set2')
                + labs(
                    title="Home Win Rate Trends by Team Over Time",
                    x="Season",
                    y="Home Win Rate"
                )
                + theme_minimal()
                + theme(
                    figure_size=(10, 5),
                    plot_title=element_text(size=14, weight='bold', margin={'b': 10}),
                    axis_title=element_text(size=11, weight='bold'),
                    axis_text_x=element_text(rotation=45, ha='right', size=9),
                    axis_text_y=element_text(size=9),
                    legend_position='right',
                    legend_title=element_text(size=10, weight='bold'),
                    panel_grid_major=element_line(color='#e0e0e0', size=0.5),
                    panel_grid_minor=element_line(color='#f0f0f0', size=0.3),
                    subplots_adjust={'bottom': 0.15, 'right': 0.85}
                )
            )
            st.pyplot(p_season.draw(), width='stretch')

            # Home vs Away comparison bar
            home_rate = games_f["HomeWin"].mean()
            away_rate = 1.0 - home_rate  
            comp_df = pd.DataFrame(
                {"Venue": ["Home", "Away (inferred)"], "WinRate": [home_rate, away_rate]}
            )
            comp_df["WinRateLabel"] = (comp_df["WinRate"] * 100).round(1).astype(str) + "%"

            p1 = (
                ggplot(comp_df, aes(x="Venue", y="WinRate", fill="Venue"))
                + geom_col(width=0.6, alpha=0.85)
                + geom_text(aes(label="WinRateLabel"), va="bottom", nudge_y=0.02, size=11, fontweight='bold')
                + scale_y_continuous(labels=percent_format(), limits=(0, max(comp_df["WinRate"]) * 1.15))
                + scale_fill_manual(values=['#2ecc71', '#e74c3c'])
                + labs(
                    title="Home vs Away Win Rate Comparison",
                    x="Venue",
                    y="Win Rate"
                )
                + theme_minimal()
                + theme(
                    figure_size=(7, 5),
                    plot_title=element_text(size=14, weight='bold', margin={'b': 10}),
                    axis_title=element_text(size=11, weight='bold'),
                    axis_text_x=element_text(rotation=0, ha='center', size=10),
                    axis_text_y=element_text(size=9),
                    legend_position='none',
                    panel_grid_major_y=element_line(color='#e0e0e0', size=0.5),
                    panel_grid_major_x=element_line(color='none'),
                    subplots_adjust={'bottom': 0.12}
                )
            )
            st.pyplot(p1.draw(), width='stretch')



    with tab2:
        st.subheader("Crowd Size and Outcomes")
        st.markdown("Explore the relationship between attendance levels and home team win rates.")

        if games_f.empty:
            st.warning("No games match the current filters. Please adjust your selections.")
        else:
            if games_f["Attendance"].nunique() < 4:
                games_f["AttBucket"] = pd.qcut(
                    games_f["Attendance"], q=2, labels=["Small", "Large"], duplicates="drop"
                )
            else:
                games_f["AttBucket"] = pd.qcut(
                    games_f["Attendance"], 4,
                    labels=["Small", "Mid-Small", "Mid-Large", "Large"],
                    duplicates="drop"
                )

            summary = (
                games_f.groupby("AttBucket", observed=True)["HomeWin"]
                .mean()
                .reset_index()
                .rename(columns={"HomeWin": "WinRate"})
                .sort_values("AttBucket")
            )

            summary["Label"] = (summary["WinRate"] * 100).round(1).astype(str) + "%"

            p2 = (
                ggplot(summary, aes(x="AttBucket", y="WinRate", fill="AttBucket"))
                + geom_col(width=0.65, alpha=0.85)
                + geom_text(aes(label="Label"), va="bottom", nudge_y=0.02, size=10, fontweight='bold')
                + scale_y_continuous(labels=percent_format(), limits=(0, max(summary["WinRate"]) * 1.15))
                + scale_fill_brewer(type='seq', palette='Blues')
                + labs(
                    title="Home Win Rate by Attendance Level",
                    x="Attendance Bucket",
                    y="Home Win Rate"
                )
                + theme_minimal()
                + theme(
                    figure_size=(8, 5),
                    plot_title=element_text(size=14, weight='bold', margin={'b': 10}),
                    axis_title=element_text(size=11, weight='bold'),
                    axis_text_x=element_text(size=9),
                    axis_text_y=element_text(size=9),
                    legend_position='none',
                    panel_grid_major_y=element_line(color='#e0e0e0', size=0.5),
                    panel_grid_major_x=element_line(color='none'),
                    subplots_adjust={'bottom': 0.12}
                )
            )
            st.pyplot(p2.draw(), width='stretch')


    with tab3:
        st.subheader("Popularity vs Home Advantage")
        st.markdown("Discover how team popularity correlates with home win rates and average attendance.")

        # Use filtered games so the plot respects sidebar filters
        base_df = games_f if not games_f.empty else games_df

        # Compute each team's mean attendance and win rate
        team_stats = (
            base_df.groupby("Team", observed=True)
            .agg(Attendance=("Attendance", "mean"),
                WinRate=("HomeWin", "mean"))
            .reset_index()
        )

        # Merge with popularity data
        merged = team_stats.merge(pop_df, on="Team", how="left")

        plot_df = merged.dropna(subset=["Popularity"])
        if plot_df.empty:
            st.warning("No teams have popularity scores available to display.")
        else:
            p3 = (
                ggplot(plot_df, aes(x="Popularity", y="WinRate", size="Attendance"))
                + geom_point(alpha=0.7, color='#3498db', fill='#5dade2')
                + geom_smooth(method="lm", se=True, color='#e74c3c', size=1.2, alpha=0.2)
                + scale_size_continuous(range=(4, 15), name="Avg Attendance")
                + scale_y_continuous(labels=percent_format())
                + labs(
                    title="Team Popularity vs Home Win Rate",
                    x="Team Popularity Score",
                    y="Home Win Rate"
                )
                + theme_minimal()
                + theme(
                    figure_size=(9, 6),
                    plot_title=element_text(size=14, weight='bold', margin={'b': 10}),
                    axis_title=element_text(size=11, weight='bold'),
                    axis_text=element_text(size=9),
                    legend_position='right',
                    legend_title=element_text(size=10, weight='bold'),
                    legend_text=element_text(size=9),
                    panel_grid_major=element_line(color='#e0e0e0', size=0.5),
                    panel_grid_minor=element_line(color='#f0f0f0', size=0.3),
                    subplots_adjust={'right': 0.85}
                )
            )
            st.pyplot(p3.draw(), width='stretch')


    with tab4:
        st.subheader("Statistical Models & Regression Analysis")
        st.markdown("Dive deep into the statistical relationships between home advantage, attendance, and win rates.")

        # turn blob content into DataFrames / dicts
        home_df = pd.read_csv(io.StringIO(HOME_CSV))
        away_df = pd.read_csv(io.StringIO(AWAY_CSV))

        # fetch games-with-ids
        GAMES_IDS_JSON = retrieve_data_from_gcs(
            service_account_file_path, project_id, bucket_name, "get_game_ids.json"
        )
        games_with_ids = json.loads(GAMES_IDS_JSON)

        def logistic_regression(home, away):
            home = home.copy(); away = away.copy()
            home['HOME'] = 1; away['HOME'] = 0
            factors = ['WIN','HOME','FGM','FGA','FG3M','FG3A','FTM','FTA','REB','AST','STL','BLK','TOV','PF','EFGP','TOVP','FTR']
            all_ = pd.concat([home[factors], away[factors]], ignore_index=True)
            all_['EFGP'] *= 100; all_['TOVP'] *= 100; all_['FTR'] *= 100
            model = smf.logit(f"WIN ~ {' + '.join(factors[1:])}", data=all_).fit(disp=False)
            st.markdown("**Logistic regression summary (WIN ~ predictors):**")
            st.code(model.summary().as_text(), language="text")

        def make_bar_chart(home, away):
            home_summary = home.groupby('TEAM_ID')['HOME_WINRATE'].mean().reset_index()
            away_summary = away.groupby('TEAM_ID')['AWAY_WINRATE'].mean().reset_index()
            comparison = home_summary.merge(away_summary, on='TEAM_ID')
            team_names = away.groupby('TEAM_ID')['TEAM_ABBREVIATION'].first().reset_index()
            comparison = comparison.merge(team_names, on='TEAM_ID')
            comparison['HOME_ADVANTAGE'] = comparison['HOME_WINRATE'] - comparison['AWAY_WINRATE']
            comparison = comparison.sort_values('HOME_WINRATE', ascending=True)

            fig, ax = plt.subplots(figsize=(10, 12))
            y = np.arange(len(comparison)); h = 0.35
            b1 = ax.barh(y - h/2, comparison['HOME_WINRATE'], h, label='Home Win Rate', color='#44CCFF')
            b2 = ax.barh(y + h/2, comparison['AWAY_WINRATE'], h, label='Away Win Rate', color='#6C6F7F')
            ax.set_ylabel('Team', fontsize=12, fontweight='bold')
            ax.set_xlabel('Win Rate', fontsize=12, fontweight='bold')
            ax.set_title('Home vs Away Win Rates by Team (2014-2025)', fontsize=14, fontweight='bold', pad=20)
            ax.set_yticks(y); ax.set_yticklabels(comparison['TEAM_ABBREVIATION'])
            ax.legend(loc='upper right', fontsize=10)
            ax.grid(axis='x', alpha=0.3, linestyle='--'); ax.set_xlim(0, 1)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['bottom'].set_linewidth(False)
            for bars in [b1, b2]:
                for bar in bars:
                    w = bar.get_width()
                    ax.text(w + 0.01, bar.get_y() + bar.get_height()/2., f'{w*100:.0f}%', ha='left', va='center', fontsize=8)
            st.pyplot(fig)
            plt.close(fig)

        def winrate_attendance_comparison(home, games_json_dict):
            games_list = []
            for _, games in games_json_dict.items():
                games_list.extend(games)
            json_df = pd.DataFrame(games_list, columns=['Date','Attendance','Points','HomeWin','GAME_ID']).dropna()
            json_df['GAME_ID'] = json_df['GAME_ID'].astype('int64')

            df = pd.merge(home, json_df, on='GAME_ID', how='inner')
            home_stats = df.groupby('TEAM_ID').agg({
                'SEASON_WINRATE':'mean', 'HOME_WINRATE':'mean', 'Attendance':'mean'
            }).round(3)
            home_stats['WINRATE_DIFF'] = (home_stats['HOME_WINRATE'] - home_stats['SEASON_WINRATE']).round(3)
            hs = home_stats.sort_values('WINRATE_DIFF', ascending=False)

            # Guard against empty DataFrame before OLS
            if hs.empty or hs['Attendance'].nunique() <= 1:
                st.warning("Insufficient data for regression (empty or constant predictor).")
                return

            model = smf.ols('WINRATE_DIFF ~ Attendance', data=hs).fit()
            st.markdown("**OLS summary (WINRATE_DIFF ~ Attendance):**")
            st.code(model.summary().as_text(), language="text")

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(hs['Attendance'], hs['WINRATE_DIFF'], alpha=0.8, s=100)
            ax.set_xlabel('Average Attendance', fontsize=12)
            ax.set_ylabel('Win Rate Difference', fontsize=12)
            ax.set_title('Avg Attendance vs Win Rate Difference', fontsize=14)
            ax.grid(True, alpha=0.3)
            ax.spines[['top','right']].set_visible(False)
            st.pyplot(fig)
            plt.close(fig)


        # --- actually run Tab 4 content ---
        logistic_regression(home_df, away_df)
        make_bar_chart(home_df, away_df)
        winrate_attendance_comparison(home_df, games_with_ids)