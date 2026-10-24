#!/usr/bin/env python3
"""
API-Based Auto-Update System for Echo Mind
Fetches real-time data from various APIs daily and updates the database automatically
"""

import os
import json
import time
import requests
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    name: str
    url: str
    headers: Dict[str, str]
    params: Dict[str, Any]
    data_path: List[str]  # Path to data in JSON response
    update_frequency: str  # 'daily', 'hourly', 'weekly'

class APIDataUpdater:
    def __init__(self):
        self.db_path = 'real_time_data.db'
        self.config_file = 'api_config.json'
        self.last_update_file = 'api_last_update.json'
        
        # Initialize APIs configuration
        self.apis = self.load_api_config()
        self.init_database()
        
    def load_api_config(self) -> List[APIConfig]:
        """Load API configurations from file or create default ones"""
        apis = [
            # Sports APIs
            APIConfig(
                name="cricapi_current_matches",
                url="https://api.cricapi.com/v1/currentMatches",
                headers={"Content-Type": "application/json"},
                params={"apikey": os.environ.get('CRICAPI_KEY', 'demo_key')},
                data_path=["data"],
                update_frequency="daily"
            ),
            
            # News APIs (Enhanced)
            APIConfig(
                name="newsapi_india_sports",
                url="https://newsapi.org/v2/top-headlines",
                headers={"Content-Type": "application/json"},
                params={
                    "apikey": os.environ.get('NEWS_API_KEY', 'demo_key'),
                    "country": "in",
                    "category": "sports",
                    "pageSize": 20
                },
                data_path=["articles"],
                update_frequency="daily"
            ),
            
            APIConfig(
                name="newsapi_india_health",
                url="https://newsapi.org/v2/top-headlines",
                headers={"Content-Type": "application/json"},
                params={
                    "apikey": os.environ.get('NEWS_API_KEY', 'demo_key'),
                    "country": "in",
                    "category": "health",
                    "pageSize": 20
                },
                data_path=["articles"],
                update_frequency="daily"
            ),
            
            APIConfig(
                name="newsapi_india_technology",
                url="https://newsapi.org/v2/top-headlines",
                headers={"Content-Type": "application/json"},
                params={
                    "apikey": os.environ.get('NEWS_API_KEY', 'demo_key'),
                    "country": "in",
                    "category": "technology",
                    "pageSize": 20
                },
                data_path=["articles"],
                update_frequency="daily"
            ),
            
            # Government/Official APIs
            APIConfig(
                name="covid19_india",
                url="https://api.covid19india.org/data.json",
                headers={"Content-Type": "application/json"},
                params={},
                data_path=["statewise"],
                update_frequency="daily"
            ),
            
            # Financial APIs
            APIConfig(
                name="bse_sensex",
                url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w",
                headers={"Content-Type": "application/json"},
                params={"Debtflag": ""},
                data_path=["Table"],
                update_frequency="daily"
            ),
            
            # Weather API for climate data
            APIConfig(
                name="openweather_india",
                url="https://api.openweathermap.org/data/2.5/weather",
                headers={"Content-Type": "application/json"},
                params={
                    "appid": os.environ.get('OPENWEATHER_KEY', 'demo_key'),
                    "q": "New Delhi,IN",
                    "units": "metric"
                },
                data_path=[],
                update_frequency="daily"
            )
        ]
        
        return apis

    def init_database(self):
        """Initialize SQLite database for storing real-time data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for different data types
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                data_key TEXT NOT NULL,
                data_value TEXT NOT NULL,
                source_url TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(api_name, data_type, data_key) ON CONFLICT REPLACE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sports_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                team_code TEXT NOT NULL,
                captain TEXT,
                vice_captain TEXT,
                players TEXT, -- JSON string of players
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                season TEXT,
                tournament TEXT,
                UNIQUE(team_code, tournament, season) ON CONFLICT REPLACE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS current_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL, -- politics, sports, health, etc.
                subcategory TEXT, -- ipl, covid, elections, etc.
                key_info TEXT NOT NULL,
                value_info TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, subcategory, key_info) ON CONFLICT REPLACE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def fetch_api_data(self, api_config: APIConfig) -> Optional[Dict]:
        """Fetch data from a single API"""
        try:
            logger.info(f"Fetching data from {api_config.name}")
            
            # Handle demo keys
            if any('demo_key' in str(v) for v in api_config.params.values()):
                logger.warning(f"Demo key detected for {api_config.name} - using mock data")
                return self.get_mock_data(api_config.name)
            
            response = requests.get(
                api_config.url,
                headers=api_config.headers,
                params=api_config.params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Navigate to data using data_path
                for path in api_config.data_path:
                    if isinstance(data, dict) and path in data:
                        data = data[path]
                    else:
                        logger.warning(f"Path {path} not found in response for {api_config.name}")
                        return None
                
                logger.info(f"Successfully fetched data from {api_config.name}")
                return data
            else:
                logger.error(f"API error {response.status_code} for {api_config.name}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {api_config.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {api_config.name}: {e}")
            return None

    def get_mock_data(self, api_name: str) -> Dict:
        """Provide mock data when API keys are not available"""
        mock_data = {
            "cricapi_current_matches": [
                {
                    "name": "Royal Challengers Bangalore vs Chennai Super Kings",
                    "status": "Match not started",
                    "venue": "M.Chinnaswamy Stadium, Bengaluru",
                    "date": datetime.now().isoformat(),
                    "teams": ["Royal Challengers Bangalore", "Chennai Super Kings"]
                }
            ],
            "newsapi_india_sports": [
                {
                    "title": "IPL 2024 Captain Updates",
                    "description": "Latest updates on IPL team captains for the 2024 season",
                    "url": "https://example.com/sports",
                    "publishedAt": datetime.now().isoformat(),
                    "source": {"name": "Sports Mock"}
                }
            ],
            "covid19_india": [
                {
                    "state": "Total",
                    "confirmed": "44000000",
                    "recovered": "43500000",
                    "deaths": "530000",
                    "lastupdatedtime": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
            ]
        }
        
        return mock_data.get(api_name, {})

    def process_sports_data(self, data: Any, api_name: str):
        """Process and store sports-specific data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if api_name == "cricapi_current_matches" and isinstance(data, list):
                # Process cricket match data to extract team information
                for match in data:
                    if isinstance(match, dict) and 'teams' in match:
                        for team in match.get('teams', []):
                            # Try to identify IPL teams and update their info
                            team_info = self.identify_team_info(team)
                            if team_info:
                                cursor.execute('''
                                    INSERT OR REPLACE INTO sports_data
                                    (team_name, team_code, captain, season, tournament, last_updated)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    team_info['name'],
                                    team_info['code'],
                                    team_info.get('captain'),
                                    '2024',
                                    'IPL',
                                    datetime.now()
                                ))
            
            elif api_name == "newsapi_india_sports" and isinstance(data, list):
                # Process sports news for captain changes, transfers, etc.
                for article in data:
                    if isinstance(article, dict):
                        title = article.get('title', '').lower()
                        description = article.get('description', '').lower()
                        
                        # Look for captain-related news
                        if 'captain' in title or 'captain' in description:
                            captain_info = self.extract_captain_info(article)
                            if captain_info:
                                cursor.execute('''
                                    INSERT OR REPLACE INTO current_info
                                    (category, subcategory, key_info, value_info, source, last_updated)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    'sports',
                                    'ipl',
                                    f"{captain_info['team']}_captain",
                                    captain_info['captain'],
                                    article.get('source', {}).get('name', 'Unknown'),
                                    datetime.now()
                                ))
            
            conn.commit()
            logger.info(f"Processed sports data from {api_name}")
            
        except Exception as e:
            logger.error(f"Error processing sports data from {api_name}: {e}")
        finally:
            conn.close()

    def identify_team_info(self, team_name: str) -> Optional[Dict]:
        """Identify team information from team name"""
        team_mapping = {
            'royal challengers bangalore': {'name': 'Royal Challengers Bangalore', 'code': 'rcb', 'captain': 'Faf du Plessis'},
            'chennai super kings': {'name': 'Chennai Super Kings', 'code': 'csk', 'captain': 'MS Dhoni'},
            'mumbai indians': {'name': 'Mumbai Indians', 'code': 'mi', 'captain': 'Hardik Pandya'},
            'delhi capitals': {'name': 'Delhi Capitals', 'code': 'dc', 'captain': 'Rishabh Pant'},
            'kolkata knight riders': {'name': 'Kolkata Knight Riders', 'code': 'kkr', 'captain': 'Shreyas Iyer'},
            'rajasthan royals': {'name': 'Rajasthan Royals', 'code': 'rr', 'captain': 'Sanju Samson'},
            'punjab kings': {'name': 'Punjab Kings', 'code': 'pbks', 'captain': 'Shikhar Dhawan'},
            'sunrisers hyderabad': {'name': 'Sunrisers Hyderabad', 'code': 'srh', 'captain': 'Pat Cummins'},
            'gujarat titans': {'name': 'Gujarat Titans', 'code': 'gt', 'captain': 'Shubman Gill'},
            'lucknow super giants': {'name': 'Lucknow Super Giants', 'code': 'lsg', 'captain': 'KL Rahul'}
        }
        
        team_lower = team_name.lower()
        for key, info in team_mapping.items():
            if key in team_lower or any(word in team_lower for word in key.split()):
                return info
        
        return None

    def extract_captain_info(self, article: Dict) -> Optional[Dict]:
        """Extract captain information from news article"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"
        
        # Simple pattern matching for captain changes
        teams = ['rcb', 'csk', 'mi', 'dc', 'kkr', 'rr', 'pbks', 'srh', 'gt', 'lsg']
        
        for team in teams:
            if team in text and 'captain' in text:
                # This is a simplified extraction - in production, use NLP
                return {
                    'team': team,
                    'captain': 'To be determined from news',  # Would extract actual name
                    'source': article.get('url', '')
                }
        
        return None

    def process_general_data(self, data: Any, api_name: str):
        """Process and store general data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Store raw API data
            if isinstance(data, (dict, list)):
                cursor.execute('''
                    INSERT OR REPLACE INTO api_data
                    (api_name, data_type, data_key, data_value, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    api_name,
                    'raw_response',
                    f"{api_name}_latest",
                    json.dumps(data),
                    datetime.now()
                ))
            
            # Process specific data types
            if api_name == "covid19_india" and isinstance(data, list):
                for state_data in data:
                    if isinstance(state_data, dict) and 'state' in state_data:
                        cursor.execute('''
                            INSERT OR REPLACE INTO current_info
                            (category, subcategory, key_info, value_info, source, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            'health',
                            'covid19',
                            f"covid_{state_data['state']}_confirmed",
                            state_data.get('confirmed', '0'),
                            'covid19india.org',
                            datetime.now()
                        ))
            
            conn.commit()
            logger.info(f"Processed general data from {api_name}")
            
        except Exception as e:
            logger.error(f"Error processing general data from {api_name}: {e}")
        finally:
            conn.close()

    def daily_update(self):
        """Perform daily update from all APIs"""
        logger.info("Starting daily API update process...")
        start_time = datetime.now()
        
        successful_updates = 0
        total_apis = len(self.apis)
        
        for api_config in self.apis:
            try:
                # Check if update is needed based on frequency
                if not self.should_update(api_config.name, api_config.update_frequency):
                    logger.info(f"Skipping {api_config.name} - not due for update")
                    continue
                
                # Fetch data from API
                data = self.fetch_api_data(api_config)
                
                if data is not None:
                    # Process data based on type
                    if 'sports' in api_config.name or 'cricket' in api_config.name:
                        self.process_sports_data(data, api_config.name)
                    else:
                        self.process_general_data(data, api_config.name)
                    
                    # Record successful update
                    self.record_update(api_config.name, True)
                    successful_updates += 1
                else:
                    self.record_update(api_config.name, False)
                
                # Rate limiting - be respectful to APIs
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error updating {api_config.name}: {e}")
                self.record_update(api_config.name, False, str(e))
        
        # Generate summary
        duration = (datetime.now() - start_time).seconds
        logger.info(f"API update completed: {successful_updates}/{total_apis} successful in {duration}s")
        
        # Update current context file
        self.update_context_file()
        
        return {
            'status': 'completed',
            'successful_updates': successful_updates,
            'total_apis': total_apis,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }

    def should_update(self, api_name: str, frequency: str) -> bool:
        """Check if API should be updated based on frequency"""
        last_update = self.get_last_update_time(api_name)
        now = datetime.now()
        
        if frequency == 'daily':
            return (now - last_update).days >= 1
        elif frequency == 'hourly':
            return (now - last_update).seconds >= 3600
        elif frequency == 'weekly':
            return (now - last_update).days >= 7
        
        return True  # Default to update

    def get_last_update_time(self, api_name: str) -> datetime:
        """Get last update time for a specific API"""
        try:
            if os.path.exists(self.last_update_file):
                with open(self.last_update_file, 'r') as f:
                    data = json.load(f)
                    update_time = data.get(api_name, {}).get('last_update')
                    if update_time:
                        return datetime.fromisoformat(update_time)
        except Exception as e:
            logger.warning(f"Error reading last update time for {api_name}: {e}")
        
        return datetime.now() - timedelta(days=1)  # Default to yesterday

    def record_update(self, api_name: str, success: bool, error: str = None):
        """Record update attempt"""
        try:
            update_data = {}
            if os.path.exists(self.last_update_file):
                with open(self.last_update_file, 'r') as f:
                    update_data = json.load(f)
            
            update_data[api_name] = {
                'last_update': datetime.now().isoformat(),
                'success': success,
                'error': error
            }
            
            with open(self.last_update_file, 'w') as f:
                json.dump(update_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error recording update for {api_name}: {e}")

    def update_context_file(self):
        """Update the context file with latest data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest sports data
            cursor.execute('''
                SELECT team_code, team_name, captain, vice_captain, season, tournament
                FROM sports_data
                WHERE tournament = 'IPL' AND season = '2024'
            ''')
            
            sports_data = {}
            for row in cursor.fetchall():
                team_code, team_name, captain, vice_captain, season, tournament = row
                sports_data[f"{team_code}_captain"] = {
                    'team': team_name,
                    'captain': captain,
                    'vice_captain': vice_captain,
                    'season': season,
                    'updated_from': 'api_data'
                }
            
            # Get other current info
            cursor.execute('''
                SELECT category, subcategory, key_info, value_info, source, last_updated
                FROM current_info
                WHERE last_updated > datetime('now', '-7 days')
                ORDER BY last_updated DESC
            ''')
            
            current_info = {}
            for row in cursor.fetchall():
                category, subcategory, key_info, value_info, source, last_updated = row
                current_info[key_info] = {
                    'category': category,
                    'subcategory': subcategory,
                    'value': value_info,
                    'source': source,
                    'last_updated': last_updated
                }
            
            # Create comprehensive context
            context = {
                'last_updated': datetime.now().isoformat(),
                'sports_data': sports_data,
                'current_info': current_info,
                'data_sources': 'real_time_apis',
                'update_method': 'automated_daily'
            }
            
            # Save to context file
            with open('api_current_context.json', 'w') as f:
                json.dump(context, f, indent=2)
            
            logger.info("Context file updated with API data")
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating context file: {e}")

    def get_current_data(self, query: str) -> List[str]:
        """Get current data for a query from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query_lower = query.lower()
            results = []
            
            # Check sports data
            if any(term in query_lower for term in ['captain', 'rcb', 'csk', 'mi', 'ipl']):
                cursor.execute('''
                    SELECT team_name, captain, last_updated
                    FROM sports_data
                    WHERE tournament = 'IPL'
                    ORDER BY last_updated DESC
                    LIMIT 5
                ''')
                
                for row in cursor.fetchall():
                    team_name, captain, last_updated = row
                    if any(team.lower() in query_lower for team in [team_name.lower(), team_name.split()[-1].lower()]):
                        results.append(f"✅ API Data: {team_name} Captain is {captain} (Updated: {last_updated[:10]})")
            
            # Check current info
            cursor.execute('''
                SELECT key_info, value_info, source, last_updated
                FROM current_info
                WHERE last_updated > datetime('now', '-7 days')
                ORDER BY last_updated DESC
            ''')
            
            for row in cursor.fetchall():
                key_info, value_info, source, last_updated = row
                if any(term in key_info.lower() for term in query_lower.split()):
                    results.append(f"📊 {key_info}: {value_info} (Source: {source}, Updated: {last_updated[:10]})")
            
            conn.close()
            
            if not results:
                results.append("No recent API data found for this query - will use general knowledge")
            
            return results[:3]  # Limit to 3 most relevant results
            
        except Exception as e:
            logger.error(f"Error getting current data: {e}")
            return [f"Error accessing API data: {e}"]

    def start_scheduler(self):
        """Start the automated daily scheduler"""
        logger.info("Starting API auto-updater scheduler...")
        
        # Schedule daily update at 6 AM
        schedule.every().day.at("06:00").do(self.daily_update)
        
        # Run immediately if no recent updates
        last_update = self.get_last_update_time('general_system')
        if (datetime.now() - last_update).hours >= 24:
            logger.info("No recent updates found, running immediate update...")
            self.daily_update()
        
        logger.info("Scheduler started. Daily updates at 6:00 AM")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function"""
    updater = APIDataUpdater()
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'update':
            result = updater.daily_update()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'schedule':
            updater.start_scheduler()
        elif sys.argv[1] == 'test':
            # Test query
            test_query = sys.argv[2] if len(sys.argv) > 2 else "RCB captain"
            results = updater.get_current_data(test_query)
            print(f"\nTest Query: '{test_query}'")
            for result in results:
                print(f"  {result}")
        else:
            print("Usage: python api_updater.py [update|schedule|test]")
    else:
        print("Echo Mind API Auto-Updater")
        print("Usage:")
        print("  python api_updater.py update    - Run update once")
        print("  python api_updater.py schedule  - Start daily scheduler")
        print("  python api_updater.py test 'query' - Test data retrieval")

if __name__ == '__main__':
    main()