import os
import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import SessionPasswordNeededError

# Configure logging
logger = logging.getLogger("TelegramScraper")

# Import database utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_utils import add_data_source, add_raw_data, get_data_sources
import config

class TelegramScraper:
    """Scraper for Telegram channels and groups"""
    
    def __init__(self, api_id=None, api_hash=None, phone=None, session_name="telegram_scraper"):
        """Initialize the Telegram scraper"""
        self.api_id = api_id or os.environ.get("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.environ.get("TELEGRAM_API_HASH")
        self.phone = phone or os.environ.get("TELEGRAM_PHONE")
        self.session_name = session_name
        self.client = None
        
        if not self.api_id or not self.api_hash:
            logger.error("Telegram API credentials not set. Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables")
    
    async def connect(self, password=None):
        """Connect to Telegram API"""
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(self.phone)
                try:
                    await self.client.sign_in(self.phone, input('Enter the code: '))
                except SessionPasswordNeededError:
                    await self.client.sign_in(password=password or input('Password: '))
            
            logger.info("Connected to Telegram API")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Telegram: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram API"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram API")
    
    async def get_channel_info(self, channel_id_or_username):
        """Get information about a channel"""
        try:
            entity = await self.client.get_entity(channel_id_or_username)
            full_channel = await self.client(GetFullChannelRequest(channel=entity))
            
            return {
                "id": entity.id,
                "title": entity.title,
                "username": getattr(entity, "username", None),
                "description": full_channel.full_chat.about,
                "member_count": full_channel.full_chat.participants_count,
                "type": "channel" if getattr(entity, "broadcast", False) else "group"
            }
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_id_or_username}: {str(e)}")
            return None
    
    async def fetch_messages(self, channel_id_or_username, limit=100, offset_date=None):
        """Fetch messages from a channel or group"""
        try:
            entity = await self.client.get_entity(channel_id_or_username)
            
            if not offset_date:
                offset_date = datetime.now()
            
            messages = []
            
            # Fetch messages
            history = await self.client(GetHistoryRequest(
                peer=entity,
                limit=limit,
                offset_date=offset_date,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            # Process messages
            for message in history.messages:
                if not message.message:
                    continue
                    
                # Create a message dictionary
                msg_data = {
                    "id": message.id,
                    "date": message.date.isoformat(),
                    "text": message.message,
                    "channel_id": entity.id,
                    "channel_name": entity.title,
                    "username": getattr(entity, "username", None),
                    "has_media": message.media is not None,
                    "views": getattr(message, "views", 0),
                    "forwards": getattr(message, "forwards", 0)
                }
                
                messages.append(msg_data)
            
            logger.info(f"Fetched {len(messages)} messages from {getattr(entity, 'title', channel_id_or_username)}")
            return messages
        except Exception as e:
            logger.error(f"Error fetching messages from {channel_id_or_username}: {str(e)}")
            return []
    
    async def fetch_channels(self, channels, days_ago=1, messages_per_channel=50):
        """Fetch messages from multiple channels"""
        if not self.client:
            logger.error("Client not connected. Call connect() first.")
            return
        
        all_messages = []
        offset_date = datetime.now() - timedelta(days=days_ago)
        
        for channel in channels:
            channel_id = channel.get("id") or channel.get("name")
            if not channel_id:
                logger.warning(f"Invalid channel configuration: {channel}")
                continue
            
            # Get channel info
            channel_info = await self.get_channel_info(channel_id)
            if not channel_info:
                logger.warning(f"Could not get info for channel {channel_id}")
                continue
            
            # Register the channel as a data source if it doesn't exist
            source_type = "telegram_" + channel_info["type"]
            source_name = channel_info["title"]
            source_id = str(channel_info["id"])
            
            # Check if source already exists
            existing_sources = get_data_sources(source_type)
            if not any(s["source_id"] == source_id for s in existing_sources):
                source_url = f"https://t.me/{channel_info['username']}" if channel_info["username"] else None
                source_id = add_data_source({
                    "source_type": source_type,
                    "source_name": source_name,
                    "source_id": source_id,
                    "source_url": source_url
                })
                logger.info(f"Added new data source: {source_name} ({source_type})")
            else:
                # Find the source ID in the database
                for s in existing_sources:
                    if s["source_id"] == source_id:
                        source_id = s["id"]
                        break
            
            # Fetch messages
            messages = await self.fetch_messages(
                channel_id, 
                limit=messages_per_channel,
                offset_date=offset_date
            )
            
            # Store messages in the database
            for message in messages:
                # Create a hash of the message content to avoid duplicates
                content_hash = hashlib.md5(
                    (str(message["id"]) + message["channel_id"] + message["text"]).encode()
                ).hexdigest()
                
                # Store the raw data
                add_raw_data(
                    source_id=source_id,
                    content=message["text"],
                    metadata=json.dumps(message),
                    content_hash=content_hash
                )
            
            all_messages.extend(messages)
            
            # Sleep to avoid rate limiting
            await asyncio.sleep(1)
        
        return all_messages
    
    async def listen_to_channels(self, channels, handler=None):
        """Listen to new messages from channels in real-time"""
        if not self.client:
            logger.error("Client not connected. Call connect() first.")
            return
        
        @self.client.on(events.NewMessage(chats=channels))
        async def handle_new_message(event):
            """Handle new message event"""
            try:
                message = event.message
                chat = await event.get_chat()
                
                # Create message data
                msg_data = {
                    "id": message.id,
                    "date": message.date.isoformat(),
                    "text": message.message,
                    "channel_id": chat.id,
                    "channel_name": getattr(chat, "title", str(chat.id)),
                    "username": getattr(chat, "username", None),
                    "has_media": message.media is not None
                }
                
                logger.info(f"New message in {msg_data['channel_name']}: {msg_data['text'][:50]}...")
                
                # Call the custom handler if provided
                if handler:
                    await handler(msg_data)
            except Exception as e:
                logger.error(f"Error handling new message: {str(e)}")
        
        # Run the client until disconnected
        logger.info(f"Listening to {len(channels)} channels for new messages...")
        await self.client.run_until_disconnected()


async def scrape_channels(scraper, days=1, messages_per_channel=50):
    """Scrape channels from configuration"""
    # Get channels from configuration
    telegram_sources = config.sources.get("telegram", [])
    
    if not telegram_sources:
        logger.warning("No Telegram sources configured")
        return
    
    # Connect to Telegram
    connected = await scraper.connect()
    if not connected:
        return
    
    try:
        # Fetch messages from all channels
        messages = await scraper.fetch_channels(
            telegram_sources,
            days_ago=days,
            messages_per_channel=messages_per_channel
        )
        
        logger.info(f"Scraped {len(messages)} messages from {len(telegram_sources)} channels")
    finally:
        # Disconnect from Telegram
        await scraper.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape Telegram channels")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages per channel")
    parser.add_argument("--api-id", type=str, help="Telegram API ID")
    parser.add_argument("--api-hash", type=str, help="Telegram API Hash")
    parser.add_argument("--phone", type=str, help="Phone number")
    args = parser.parse_args()
    
    # Create scraper
    scraper = TelegramScraper(
        api_id=args.api_id,
        api_hash=args.api_hash,
        phone=args.phone
    )
    
    # Run the scraper
    asyncio.run(scrape_channels(
        scraper,
        days=args.days,
        messages_per_channel=args.limit
    )) 