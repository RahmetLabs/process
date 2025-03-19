import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cryptofarm.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CryptoFarm")

class Config:
    """Configuration manager for CryptoFarm"""
    
    def __init__(self, config_dir="config"):
        """Initialize configuration with default values"""
        self.config_dir = config_dir
        
        # Ensure config directory exists
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Initialize default configuration
        self.defaults = {
            "database": {
                "path": "database/cryptofarm.db",
                "backup_dir": "database/backups"
            },
            "api": {
                "host": "localhost",
                "port": 8000,
                "debug": True,
                "secret_key": "your-secret-key-here",
                "token_expire_minutes": 60 * 24 * 7  # 1 week
            },
            "data_collection": {
                "concurrent_scrapers": 3,
                "rate_limit": {
                    "twitter": 15,  # requests per 15 minutes
                    "telegram": 20,  # requests per minute
                    "discord": 10    # requests per minute
                },
                "fetch_interval": {
                    "twitter": 15,   # minutes
                    "telegram": 5,   # minutes
                    "discord": 30    # minutes
                }
            },
            "analysis": {
                "min_priority_score": 0.7,
                "high_priority_threshold": 1.5,
                "med_priority_threshold": 1.0,
                "model_path": "models/classifier.pkl",
                "use_llm": False,
                "llm_provider": "openai",
                "llm_model": "gpt-3.5-turbo"
            },
            "automation": {
                "enabled": True,
                "max_concurrent_tasks": 5,
                "notification_channels": ["console"],
                "check_interval": 15  # minutes
            },
            "workflow": {
                "auto_discovery": True,
                "auto_participation": False,
                "approval_required": True
            }
        }
        
        # Load configuration from files
        self.config = self.defaults.copy()
        self.load_config()
        
        # Set up project priorities
        self.project_config = ProjectConfig()
        self.load_projects()
        
        # Load data sources
        self.sources = {}
        self.load_sources()
        
    def load_config(self):
        """Load main configuration from main.json"""
        config_file = os.path.join(self.config_dir, "main.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Update config with user values (nested update)
                self._update_nested_dict(self.config, user_config)
                logger.info(f"Configuration loaded from {config_file}")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
    
    def load_projects(self):
        """Load project priorities and details"""
        projects_file = os.path.join(self.config_dir, "projects.json")
        if os.path.exists(projects_file):
            try:
                with open(projects_file, 'r') as f:
                    projects_data = json.load(f)
                
                # Add projects to configuration
                for priority, projects in projects_data.items():
                    for project in projects:
                        self.project_config.add_project(priority, project)
                
                logger.info(f"Loaded {len(self.project_config.get_all_projects())} projects from {projects_file}")
            except Exception as e:
                logger.error(f"Error loading projects: {str(e)}")
    
    def load_sources(self):
        """Load data source configurations"""
        sources_file = os.path.join(self.config_dir, "sources.json")
        if os.path.exists(sources_file):
            try:
                with open(sources_file, 'r') as f:
                    self.sources = json.load(f)
                
                logger.info(f"Loaded data sources from {sources_file}")
            except Exception as e:
                logger.error(f"Error loading data sources: {str(e)}")
    
    def save_config(self):
        """Save current configuration to file"""
        config_file = os.path.join(self.config_dir, "main.json")
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
    
    def save_projects(self):
        """Save project configuration to file"""
        projects_file = os.path.join(self.config_dir, "projects.json")
        try:
            projects_data = {
                "high_priority": self.project_config.projects["high_priority"],
                "medium_priority": self.project_config.projects["medium_priority"]
            }
            
            with open(projects_file, 'w') as f:
                json.dump(projects_data, f, indent=2)
            logger.info(f"Projects saved to {projects_file}")
        except Exception as e:
            logger.error(f"Error saving projects: {str(e)}")
    
    def save_sources(self):
        """Save data sources configuration to file"""
        sources_file = os.path.join(self.config_dir, "sources.json")
        try:
            with open(sources_file, 'w') as f:
                json.dump(self.sources, f, indent=2)
            logger.info(f"Data sources saved to {sources_file}")
        except Exception as e:
            logger.error(f"Error saving data sources: {str(e)}")
    
    def get(self, section, key=None):
        """Get configuration value"""
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)
    
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def _update_nested_dict(self, d, u):
        """Update nested dictionary d with values from u"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._update_nested_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d


class ProjectConfig:
    """Project configuration and priority management"""
    
    def __init__(self):
        """Initialize project configuration"""
        self.projects = {
            'high_priority': [],
            'medium_priority': []
        }
        
        self.source_weights = {
            'official': 1.0,    # Official project channels
            'partner': 0.8,     # Verified partners
            'community': 0.6,   # Community discussions
            'general': 0.4      # General market discussion
        }
    
    def add_project(self, priority: str, project_data: dict):
        """Add or update a project configuration"""
        if priority not in self.projects:
            raise ValueError(f"Invalid priority level: {priority}")
            
        # Remove existing project with same name if it exists
        self.remove_project(priority, project_data.get('name', ''))
            
        self.projects[priority].append({
            'name': project_data.get('name', ''),
            'symbol': project_data.get('symbol', ''),
            'official_channels': project_data.get('official_channels', []),
            'partner_channels': project_data.get('partner_channels', []),
            'keywords': project_data.get('keywords', []),
            'contracts': project_data.get('contracts', []),
            'tracking_reason': project_data.get('tracking_reason', ''),
            'investment_type': project_data.get('investment_type', ''),
            'entry_date': project_data.get('entry_date', ''),
            'target_events': project_data.get('target_events', [])
        })
    
    def remove_project(self, priority: str, project_name: str):
        """Remove a project from tracking"""
        if priority not in self.projects:
            raise ValueError(f"Invalid priority level: {priority}")
            
        self.projects[priority] = [
            p for p in self.projects[priority] 
            if p['name'].lower() != project_name.lower()
        ]
    
    def get_project(self, project_name: str):
        """Get project details regardless of priority"""
        for priority in self.projects:
            for project in self.projects[priority]:
                if project['name'].lower() == project_name.lower():
                    return priority, project
        return None, None
    
    def get_all_projects(self):
        """Get all projects regardless of priority"""
        all_projects = []
        for priority in self.projects:
            for project in self.projects[priority]:
                project_copy = project.copy()
                project_copy['priority'] = priority
                all_projects.append(project_copy)
        return all_projects
    
    def get_all_channels(self):
        """Get all tracked channels with their weights"""
        channels = {}
        for priority in self.projects:
            for project in self.projects[priority]:
                # Official channels
                for channel in project['official_channels']:
                    channels[channel] = {
                        'weight': self.source_weights['official'],
                        'project': project['name'],
                        'type': 'official'
                    }
                # Partner channels
                for channel in project['partner_channels']:
                    channels[channel] = {
                        'weight': self.source_weights['partner'],
                        'project': project['name'],
                        'type': 'partner'
                    }
        return channels
    
    def get_all_keywords(self):
        """Get all project-specific keywords"""
        keywords = {}
        for priority in self.projects:
            for project in self.projects[priority]:
                for keyword in project['keywords']:
                    keyword = keyword.lower()
                    if keyword not in keywords:
                        keywords[keyword] = []
                    keywords[keyword].append({
                        'project': project['name'],
                        'priority': priority
                    })
        return keywords


# Create default configuration
default_config = Config()

# Make configuration accessible as module properties
get = default_config.get
set = default_config.set
project_config = default_config.project_config
sources = default_config.sources 