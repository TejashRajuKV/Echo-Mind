#!/usr/bin/env python3
"""
Echo Mind Auto-Update System
Automatically updates fact-checking data daily from trusted news sources
"""

import os
import json
import time
import schedule
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import feedparser
import sqlite3
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    title: str
    description: str
    url: str
    source: str
    published_date: datetime
    category: str

class AutoUpdater:
    def __init__(self):
        # API Configuration
        self.newsapi_key = os.environ.get('NEWSAPI_KEY', 'YOUR_NEWS_API_KEY')
        self.update_log_file = 'last_update.json'
        
        # News sources and their RSS feeds
        self.news_sources = {
            'BBC': 'http://feeds.bbci.co.uk/news/rss.xml',
            'Reuters': 'http://feeds.reuters.com/reuters/topNews',
            'The Hindu': 'https://www.thehindu.com/news/feeder/default.rss',
            'India Today': 'https://www.indiatoday.in/rss/1206578',
            'Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms'
        }
        
        # Political keywords to track
        self.political_keywords = [
            'chief minister', 'cm', 'prime minister', 'pm', 'president',
            'election', 'government', 'minister', 'parliament', 'assembly',
            'andhra pradesh', 'telangana', 'karnataka', 'tamil nadu', 'kerala'
        ]
        
        # Health and science keywords
        self.health_keywords = [
            'covid', 'vaccine', 'health', 'medical', 'disease', 'treatment',
            'who', 'fda', 'clinical trial', 'research study'
        ]
        
        self.db_path = 'factchecks.db'
        self.current_context_file = 'current_context.json'

    def get_last_update_time(self) -> datetime:
        """Get the last update timestamp"""
        try:
            if os.path.exists(self.update_log_file):
                with open(self.update_log_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data.get('last_update', '2024-01-01T00:00:00'))
            return datetime.now() - timedelta(days=1)
        except Exception as e:
            logger.error(f"Error reading last update time: {e}")
            return datetime.now() - timedelta(days=1)

    def save_last_update_time(self):
        """Save the current timestamp as last update"""
        try:
            with open(self.update_log_file, 'w') as f:
                json.dump({
                    'last_update': datetime.now().isoformat(),
                    'status': 'success'
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving last update time: {e}")

    def fetch_news_from_rss(self, source_name: str, rss_url: str) -> List[NewsItem]:
        """Fetch news from RSS feed"""
        try:
            logger.info(f"Fetching news from {source_name}")
            feed = feedparser.parse(rss_url)
            news_items = []
            
            for entry in feed.entries[:10]:  # Get latest 10 articles
                try:
                    published_date = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_date = datetime(*entry.published_parsed[:6])
                    
                    news_item = NewsItem(
                        title=entry.title,
                        description=entry.get('summary', entry.get('description', '')),
                        url=entry.link,
                        source=source_name,
                        published_date=published_date,
                        category=self.categorize_news(entry.title + ' ' + entry.get('summary', ''))
                    )
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"Error parsing news item from {source_name}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(news_items)} items from {source_name}")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching news from {source_name}: {e}")
            return []

    def fetch_news_from_newsapi(self) -> List[NewsItem]:
        """Fetch news from NewsAPI (if API key is available)"""
        if self.newsapi_key == 'YOUR_NEWS_API_KEY':
            logger.info("NewsAPI key not configured, skipping NewsAPI fetch")
            return []
        
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'apiKey': self.newsapi_key,
                'country': 'in',  # India
                'category': 'general',
                'pageSize': 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            news_items = []
            for article in data.get('articles', []):
                try:
                    published_date = datetime.now()
                    if article.get('publishedAt'):
                        published_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                    
                    news_item = NewsItem(
                        title=article['title'],
                        description=article.get('description', ''),
                        url=article['url'],
                        source=article.get('source', {}).get('name', 'NewsAPI'),
                        published_date=published_date,
                        category=self.categorize_news(article['title'] + ' ' + article.get('description', ''))
                    )
                    news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"Error parsing NewsAPI item: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(news_items)} items from NewsAPI")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []

    def categorize_news(self, text: str) -> str:
        """Categorize news based on content"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in self.political_keywords):
            return 'politics'
        elif any(keyword in text_lower for keyword in self.health_keywords):
            return 'health'
        elif any(keyword in text_lower for keyword in ['stock', 'market', 'economy', 'finance', 'crypto']):
            return 'finance'
        elif any(keyword in text_lower for keyword in ['climate', 'environment', 'global warming', 'pollution']):
            return 'environment'
        else:
            return 'general'

    def extract_political_updates(self, news_items: List[NewsItem]) -> Dict[str, str]:
        """Extract current political information from news"""
        political_updates = {}
        
        for item in news_items:
            if item.category == 'politics':
                text = (item.title + ' ' + item.description).lower()
                
                # Check for CM updates
                if 'chief minister' in text or ' cm ' in text:
                    for state in ['andhra pradesh', 'telangana', 'karnataka', 'tamil nadu', 'kerala']:
                        if state in text:
                            political_updates[f"{state}_cm"] = {
                                'title': item.title,
                                'description': item.description,
                                'source': item.source,
                                'url': item.url,
                                'date': item.published_date.isoformat()
                            }
                
                # Check for PM updates
                if 'prime minister' in text or ' pm ' in text:
                    political_updates['prime_minister'] = {
                        'title': item.title,
                        'description': item.description,
                        'source': item.source,
                        'url': item.url,
                        'date': item.published_date.isoformat()
                    }
        
        return political_updates

    def update_current_context(self, news_items: List[NewsItem]):
        """Update the current context file with latest information"""
        try:
            political_updates = self.extract_political_updates(news_items)
            
            current_context = {
                'last_updated': datetime.now().isoformat(),
                'political_updates': political_updates,
                'recent_news_count': len(news_items),
                'categories': {},
                'trusted_sources': list(set([item.source for item in news_items]))
            }
            
            # Count by category
            for item in news_items:
                current_context['categories'][item.category] = current_context['categories'].get(item.category, 0) + 1
            
            with open(self.current_context_file, 'w') as f:
                json.dump(current_context, f, indent=2)
            
            logger.info(f"Updated current context with {len(political_updates)} political updates")
            
        except Exception as e:
            logger.error(f"Error updating current context: {e}")

    def update_database_with_news(self, news_items: List[NewsItem]):
        """Add relevant news items to the fact-check database"""
        try:
            # Import database helper
            from database_helper import add_fact_check_to_database
            
            for item in news_items:
                # Only add items that could serve as fact-checks
                if item.category in ['politics', 'health', 'environment'] and len(item.description) > 50:
                    try:
                        # Create a fact-check entry from news
                        fact_check_data = {
                            'claim': item.title,
                            'verdict': 'Trustworthy',  # News from trusted sources
                            'source': item.source,
                            'url': item.url,
                            'explanation': item.description,
                            'category': item.category,
                            'date_added': datetime.now().isoformat()
                        }
                        
                        add_fact_check_to_database(fact_check_data)
                        
                    except Exception as e:
                        logger.warning(f"Error adding news item to database: {e}")
                        continue
            
            logger.info(f"Added relevant news items to database")
            
        except Exception as e:
            logger.error(f"Error updating database with news: {e}")

    def daily_update(self):
        """Perform daily update of all data sources"""
        logger.info("Starting daily update process...")
        start_time = datetime.now()
        
        try:
            all_news_items = []
            
            # Fetch from RSS feeds
            for source_name, rss_url in self.news_sources.items():
                news_items = self.fetch_news_from_rss(source_name, rss_url)
                all_news_items.extend(news_items)
                time.sleep(1)  # Be respectful to news sources
            
            # Fetch from NewsAPI if available
            newsapi_items = self.fetch_news_from_newsapi()
            all_news_items.extend(newsapi_items)
            
            # Filter for recent items (last 24 hours)
            recent_items = [
                item for item in all_news_items 
                if (datetime.now() - item.published_date).days <= 1
            ]
            
            logger.info(f"Collected {len(recent_items)} recent news items from {len(all_news_items)} total")
            
            # Update current context
            self.update_current_context(recent_items)
            
            # Update database
            self.update_database_with_news(recent_items)
            
            # Save successful update timestamp
            self.save_last_update_time()
            
            duration = (datetime.now() - start_time).seconds
            logger.info(f"Daily update completed successfully in {duration} seconds")
            
            return {
                'status': 'success',
                'items_processed': len(recent_items),
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Daily update failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_current_context(self) -> Dict:
        """Get the current context for AI prompts"""
        try:
            if os.path.exists(self.current_context_file):
                with open(self.current_context_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error reading current context: {e}")
            return {}

    def start_scheduler(self):
        """Start the daily scheduler"""
        logger.info("Starting auto-update scheduler...")
        
        # Schedule daily update at 6 AM
        schedule.every().day.at("06:00").do(self.daily_update)
        
        # Also run immediately if last update was more than 24 hours ago
        last_update = self.get_last_update_time()
        if (datetime.now() - last_update).hours >= 24:
            logger.info("Last update was more than 24 hours ago, running immediate update...")
            self.daily_update()
        
        logger.info("Scheduler started. Daily updates at 6:00 AM")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function to run the auto-updater"""
    updater = AutoUpdater()
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'update':
            # Run update once
            result = updater.daily_update()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'schedule':
            # Start scheduler
            updater.start_scheduler()
        else:
            print("Usage: python auto_updater.py [update|schedule]")
    else:
        print("Echo Mind Auto-Updater")
        print("Usage:")
        print("  python auto_updater.py update    - Run update once")
        print("  python auto_updater.py schedule  - Start daily scheduler")

if __name__ == '__main__':
    main()