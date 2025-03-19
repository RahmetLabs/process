#!/usr/bin/env python3
"""
Main data processor for CryptoFarm.
This module handles processing collected messages, running the classifiers, and identifying opportunities.
"""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import db_utils
sys.path.append(str(Path(__file__).parent.parent))
from data_classifier import DataClassifier
from opportunity_analyzer import OpportunityAnalyzer
from db_utils import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='data_processor.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Add console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

class DataProcessor:
    """
    Main data processor for CryptoFarm.
    Processes collected messages, classifies data, and identifies opportunities.
    """
    
    def __init__(self, config_path='config/main.json'):
        """Initialize the data processor with configuration."""
        try:
            self.load_config(config_path)
            self.db_manager = DatabaseManager(self.db_path)
            self.classifier = DataClassifier(self.db_path)
            self.opportunity_analyzer = OpportunityAnalyzer(self.db_path)
            self.last_processed_id = 0
            self.initialized = True
            logger.info("Data processor initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing data processor: {e}")
            self.initialized = False
            raise
    
    def load_config(self, config_path):
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Database settings
            db_settings = config.get('database', {})
            self.db_path = db_settings.get('path', 'data/cryptofarm.db')
            
            # Analysis settings
            analysis_settings = config.get('analysis', {})
            self.batch_size = analysis_settings.get('batch_size', 100)
            self.analysis_interval = analysis_settings.get('analysis_interval', 3600)
            self.opportunity_threshold = analysis_settings.get('opportunity_threshold', 0.7)
            
            # Load LLM settings if available
            llm_settings = config.get('llm', {})
            self.use_llm = llm_settings.get('enabled', False)
            self.llm_provider = llm_settings.get('provider', 'openai')
            self.llm_model = llm_settings.get('model', 'gpt-3.5-turbo')
            
            # Notification settings
            notification_settings = config.get('notifications', {})
            self.notify_new_opportunities = notification_settings.get('notify_new_opportunities', True)
            
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    async def process_new_messages(self):
        """Process new unprocessed messages from the database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get the latest processed message ID if not set
            if self.last_processed_id == 0:
                cursor.execute("SELECT MAX(id) FROM messages WHERE processed = 1")
                result = cursor.fetchone()
                if result[0] is not None:
                    self.last_processed_id = result[0]
            
            # Get unprocessed messages
            cursor.execute(
                """
                SELECT m.id, m.source_id, m.content, m.timestamp, m.metadata, 
                       s.source_type, s.name
                FROM messages m
                JOIN sources s ON m.source_id = s.id
                WHERE m.processed = 0 AND m.id > ?
                ORDER BY m.id
                LIMIT ?
                """,
                (self.last_processed_id, self.batch_size)
            )
            
            messages = cursor.fetchall()
            
            if not messages:
                logger.info("No new messages to process.")
                return 0
            
            logger.info(f"Processing {len(messages)} new messages.")
            
            # Process each message
            for message in messages:
                msg_id, source_id, content, timestamp, metadata_str, source_type, source_name = message
                
                # Parse metadata if exists
                metadata = json.loads(metadata_str) if metadata_str else {}
                
                # Classify message
                classification_results = self.classifier.classify_message(
                    msg_id, source_id, content, source_type, metadata
                )
                
                # Analyze opportunities based on classification
                if classification_results and len(classification_results) > 0:
                    for result in classification_results:
                        project_id = result.get('project_id')
                        confidence = result.get('confidence', 0)
                        
                        if project_id and confidence >= self.opportunity_threshold:
                            self.opportunity_analyzer.analyze_opportunity(
                                project_id, msg_id, source_id, result
                            )
                
                # Mark message as processed
                cursor.execute(
                    "UPDATE messages SET processed = 1 WHERE id = ?",
                    (msg_id,)
                )
                
                self.last_processed_id = msg_id
            
            conn.commit()
            logger.info(f"Processed {len(messages)} messages successfully.")
            return len(messages)
            
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            conn.rollback()
            return 0
    
    async def analyze_opportunities(self):
        """Analyze all current opportunities and update their status."""
        try:
            logger.info("Analyzing current opportunities...")
            updated = self.opportunity_analyzer.update_all_opportunities()
            logger.info(f"Updated {updated} opportunities.")
            
            # Generate alerts for high-priority opportunities
            alerts_generated = self.opportunity_analyzer.generate_alerts()
            if alerts_generated > 0:
                logger.info(f"Generated {alerts_generated} new alerts.")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error analyzing opportunities: {e}")
            return 0
    
    async def run_once(self):
        """Run a single processing cycle."""
        if not self.initialized:
            logger.error("Data processor not properly initialized.")
            return
        
        try:
            # Process new messages
            processed_count = await self.process_new_messages()
            
            # Analyze opportunities
            await self.analyze_opportunities()
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error in processing cycle: {e}")
            return 0
    
    async def run_continuous(self, interval=None):
        """Run the processor continuously with the specified interval."""
        if not self.initialized:
            logger.error("Data processor not properly initialized.")
            return
        
        interval = interval or self.analysis_interval
        
        logger.info(f"Starting continuous processing with interval of {interval} seconds.")
        
        try:
            while True:
                start_time = time.time()
                
                # Run a single processing cycle
                processed_count = await self.run_once()
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if processed_count == 0:
                    # If no messages were processed, we can sleep for the full interval
                    logger.info(f"No new messages. Sleeping for {sleep_time:.2f} seconds...")
                else:
                    # If messages were processed, we might want to process again sooner
                    sleep_time = min(sleep_time, 10)  # Max 10 seconds if there were messages
                    logger.info(f"Processed {processed_count} messages. Sleeping for {sleep_time:.2f} seconds...")
                
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Continuous processing stopped by user.")
        except Exception as e:
            logger.error(f"Error in continuous processing: {e}")
            raise

async def main_async():
    """Async main function to run the data processor."""
    parser = argparse.ArgumentParser(description='Run the CryptoFarm data processor.')
    parser.add_argument('--config', default='config/main.json', help='Path to configuration file')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, help='Processing interval in seconds (for continuous mode)')
    parser.add_argument('--process-only', action='store_true', help='Only process new messages, no opportunity analysis')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze opportunities, no message processing')
    args = parser.parse_args()
    
    try:
        processor = DataProcessor(args.config)
        
        if args.continuous:
            if args.process_only:
                logger.warning("--process-only flag is ignored in continuous mode")
            if args.analyze_only:
                logger.warning("--analyze-only flag is ignored in continuous mode")
            await processor.run_continuous(args.interval)
        else:
            if args.process_only:
                await processor.process_new_messages()
            elif args.analyze_only:
                await processor.analyze_opportunities()
            else:
                await processor.run_once()
                
    except Exception as e:
        logger.error(f"Data processor failed: {e}")
        sys.exit(1)

def main():
    """Main function to run the data processor."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Data processor stopped by user.")
    except Exception as e:
        logger.error(f"Data processor failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 