# NBA Home Court Advantage Analysis

## Project Overview

This project investigates whether "Home Court Advantage" exists in modern NBA basketball. By combining crowd data, team schedules, and game outcomes, we analyze how teams perform in large versus small arenas and during long road game streaks.

The system scrapes NBA game data from Basketball Reference and the NBA Stats API, stores it in Google Cloud Storage (GCS), and provides interactive visualizations through a Streamlit dashboard.

https://streamlit-55318076574.us-west2.run.app/

---

## Architecture

The project uses a **multi-container Docker architecture** with services orchestrated via Docker Compose:

1. **api-server** (FastAPI on port 8000): Data scraping and API endpoints
2. **webapp** (Streamlit on port 8501/80): Interactive dashboard for analysis

**Note:** The cron service has been removed from docker-compose.yml as it cannot be deployed to GCP Cloud Run. Use Google Cloud Scheduler to trigger endpoints instead.

All services share the same conda environment and communicate over a Docker network (`app-network`). Data is persisted to Google Cloud Storage.

---

## Data Sources

### 1. [Basketball Reference](https://www.basketball-reference.com/leagues/NBA_2024_games.html)

- Provides box scores and game results over a long period of time
- Data collected via web scraping (no API) using asynchronous GET requests
- Information for the past 10+ years stored in GCS as JSON:

```json
{
  "Team Name": [
    {
      "Date": "YYYY-MM-DD",
      "Attendance": <int>,
      "Points": <int>,
      "HomeWin": <bool>
    }
  ]
}
```

### 2. [NBA Stats API](https://stats.nba.com/)

- Provides player statistics, advanced metrics, shot charts, and game-by-game performance
- Data collected via the `nba-api` Python library
- Combined dataset structure:

```json
{
  "Date": "YYYY-MM-DD",
  "GAME_ID": <int>,
  "TEAM_ID": <int>,
  "HOME": <bool>,
  "WIN": <bool>,
  "Attendance": <int>,
  "various box score stats": "...",
  "eFG%": <float>,
  "TOV%": <float>,
  "FT Rate": <float>
}
```

### 3. [SeatGeek API](https://developer.seatgeek.com/) (Optional)

- Provides team popularity metrics
- **Optional** - Not required for core analysis
- Requires developer account approval (email tech-architecture@seatgeek.com)

---

## Setup Instructions

### Prerequisites

1. **Python Environment**: Conda is required
2. **GCP Credentials**: Service account key for Google Cloud Storage access
3. **Docker**: For containerized deployment

### Environment Setup

1. **Create environment variables file**:
   ```bash
   cp .env.template .env
   ```

2. **Required environment variables** (in `.env`):
   - `GCP_SERVICE_ACCOUNT_KEY`: Path to GCP service account JSON key file
   - `PROJECT_ID`: GCP project ID
   - `GCP_BUCKET_NAME`: GCS bucket name for data storage
   - `SEATGEEK_CLIENT_ID`: SeatGeek API client ID (optional)
   - `SECRET_ID`: SeatGeek API secret (optional)

3. **Update GCP credentials path** in `docker-compose.yml`:
   ```yaml
   volumes:
     - /path/to/your/gcp-key.json:/tmp/gcp-key.json:ro
   ```

### Local Development (Without Docker)

1. **Create conda environment**:
   ```bash
   conda env create -n msds692_final_project -f api_server/environment.yml
   ```

2. **Activate environment**:
   ```bash
   conda activate msds692_final_project
   ```

3. **Run FastAPI server**:
   ```bash
   fastapi run api_server/main.py
   ```
   Access API documentation at: http://localhost:8000/docs

4. **Run Streamlit dashboard** (in separate terminal):
   ```bash
   cd streamlit
   streamlit run interactive_app.py
   ```
   Access dashboard at: http://localhost:8501

### Docker Deployment

1. **Build all services**:
   ```bash
   docker compose build
   ```

2. **Start services**:
   ```bash
   docker compose up
   ```
   Or run in background:
   ```bash
   docker compose up -d
   ```

3. **Access services**:
   - FastAPI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Streamlit: http://localhost (port 80) or http://localhost:8501

4. **View logs**:
   ```bash
   docker compose logs -f api-server
   docker compose logs -f webapp
   ```

5. **Stop services**:
   ```bash
   docker compose down
   ```

---

## API Endpoints

The FastAPI server (`api_server/main.py`) provides four main data collection endpoints:

### 1. NBA Attendance Data
```
GET /retrieve_nba_attendance_data_as_json_file
```
- Scrapes attendance data from Basketball Reference
- Returns JSON, uploads to GCS as `nba_attendance_data.json`
- Runtime: ~6 minutes

### 2. SeatGeek API Data (Optional)
```
GET /retrieve_seatgeek_api_data_as_json_file
```
- Fetches team popularity data from SeatGeek API
- Requires SeatGeek API credentials
- Returns JSON, uploads to GCS as `seatgeek_api_data.json`
- Runtime: ~1 second

