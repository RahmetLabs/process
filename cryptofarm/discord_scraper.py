#!/usr/bin/env python3
"""
Discord scraper for CryptoFarm.
Collects messages from Discord channels using discord.py library.
"""

import asyncio
import datetime
import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add parent directory to path to import db_utils
sys.path.append(str(Path(__file__).parent))
from db_utils import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='discord_scraper.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Add console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

class DiscordScraper:
    """Discord scraper for collecting messages from Discord channels."""
    
    def __init__(self, db_path: str = 'data/cryptofarm.db', config_path: str = 'config/main.json'):
        """Initialize the Discord scraper."""
        # Load environment variables
        load_dotenv()
        
        # Set up database manager
        self.db_manager = DatabaseManager(db_path)
        
        # Load configuration
        self.config_path = config_path
        self.load_config()
        
        # Set up Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # Set up event handlers
        self.setup_event_handlers()
        
        # Discord sources
        self.sources = []
        self.channels_to_monitor = {}
        self.last_collection_time = {}
        
        # Ready flag
        self.is_ready = asyncio.Event()
        
        # Token
        self.token = os.getenv('DISCORD_BOT_TOKEN')
        if not self.token:
            logger.error("DISCORD_BOT_TOKEN not found in environment variables")
            raise ValueError("DISCORD_BOT_TOKEN not found")
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Discord collection settings
            collection_settings = config.get('collection', {}).get('discord', {})
            self.message_limit = collection_settings.get('message_limit', 100)
            self.historical_days = collection_settings.get('historical_days', 7)
            self.collection_interval = collection_settings.get('collection_interval', 3600)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Set defaults
            self.message_limit = 100
            self.historical_days = 7
            self.collection_interval = 3600
    
    def setup_event_handlers(self):
        """Set up Discord event handlers."""
        
        @self.bot.event
        async def on_ready():
            """Called when the bot is ready."""
            logger.info(f"Logged in as {self.bot.user.name}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            
            # Load Discord sources from database
            await self.load_sources()
            
            # Set ready flag
            self.is_ready.set()
        
        @self.bot.event
        async def on_message(message):
            """Called when a message is received."""
            # Skip messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Check if the message is from a monitored channel
            if message.channel.id in self.channels_to_monitor:
                await self.store_message(message)
            
            # Process commands
            await self.bot.process_commands(message)
    
    async def load_sources(self):
        """Load Discord sources from database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get Discord sources
            cursor.execute(
                "SELECT id, name, source_id, priority, metadata FROM sources WHERE source_type = 'discord'"
            )
            
            sources = cursor.fetchall()
            self.sources = []
            
            for source in sources:
                source_id, name, channel_id, priority, metadata_str = source
                metadata = json.loads(metadata_str) if metadata_str else {}
                
                self.sources.append({
                    'id': source_id,
                    'name': name,
                    'channel_id': channel_id,
                    'priority': priority,
                    'metadata': metadata
                })
                
                # Add to channels to monitor
                self.channels_to_monitor[int(channel_id)] = source_id
                
                # Initialize last collection time
                self.last_collection_time[channel_id] = datetime.datetime.now() - datetime.timedelta(days=self.historical_days)
            
            logger.info(f"Loaded {len(self.sources)} Discord sources from database.")
            
        except Exception as e:
            logger.error(f"Error loading Discord sources: {e}")
    
    async def store_message(self, message):
        """Store a Discord message in the database."""
        try:
            # Get source ID from channel ID
            source_id = self.channels_to_monitor.get(message.channel.id)
            if not source_id:
                return
            
            # Extract message content
            content = message.content
            
            # Extract attachments, if any
            attachments = []
            for attachment in message.attachments:
                attachments.append({
                    'url': attachment.url,
                    'filename': attachment.filename,
                    'content_type': attachment.content_type,
                    'size': attachment.size
                })
            
            # Extract embeds, if any
            embeds = []
            for embed in message.embeds:
                embeds.append(embed.to_dict())
            
            # Create metadata
            metadata = {
                'author': {
                    'id': str(message.author.id),
                    'name': message.author.name,
                    'display_name': message.author.display_name
                },
                'channel': {
                    'id': str(message.channel.id),
                    'name': message.channel.name
                },
                'guild': {
                    'id': str(message.guild.id),
                    'name': message.guild.name
                } if message.guild else None,
                'attachments': attachments,
                'embeds': embeds,
                'mentions': [str(user.id) for user in message.mentions],
                'reference': str(message.reference.message_id) if message.reference else None
            }
            
            # Insert message into database
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR IGNORE INTO messages
                (source_id, message_id, content, timestamp, processed, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id, 
                    str(message.id),
                    content,
                    message.created_at.isoformat(),
                    False,
                    json.dumps(metadata)
                )
            )
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing Discord message: {e}")
    
    async def collect_historical_messages(self, channel, since_time=None):
        """Collect historical messages from a Discord channel."""
        try:
            if since_time is None:
                since_time = datetime.datetime.now() - datetime.timedelta(days=self.historical_days)
            
            source_id = self.channels_to_monitor.get(channel.id)
            if not source_id:
                logger.warning(f"Channel {channel.id} not found in monitored channels")
                return 0
            
            logger.info(f"Collecting messages from channel {channel.name} (ID: {channel.id}) since {since_time}")
            
            # Get the most recent messages
            messages = []
            async for message in channel.history(limit=self.message_limit, after=since_time):
                messages.append(message)
            
            # Store each message
            count = 0
            for message in messages:
                await self.store_message(message)
                count += 1
            
            # Update last collection time
            self.last_collection_time[str(channel.id)] = datetime.datetime.now()
            
            logger.info(f"Collected {count} messages from channel {channel.name}")
            return count
            
        except Exception as e:
            logger.error(f"Error collecting historical messages: {e}")
            return 0
    
    async def collect_all_channels(self):
        """Collect messages from all monitored channels."""
        if not self.is_ready.is_set():
            logger.warning("Discord bot not ready yet. Waiting...")
            await self.is_ready.wait()
        
        total_count = 0
        
        for channel_id, source_id in self.channels_to_monitor.items():
            try:
                # Get channel object
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    logger.warning(f"Channel {channel_id} not found. Skipping.")
                    continue
                
                # Get last collection time
                since_time = self.last_collection_time.get(str(channel_id))
                
                # Collect messages
                count = await self.collect_historical_messages(channel, since_time)
                total_count += count
                
                # Avoid rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error collecting messages from channel {channel_id}: {e}")
        
        return total_count
    
    async def run_continuous_collection(self, interval=None):
        """Run continuous collection with the specified interval."""
        interval = interval or self.collection_interval
        
        logger.info(f"Starting continuous Discord collection with interval of {interval} seconds.")
        
        try:
            while True:
                start_time = time.time()
                
                # Collect messages
                count = await self.collect_all_channels()
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                logger.info(f"Collected {count} Discord messages. Sleeping for {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Continuous collection stopped by user.")
        except Exception as e:
            logger.error(f"Error in continuous collection: {e}")
    
    async def start(self):
        """Start the Discord bot."""
        try:
            await self.bot.start(self.token)
        except KeyboardInterrupt:
            logger.info("Discord scraper stopped by user.")
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
    
    def run(self):
        """Run the Discord scraper synchronously."""
        asyncio.run(self.start())
    
    async def close(self):
        """Close the Discord bot."""
        await self.bot.close()

async def main_async():
    """Async main function to run the Discord scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run the Discord scraper.')
    parser.add_argument('--db-path', default='data/cryptofarm.db', help='Path to the database file')
    parser.add_argument('--config', default='config/main.json', help='Path to the configuration file')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--interval', type=int, help='Collection interval in seconds (for continuous mode)')
    args = parser.parse_args()
    
    try:
        scraper = DiscordScraper(args.db_path, args.config)
        
        # Start the bot in the background
        bot_task = asyncio.create_task(scraper.start())
        
        # Wait for bot to be ready
        await scraper.is_ready.wait()
        
        if args.continuous:
            # Run continuous collection
            collection_task = asyncio.create_task(scraper.run_continuous_collection(args.interval))
            
            # Wait for both tasks
            await asyncio.gather(bot_task, collection_task)
        else:
            # Collect once
            await scraper.collect_all_channels()
            
            # Close bot
            await scraper.close()
            
    except KeyboardInterrupt:
        logger.info("Discord scraper stopped by user.")
    except Exception as e:
        logger.error(f"Discord scraper failed: {e}")
        if 'scraper' in locals():
            await scraper.close()

def main():
    """Main function to run the Discord scraper."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 