import pandas as pd
import statsmodels.formula.api as smf
import json
import matplotlib.pyplot as plt
import numpy as np

def logistic_regression(home, away): 
    home['HOME'] = 1
    away['HOME'] = 0

    factors = ['WIN', 'HOME', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'EFGP', 'TOVP', 'FTR']

    all = pd.concat([home[factors], away[factors]], ignore_index=True)
    all['EFGP']*=100	
    all['TOVP']*=100
    all['FTR']*=100

    model = smf.logit(f'WIN~{'+'.join(factors[1:])}', data=all).fit()
    print(model.summary())

def make_bar_chart(home, away):
    home_summary = home.groupby('TEAM_ID')['HOME_WINRATE'].mean().reset_index()
    away_summary = away.groupby('TEAM_ID')['AWAY_WINRATE'].mean().reset_index()

    comparison = home_summary.merge(away_summary, on='TEAM_ID')

    team_names = away.groupby('TEAM_ID')['TEAM_ABBREVIATION'].first().reset_index()
    comparison = comparison.merge(team_names, on='TEAM_ID')

    comparison['HOME_ADVANTAGE'] = comparison['HOME_WINRATE'] - comparison['AWAY_WINRATE']
    comparison = comparison.sort_values('HOME_WINRATE', ascending=True)

    fig, ax = plt.subplots(figsize=(10, 12))

    y = np.arange(len(comparison))
    height = 0.35

    bars1 = ax.barh(y - height/2, comparison['HOME_WINRATE'], height, label='Home Win Rate', color='#44CCFF')
    bars2 = ax.barh(y + height/2, comparison['AWAY_WINRATE'], height, label='Away Win Rate', color='#6C6F7F')

    ax.set_ylabel('Team', fontsize=12, fontweight='bold')
    ax.set_xlabel('Win Rate', fontsize=12, fontweight='bold')
    ax.set_title('Home vs Away Win Rates by Team (2014-2025)', fontsize=14, fontweight='bold', pad=20)
    ax.set_yticks(y)
    ax.set_yticklabels(comparison['TEAM_ABBREVIATION'])
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_xlim(0, 1)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(False)
    for bars in [bars1, bars2]:
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                    f'{width*100:.0f}%',
                    ha='left', va='center', fontsize=8)
    plt.tight_layout()
    plt.savefig('home_vs_away_winrates.png', dpi=300, bbox_inches='tight')



def winrate_attendance_comparison(home):
    with open('../games_with_gameids.json', 'r') as f:
        data = json.load(f)

    games_list = []
    for team, games in data.items():
        games_list.extend(games)

    json_df = pd.DataFrame(games_list)
    json_df.columns = ['Date', 'Attendance', 'Points', 'HomeWin', 'GAME_ID']
    json_df = json_df.dropna()
    json_df["GAME_ID"] = json_df["GAME_ID"].astype('int64')
    df = pd.merge(home, json_df, on='GAME_ID', how='inner')
    home_stats = df.groupby('TEAM_ID').agg({
        'SEASON_WINRATE': 'mean',
        'HOME_WINRATE': 'mean',
        'Attendance': 'mean'
    }).round(3)
    home_stats['WINRATE_DIFF'] = (home_stats['HOME_WINRATE'] - home_stats['SEASON_WINRATE']).round(3)
    home_stats_sorted = home_stats.sort_values('WINRATE_DIFF', ascending=False)
    model = smf.ols(f'WINRATE_DIFF~Attendance', data=home_stats_sorted).fit()
    print(model.summary())

    fig, ax= plt.subplots(figsize=(10, 6))
    ax.scatter(home_stats_sorted['Attendance'], home_stats_sorted['WINRATE_DIFF'], alpha=0.8, s=100)

    plt.xlabel('Average Attendance', fontsize=12)
    plt.ylabel('Win Rate Difference', fontsize=12)
    plt.title('Avg Attendance vs Win Rate Difference', fontsize=14)
    plt.grid(True, alpha=0.3)

    ax.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    plt.savefig('winrate_diff_vs_attendance.png', dpi=300, bbox_inches='tight')

if __name__=='__main__':
    home=pd.read_csv('../data/HOME_GAMES.csv')
    away=pd.read_csv('../data/AWAY_GAMES.csv')
    logistic_regression(home, away)
    make_bar_chart(home, away)
    winrate_attendance_comparison(home)
    print('========================================================================')
    print('\n\nPlots saved to home_vs_away_winrates.png and winrate_diff_vs_attendance.png')