### 3. NBA Game IDs
```
GET /retrieve_nba_game_ids_as_json_file
```
- Gets NBA game IDs using nba-api library
- Returns JSON, uploads to GCS as `get_game_ids.json`
- Runtime: ~6 minutes

### 4. NBA Game Data (Full Statistics)
```
GET /retrieve_all_nba_game_data_as_csv
```
- Fetches complete game statistics for seasons 2013-14 through 2023-24
- Returns CSVs for home/away games
- Uploads to GCS as `all_nba_game_data_home.csv` and `all_nba_game_data_away.csv`
- Runtime: ~6 minutes

**Query Parameter**: Add `?crontab=true` to suppress response body (useful for automated jobs)

---

## Data Collection Workflow

1. **Manual Collection**: Call endpoints directly via the FastAPI `/docs` interface
2. **Automated Collection**: Use Google Cloud Scheduler to trigger endpoints via HTTP requests

All scraped data is automatically uploaded to the configured GCS bucket.

---

## Code Organization

### `api_server/server/`
- `get_nba_attendance_v2.py`: Basketball Reference scraping logic with retry mechanisms
- `seatgeek_api_data.py`: SeatGeek API integration
- `get_game_data.py`: Sequential game data fetching from NBA API
- `get_game_id_api_mod.py`: NBA game ID retrieval using nba-api
- `define_variables.py`: Environment variable loading

### `streamlit/`
- `interactive_app.py`: Main Streamlit dashboard with visualizations
- `define_variables.py`: Environment variable loading

### `dev_scripts/`
Development and testing scripts (not used in production):
- `nba_attendance.py`: Attendance scraping experiments
- `get_game_data.py`: Game data retrieval experiments
- `get_game_id.py`: Game ID retrieval experiments
- `plots.py`: Visualization experiments

### Data Flow

1. FastAPI endpoints scrape/fetch data from web sources
2. Data is transformed into JSON/CSV format
3. `save_to_gcs()` function uploads data to GCS bucket
4. Streamlit app retrieves data from GCS using `retrieve_data_from_gcs()`
5. Streamlit performs analysis and creates visualizations

---

## Production Deployment (GCP Cloud Run)

For detailed deployment instructions and troubleshooting, see:
- [`api_server/DEPLOYMENT_FIXES.md`](api_server/DEPLOYMENT_FIXES.md) - Comprehensive guide for GCP deployment

### Quick Summary

1. **Build and test locally** using Docker first
2. **Deploy to Cloud Run**:
   - Deploy `api-server` and `webapp` as separate Cloud Run services
   - Configure environment variables in Cloud Run settings
   - Set timeout to at least 30 minutes for scraping endpoints

3. **Configure Cloud Scheduler**:
   ```
   URL: https://your-api-server.run.app/retrieve_nba_attendance_data_as_json_file?crontab=true
   Method: GET
   Timeout: 1800 seconds (30 minutes)
   ```

4. **Monitor logs** via Cloud Logging

---

## Team Name Handling

The codebase uses a canonicalization system for team names to handle aliases and historical name changes:

```python
ALIASES = {
    "LA Clippers": "Los Angeles Clippers",
    "Charlotte Bobcats": "Charlotte Hornets",
    "New Orleans Hornets": "New Orleans Pelicans"
}
```

Use `canonize(team_name)` in `streamlit/interactive_app.py` when working with team names.

---

## Known Issues & Limitations

1. **LA Clippers/Lakers edge case**: Games between these teams may have scheduling conflicts since they share an arena (Crypto.com Arena).

2. **SeatGeek API access**: Requires manual approval from SeatGeek (2-3 day turnaround). Not critical for core analysis.

3. **Basketball Reference rate limiting**: Enhanced headers and delays implemented to avoid blocking (see `DEPLOYMENT_FIXES.md`).

---

## Testing

No formal test suite exists. Manual testing is done via:
- FastAPI `/docs` endpoint (interactive API testing)
- Direct API endpoint calls using `curl`
- Streamlit dashboard verification
- Docker logs monitoring

**Test Results**: All scrapers successfully tested in Docker environment (see `api_server/DEPLOYMENT_FIXES.md` for details).

---

## Package Management

The project uses **conda** for environment management. Key packages:

**Core Framework**:
- `fastapi`, `uvicorn` (API server)
- `streamlit` (dashboard)

**Data Processing**:
- `pandas`, `numpy`
- `statsmodels`, `matplotlib`, `plotnine`

**Web Scraping**:
- `requests`, `beautifulsoup4`, `lxml`
- `nba-api` (pip package)

**Cloud Integration**:
- `google-cloud-storage`

See `api_server/environment.yml` for the complete package list.

---

## Documentation Files

- `README.md` (this file): Complete project guide
- `api_server/DEPLOYMENT_FIXES.md`: GCP deployment troubleshooting and fixes

---

## License

This project is part of a course assignment for MSDS 692.

---

## Support

For issues:
1. Check `api_server/DEPLOYMENT_FIXES.md` for deployment issues
2. View container logs: `docker compose logs api-server`
3. Check Cloud Logging for GCP deployments
4. Verify GCS bucket permissions and uploads
