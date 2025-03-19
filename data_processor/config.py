"""Project configuration and priority management"""

class ProjectConfig:
    def __init__(self):
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
            
        self.projects[priority].append({
            'name': project_data.get('name', ''),
            'symbol': project_data.get('symbol', ''),
            'official_channels': project_data.get('official_channels', []),
            'partner_channels': project_data.get('partner_channels', []),
            'keywords': project_data.get('keywords', []),
            'contracts': project_data.get('contracts', []),
            'tracking_reason': project_data.get('tracking_reason', ''),
            'investment_type': project_data.get('investment_type', ''),  # e.g., 'staking', 'holding'
            'entry_date': project_data.get('entry_date', ''),
            'target_events': project_data.get('target_events', [])  # e.g., ['mainnet', 'token_launch']
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
                    if keyword not in keywords:
                        keywords[keyword] = []
                    keywords[keyword].append({
                        'project': project['name'],
                        'priority': priority
                    })
        return keywords

# Default configuration
default_config = ProjectConfig()

# Example project configuration
example_project = {
    'name': 'TON',
    'symbol': 'TON',
    'official_channels': ['The Open Network', 'TON Foundation'],
    'partner_channels': ['TON Community', 'TON Dev'],
    'keywords': ['ton', 'toncoin', 'gram'],
    'contracts': ['0x123...'],
    'tracking_reason': 'Active validator node',
    'investment_type': 'staking',
    'entry_date': '2025-01-01',
    'target_events': ['mainnet_upgrade', 'new_validator_requirements']
}

# Uncomment to add example project
# default_config.add_project('high_priority', example_project)
