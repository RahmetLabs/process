#!/usr/bin/env python3
"""
Database setup script for CryptoFarm.
This script initializes the SQLite database with all necessary tables.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='setup_database.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Add console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

def load_config():
    """Load the main configuration file."""
    try:
        config_path = Path('config/main.json')
        if not config_path.exists():
            logger.error("Configuration file not found. Make sure config/main.json exists.")
            sys.exit(1)
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)

def get_db_path(config):
    """Get the database path from configuration."""
    db_settings = config.get('database', {})
    db_path = db_settings.get('path', 'data/cryptofarm.db')
    
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    return db_path

def create_tables(conn):
    """Create all necessary tables in the database."""
    try:
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            symbol TEXT,
            priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        ''')
        
        # Sources table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            username TEXT,
            priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            UNIQUE(source_type, source_id)
        )
        ''')
        
        # Project-source relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_sources (
            project_id INTEGER,
            source_id INTEGER,
            relationship_type TEXT,
            PRIMARY KEY (project_id, source_id),
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (source_id) REFERENCES sources (id)
        )
        ''')
        
        # Messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            message_id TEXT,
            content TEXT,
            timestamp TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE,
            metadata TEXT,
            FOREIGN KEY (source_id) REFERENCES sources (id),
            UNIQUE(source_id, message_id)
        )
        ''')
        
        # Keywords table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            keyword TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            UNIQUE(project_id, keyword)
        )
        ''')
        
        # Contracts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            chain TEXT NOT NULL,
            address TEXT NOT NULL,
            contract_type TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            UNIQUE(chain, address)
        )
        ''')
        
        # Opportunities table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            opportunity_type TEXT NOT NULL,
            source_id INTEGER,
            message_id INTEGER,
            score REAL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (source_id) REFERENCES sources (id),
            FOREIGN KEY (message_id) REFERENCES messages (id)
        )
        ''')
        
        # Alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            alert_type TEXT NOT NULL,
            severity TEXT,
            message TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        ''')
        
        # Stats table for analytics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_type TEXT NOT NULL,
            stat_date DATE NOT NULL,
            value REAL,
            metadata TEXT,
            UNIQUE(stat_type, stat_date)
        )
        ''')
        
        conn.commit()
        logger.info("All tables created successfully.")
        
    except sqlite3.Error as e:
        logger.error(f"Error creating tables: {e}")
        conn.rollback()
        sys.exit(1)

def import_projects_from_config(conn):
    """Import projects from the projects.json config file."""
    try:
        projects_path = Path('config/projects.json')
        if not projects_path.exists():
            logger.warning("Projects config file not found. Skipping project import.")
            return
            
        with open(projects_path, 'r') as f:
            projects_config = json.load(f)
        
        cursor = conn.cursor()
        
        # Process high priority projects
        for project in projects_config.get('high_priority', []):
            metadata = {k: v for k, v in project.items() if k not in ['name', 'symbol']}
            metadata_json = json.dumps(metadata)
            
            cursor.execute('''
            INSERT OR REPLACE INTO projects (name, symbol, priority, metadata)
            VALUES (?, ?, ?, ?)
            ''', (project['name'], project.get('symbol', ''), 'high', metadata_json))
            
            project_id = cursor.lastrowid
            
            # Insert keywords
            for keyword in project.get('keywords', []):
                cursor.execute('''
                INSERT OR IGNORE INTO keywords (project_id, keyword)
                VALUES (?, ?)
                ''', (project_id, keyword))
                
            # Insert contracts
            for contract in project.get('contracts', []):
                cursor.execute('''
                INSERT OR IGNORE INTO contracts (project_id, chain, address, contract_type)
                VALUES (?, ?, ?, ?)
                ''', (project_id, contract['chain'], contract['address'], contract.get('type', 'main')))
        
        # Process medium priority projects
        for project in projects_config.get('medium_priority', []):
            metadata = {k: v for k, v in project.items() if k not in ['name', 'symbol']}
            metadata_json = json.dumps(metadata)
            
            cursor.execute('''
            INSERT OR REPLACE INTO projects (name, symbol, priority, metadata)
            VALUES (?, ?, ?, ?)
            ''', (project['name'], project.get('symbol', ''), 'medium', metadata_json))
            
            project_id = cursor.lastrowid
            
            # Insert keywords
            for keyword in project.get('keywords', []):
                cursor.execute('''
                INSERT OR IGNORE INTO keywords (project_id, keyword)
                VALUES (?, ?)
                ''', (project_id, keyword))
                
            # Insert contracts
            for contract in project.get('contracts', []):
                cursor.execute('''
                INSERT OR IGNORE INTO contracts (project_id, chain, address, contract_type)
                VALUES (?, ?, ?, ?)
                ''', (project_id, contract['chain'], contract['address'], contract.get('type', 'main')))
        
        conn.commit()
        logger.info(f"Imported projects from configuration file.")
        
    except Exception as e:
        logger.error(f"Error importing projects: {e}")
        conn.rollback()

def import_sources_from_config(conn):
    """Import sources from the sources.json config file."""
    try:
        sources_path = Path('config/sources.json')
        if not sources_path.exists():
            logger.warning("Sources config file not found. Skipping source import.")
            return
            
        with open(sources_path, 'r') as f:
            sources_config = json.load(f)
        
        cursor = conn.cursor()
        
        # Import Telegram sources
        for source in sources_config.get('telegram', []):
            metadata = {k: v for k, v in source.items() if k not in ['name', 'id', 'username', 'priority']}
            metadata_json = json.dumps(metadata)
            
            cursor.execute('''
            INSERT OR REPLACE INTO sources (name, source_type, source_id, username, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (source['name'], 'telegram', source['id'], source.get('username', ''), source.get('priority', 'medium'), metadata_json))
        
        # Import Twitter sources
        for source in sources_config.get('twitter', []):
            metadata = {k: v for k, v in source.items() if k not in ['name', 'id', 'username', 'priority']}
            metadata_json = json.dumps(metadata)
            
            cursor.execute('''
            INSERT OR REPLACE INTO sources (name, source_type, source_id, username, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (source['name'], 'twitter', source['id'], source.get('username', ''), source.get('priority', 'medium'), metadata_json))
        
        # Import Discord sources
        for source in sources_config.get('discord', []):
            metadata = {k: v for k, v in source.items() if k not in ['name', 'id', 'username', 'priority']}
            metadata_json = json.dumps(metadata)
            
            cursor.execute('''
            INSERT OR REPLACE INTO sources (name, source_type, source_id, username, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (source['name'], 'discord', source['id'], source.get('username', ''), source.get('priority', 'medium'), metadata_json))
        
        conn.commit()
        logger.info(f"Imported sources from configuration file.")
        
    except Exception as e:
        logger.error(f"Error importing sources: {e}")
        conn.rollback()

def map_project_sources(conn):
    """Map projects to their sources based on configuration."""
    try:
        projects_path = Path('config/projects.json')
        if not projects_path.exists():
            logger.warning("Projects config file not found. Skipping project-source mapping.")
            return
            
        with open(projects_path, 'r') as f:
            projects_config = json.load(f)
        
        cursor = conn.cursor()
        
        # Process all projects
        for priority in ['high_priority', 'medium_priority']:
            for project in projects_config.get(priority, []):
                # Get project ID
                cursor.execute("SELECT id FROM projects WHERE name = ?", (project['name'],))
                project_row = cursor.fetchone()
                if not project_row:
                    continue
                    
                project_id = project_row[0]
                
                # Map official channels
                for channel in project.get('official_channels', []):
                    channel_type, channel_id = channel.split(':')
                    cursor.execute(
                        "SELECT id FROM sources WHERE source_type = ? AND (source_id = ? OR username = ?)",
                        (channel_type, channel_id, channel_id)
                    )
                    source_row = cursor.fetchone()
                    if source_row:
                        cursor.execute('''
                        INSERT OR IGNORE INTO project_sources (project_id, source_id, relationship_type)
                        VALUES (?, ?, ?)
                        ''', (project_id, source_row[0], 'official'))
                
                # Map partner channels
                for channel in project.get('partner_channels', []):
                    channel_type, channel_id = channel.split(':')
                    cursor.execute(
                        "SELECT id FROM sources WHERE source_type = ? AND (source_id = ? OR username = ?)",
                        (channel_type, channel_id, channel_id)
                    )
                    source_row = cursor.fetchone()
                    if source_row:
                        cursor.execute('''
                        INSERT OR IGNORE INTO project_sources (project_id, source_id, relationship_type)
                        VALUES (?, ?, ?)
                        ''', (project_id, source_row[0], 'partner'))
        
        conn.commit()
        logger.info(f"Mapped projects to sources successfully.")
        
    except Exception as e:
        logger.error(f"Error mapping projects to sources: {e}")
        conn.rollback()

def reset_database(db_path):
    """Delete the database file if it exists."""
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Existing database deleted: {db_path}")
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup the CryptoFarm database.')
    parser.add_argument('--reset', action='store_true', help='Reset the database (delete and recreate)')
    args = parser.parse_args()
    
    try:
        config = load_config()
        db_path = get_db_path(config)
        
        if args.reset:
            if reset_database(db_path):
                logger.info("Database reset successfully.")
            else:
                logger.error("Failed to reset database.")
                return
        
        # Create database connection
        conn = sqlite3.connect(db_path)
        
        # Create tables
        create_tables(conn)
        
        # Import data from config files
        import_projects_from_config(conn)
        import_sources_from_config(conn)
        map_project_sources(conn)
        
        # Close connection
        conn.close()
        
        logger.info(f"Database setup completed successfully: {db_path}")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 