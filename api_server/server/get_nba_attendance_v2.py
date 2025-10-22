import io
import pandas as pd
import requests
import time
import logging
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_nba_attendance_data() -> pd.DataFrame:
    '''
    Scrapes data from basketball-reference.com for the last
    10 seasons' worth of NBA games and puts them into a
    dataframe.  2020 and 2021 are skipped due to varying
    Covid restrictions on attendance.
    '''

    # Setup session with retry logic
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    months = ["october", "november", "december", "january",
            "february", "march", "april", "may", "june"]
    all_years_df = []

    logger.info("Starting NBA attendance data scraping...")
    try:
        for year in tqdm(range(2014, 2025), desc="Years", unit="year"):
            all_months_df = []
            if year == 2020 or year == 2021:
                continue
            for month in tqdm(months, desc=f"{year}", unit="month", leave=False):
                url = (
                    f"https://www.basketball-reference.com/"
                    f"leagues/NBA_{year}_games-{month}.html"
                    )
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0"
                }
                response = session.get(url, headers=headers, timeout=30)
                time.sleep(6)
                if response.status_code == 404:
                    logger.warning(f"Page not found: year={year}, month={month}")
                    continue
                elif response.status_code != 200:
                    logger.error(f"HTTP {response.status_code} for year={year}, month={month}")
                    continue
                logger.info(f"Successfully fetched: year={year}, month={month}")
                html_table = io.StringIO(response.text)
                tables = pd.read_html(html_table)
                df_temp = tables[0]
                all_months_df.append(df_temp)
            df_single_year = pd.concat(all_months_df, ignore_index=True)
            all_years_df.append(df_single_year)
            logger.info(f"Completed year {year}: {len(df_single_year)} games")
    except Exception as e:
        logger.error(f"Scraping error: {e}", exc_info=True)
        raise

    df = pd.concat(all_years_df, ignore_index=True)
    logger.info(f"Scraping complete: {len(df)} total games")
    return df


def clean_nba_attendance_data(nba_attendance_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Cleans raw dataframe by removing unnecessary columns and ensuring
    null values are dealt with.
    '''

    df = nba_attendance_df.drop(columns=
                        ["Start (ET)", "Unnamed: 6", "Unnamed: 7", "LOG",
                         "Notes"], errors="ignore")
    df["Home_Win"] = df["PTS.1"] > df["PTS"]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce",
                                format="%a, %b %d, %Y")
    df = df.dropna(subset=["Date"]).reset_index(drop=True)
    return df 


def create_nba_team_dictionary(nba_attendance_clean_df: pd.DataFrame) -> dict:
    '''
    Creates a dictionary of scraped data with each NBA team as a key
    which maps to a list of dictionaries, each containing the following
    information per game: Date, Attendance, Points Scored, Home Win
    '''

    nba_team_dict = {}
    for _, row in nba_attendance_clean_df.iterrows():
        team = row["Home/Neutral"]
        if team not in nba_team_dict:
            nba_team_dict[team] = []
        attendance = row["Attend."]
        attendance = int(attendance) if pd.notna(attendance) else None
        points = row["PTS.1"]
        points = int(points) if pd.notna(points) else None
        home_win = row["Home_Win"]
        home_win = bool(home_win) if pd.notna(home_win) else None
        nba_team_dict[team].append({
            "Date": row["Date"].strftime("%Y-%m-%d"),
            "Attendance": attendance,
            "Points": points,
            "HomeWin": home_win
        })
    return nba_team_dict
