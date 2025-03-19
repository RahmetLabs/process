#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import components
from data_collection.telegram_scraper import TelegramScraper, scrape_channels
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("collection_service.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CollectionService")

# Check if other scrapers are available
try:
    from data_collection.twitter_scraper import TwitterScraper, scrape_tweets
    twitter_available = True
except ImportError:
    twitter_available = False
    logger.warning("Twitter scraper not available")

try:
    from data_collection.discord_scraper import DiscordScraper, scrape_discord
    discord_available = True
except ImportError:
    discord_available = False
    logger.warning("Discord scraper not available")

class CollectionService:
    """Service for collecting data from various sources"""
    
    def __init__(self):
        """Initialize the collection service"""
        self.telegram_scraper = None
        self.twitter_scraper = None
        self.discord_scraper = None
        
        # Collection settings from config
        self.settings = config.get('data_collection')
        
        # Collection intervals
        self.intervals = {
            'telegram': self.settings.get('fetch_interval', {}).get('telegram', 5) * 60,
            'twitter': self.settings.get('fetch_interval', {}).get('twitter', 15) * 60,
            'discord': self.settings.get('fetch_interval', {}).get('discord', 30) * 60
        }
        
        # Last collection times
        self.last_collection = {
            'telegram': 0,
            'twitter': 0,
            'discord': 0
        }
    
    async def initialize(self):
        """Initialize scrapers"""
        # Initialize Telegram scraper
        self.telegram_scraper = TelegramScraper()
        
        # Initialize Twitter scraper if available
        if twitter_available:
            self.twitter_scraper = TwitterScraper()
        
        # Initialize Discord scraper if available
        if discord_available:
            self.discord_scraper = DiscordScraper()
        
        logger.info("Collection service initialized")
    
    async def collect_telegram(self):
        """Run Telegram collection"""
        try:
            logger.info("Starting Telegram collection")
            await scrape_channels(self.telegram_scraper, days=1, messages_per_channel=50)
            self.last_collection['telegram'] = time.time()
            logger.info("Telegram collection completed")
            return True
        except Exception as e:
            logger.error(f"Error in Telegram collection: {str(e)}")
            return False
    
    async def collect_twitter(self):
        """Run Twitter collection"""
        if not twitter_available or not self.twitter_scraper:
            logger.warning("Twitter scraper not available")
            return False
        
        try:
            logger.info("Starting Twitter collection")
            # Assuming the twitter scraper has a similar interface
            await scrape_tweets(self.twitter_scraper)
            self.last_collection['twitter'] = time.time()
            logger.info("Twitter collection completed")
            return True
        except Exception as e:
            logger.error(f"Error in Twitter collection: {str(e)}")
            return False
    
    async def collect_discord(self):
        """Run Discord collection"""
        if not discord_available or not self.discord_scraper:
            logger.warning("Discord scraper not available")
            return False
        
        try:
            logger.info("Starting Discord collection")
            # Assuming the discord scraper has a similar interface
            await scrape_discord(self.discord_scraper)
            self.last_collection['discord'] = time.time()
            logger.info("Discord collection completed")
            return True
        except Exception as e:
            logger.error(f"Error in Discord collection: {str(e)}")
            return False
    
    async def collect_all(self):
        """Collect data from all available sources"""
        results = {
            'telegram': await self.collect_telegram(),
            'twitter': await self.collect_twitter() if twitter_available else False,
            'discord': await self.collect_discord() if discord_available else False
        }
        
        success_count = sum(1 for result in results.values() if result)
        total_count = len([k for k, v in results.items() if k in ['telegram', 'twitter', 'discord'] and v is not False])
        
        logger.info(f"Collection completed: {success_count}/{total_count} sources successful")
        
        return results
    
    async def run_continuous(self, interval: int = 300, max_runs: int = None):
        """Run collection continuously with the specified interval"""
        logger.info(f"Starting continuous collection (interval: {interval} seconds)")
        
        run_count = 0
        
        try:
            await self.initialize()
            
            while True:
                current_time = time.time()
                
                # Check if we need to collect from each source
                collection_tasks = []
                
                # Telegram collection
                if current_time - self.last_collection['telegram'] >= self.intervals['telegram']:
                    collection_tasks.append(self.collect_telegram())
                
                # Twitter collection
                if twitter_available and current_time - self.last_collection['twitter'] >= self.intervals['twitter']:
                    collection_tasks.append(self.collect_twitter())
                
                # Discord collection
                if discord_available and current_time - self.last_collection['discord'] >= self.intervals['discord']:
                    collection_tasks.append(self.collect_discord())
                
                # Run collection tasks
                if collection_tasks:
                    logger.info(f"Running {len(collection_tasks)} collection tasks")
                    await asyncio.gather(*collection_tasks)
                    run_count += 1
                else:
                    logger.info("No collection tasks needed at this time")
                
                # Check if max runs reached
                if max_runs and run_count >= max_runs:
                    logger.info(f"Reached maximum number of runs ({max_runs}). Stopping.")
                    break
                
                # Sleep until next check
                await asyncio.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("Continuous collection interrupted by user")
        except Exception as e:
            logger.error(f"Error in continuous collection: {str(e)}")
        
        logger.info(f"Continuous collection completed after {run_count} runs")

async def main_async():
    """Async main function for running the collection service"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Collect data from various sources')
    
    # Collection options
    parser.add_argument('--telegram', action='store_true', help='Collect from Telegram')
    parser.add_argument('--twitter', action='store_true', help='Collect from Twitter')
    parser.add_argument('--discord', action='store_true', help='Collect from Discord')
    parser.add_argument('--all', action='store_true', help='Collect from all available sources')
    
    # Continuous mode options
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300)')
    parser.add_argument('--runs', type=int, default=None, help='Maximum number of runs')
    
    # Other options
    parser.add_argument('--days', type=int, default=1, help='Number of days to look back for data')
    parser.add_argument('--limit', type=int, default=50, help='Maximum items per source')
    
    args = parser.parse_args()
    
    # Initialize collection service
    service = CollectionService()
    await service.initialize()
    
    # Handle continuous mode
    if args.continuous:
        await service.run_continuous(interval=args.interval, max_runs=args.runs)
        return
    
    # Handle specific collection requests
    if args.all:
        await service.collect_all()
    else:
        collection_tasks = []
        
        if args.telegram:
            collection_tasks.append(service.collect_telegram())
        
        if args.twitter and twitter_available:
            collection_tasks.append(service.collect_twitter())
        
        if args.discord and discord_available:
            collection_tasks.append(service.collect_discord())
        
        if not collection_tasks:
            logger.warning("No collection sources specified")
            return
        
        results = await asyncio.gather(*collection_tasks)
        
        success_count = sum(1 for result in results if result)
        logger.info(f"Collection completed: {success_count}/{len(collection_tasks)} sources successful")

def main():
    """Main function for running the collection service"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 