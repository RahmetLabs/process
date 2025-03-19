import pandas as pd
import re
from datetime import datetime
from config import ProjectConfig

class DataClassifier:
    def __init__(self, project_config=None):
        """Initialize the classifier with priority-based categorization"""
        # Load project configuration
        self.config = project_config or ProjectConfig()
        
        # Load all tracked channels and keywords
        self.tracked_channels = self.config.get_all_channels()
        self.tracked_keywords = self.config.get_all_keywords()
        
        # Core classification categories
        self.categories = {
            # Project Status Categories
            'active_investment': ['staked', 'locked', 'holding', 'position', 'invested'],
            'testnet_participation': ['validator', 'node', 'testnet', 'валидатор', 'нода', 'тестнет'],
            'research_phase': ['research', 'analysis', 'potential', 'исследование', 'анализ'],
            
            # Action Categories
            'urgent_action': ['claim', 'mint', 'stake', 'deadline', 'срочно', 'клейм', 'минт'],
            'upcoming_opportunity': ['whitelist', 'presale', 'launch', 'вайтлист', 'пресейл'],
            'monitoring_needed': ['proposal', 'update', 'change', 'обновление'],
            
            # Standard Categories (Lower Priority)
            'defi': ['yield', 'liquidity', 'pool', 'farm', 'lp', 'стейкинг', 'пул', 'фарм'],
            'nft': ['nft', 'collection', 'нфт', 'коллекция'],
            'tech': ['protocol', 'chain', 'layer', 'протокол', 'чейн']
        }
        
        # Context and priority indicators
        self.priority_indicators = {
            'high_impact': ['important', 'critical', 'major', 'важно', 'критично'],
            'time_sensitive': ['today', 'tomorrow', 'hours left', 'сегодня', 'завтра'],
            'alpha': ['alpha', 'insider', 'exclusive', 'альфа', 'инсайд'],
            'risk': ['warning', 'alert', 'scam', 'предупреждение', 'скам']
        }

    def preprocess_text(self, text):
        """Preprocess text for better categorization"""
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Handle common abbreviations and variations
        text = text.replace('$', '')  # Handle token symbols
        text = text.replace('#', '')  # Handle hashtags
        text = text.replace('@', '')  # Handle mentions
        
        return text

    def get_source_weight(self, source_type='general', channel=None):
        """Get weight for a data source"""
        if channel and channel in self.tracked_channels:
            return self.tracked_channels[channel]['weight']
        return self.config.source_weights.get(source_type, 0.4)

    def identify_projects(self, text, channel=None):
        """Identify mentioned projects and their priorities"""
        text = self.preprocess_text(text)
        projects = []
        
        # Check channel first
        if channel and channel in self.tracked_channels:
            channel_info = self.tracked_channels[channel]
            projects.append({
                'name': channel_info['project'],
                'confidence': channel_info['weight'],
                'source': 'channel'
            })
        
        # Check keywords
        for keyword, project_list in self.tracked_keywords.items():
            if keyword in text:
                for project in project_list:
                    projects.append({
                        'name': project['project'],
                        'priority': project['priority'],
                        'confidence': 0.8 if project['priority'] == 'high_priority' else 0.6,
                        'source': 'keyword'
                    })
        
        return projects

    def categorize_text(self, text, channel=None):
        """Categorize text with priority-based approach"""
        text = self.preprocess_text(text)
        
        # Initialize result
        result = {
            'categories': [],
            'context': [],
            'projects': self.identify_projects(text, channel),
            'source_weight': self.get_source_weight(channel=channel)
        }
        
        # Check categories
        for category, keywords in self.categories.items():
            if any(keyword in text for keyword in keywords):
                result['categories'].append(category)
        
        # Check priority indicators
        for indicator, keywords in self.priority_indicators.items():
            if any(keyword in text for keyword in keywords):
                result['context'].append(indicator)
        
        # Infer categories from context
        if not result['categories']:
            if any(word in text for word in ['update', 'new', 'release', 'version']):
                result['categories'].append('monitoring_needed')
            
            if any(char.isdigit() for char in text):
                if 'x' in text or '%' in text or 'apy' in text:
                    result['categories'].append('defi')
                elif 'holder' in text or 'supply' in text:
                    result['categories'].append('tokenomics')
        
        return result

    def calculate_priority_score(self, analysis):
        """Calculate priority score based on various factors"""
        score = 1.0
        
        # Project priority multiplier
        if analysis['projects']:
            max_project_score = max(
                1.5 if p.get('priority') == 'high_priority' else 1.2
                for p in analysis['projects']
            )
            score *= max_project_score
        
        # Context multiplier
        if 'high_impact' in analysis['context']:
            score *= 1.3
        if 'time_sensitive' in analysis['context']:
            score *= 1.4
        if 'alpha' in analysis['context']:
            score *= 1.2
        if 'risk' in analysis['context']:
            score *= 1.5
        
        # Category multiplier
        if 'urgent_action' in analysis['categories']:
            score *= 1.5
        if 'active_investment' in analysis['categories']:
            score *= 1.3
        
        # Source weight
        score *= analysis['source_weight']
        
        return score

    def process_data(self, df, source_type):
        """Process data with priority-based analysis"""
        if not isinstance(df, pd.DataFrame):
            return []
        
        results = []
        
        for _, row in df.iterrows():
            # Get text and channel
            if source_type == 'twitter':
                text = row.get('text', '')
                channel = row.get('username', '')
            else:  # telegram
                text = row.get('Message Text', '')
                channel = row.get('Channel', '')
            
            # Perform analysis
            analysis = self.categorize_text(text, channel)
            
            # Calculate engagement and priority scores
            if source_type == 'twitter':
                engagement_score = self.get_engagement_score(
                    likes=row.get('likes', 0),
                    retweets=row.get('retweets', 0),
                    replies=row.get('replies', 0),
                    views=row.get('views', 0)
                )
            else:
                engagement_score = 0  # TODO: Add Telegram engagement metrics
            
            priority_score = self.calculate_priority_score(analysis)
            
            # Prepare result
            result = {
                'source': source_type,
                'text': text,
                'channel': channel,
                'categories': analysis['categories'],
                'context': analysis['context'],
                'projects': analysis['projects'],
                'engagement_score': engagement_score,
                'priority_score': priority_score,
                'timestamp': row.get('created_at' if source_type == 'twitter' else 'Timestamp', '')
            }
            
            results.append(result)
        
        return results

    def process_twitter_data(self, df):
        """Process Twitter data"""
        return self.process_data(df, 'twitter')

    def process_telegram_data(self, df):
        """Process Telegram data"""
        return self.process_data(df, 'telegram')

    def get_engagement_score(self, likes=0, retweets=0, replies=0, views=0):
        """Calculate engagement score"""
        score = 0
        if likes: score += likes * 1.0
        if retweets: score += retweets * 2.0
        if replies: score += replies * 1.5
        if views: score += views * 0.01
        return score

    def generate_analytics(self, twitter_data=None, telegram_data=None):
        """Generate comprehensive analytics from processed data"""
        analytics = {
            'total_items': {
                'twitter': len(twitter_data) if twitter_data is not None else 0,
                'telegram': len(telegram_data) if telegram_data is not None else 0
            },
            'project_mentions': {},
            'category_distribution': {},
            'context_distribution': {},
            'high_priority_items': [],
            'top_engaging_content': [],
            'channel_categories': {}
        }

        # Initialize counters
        for category in self.categories:
            analytics['category_distribution'][category] = 0
        for context in self.priority_indicators:
            analytics['context_distribution'][context] = 0

        # Process all data
        all_data = []
        if twitter_data:
            all_data.extend(twitter_data)
        if telegram_data:
            all_data.extend(telegram_data)

        # Sort by priority score
        all_data.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        for item in all_data:
            # Update category distribution
            for category in item.get('categories', []):
                analytics['category_distribution'][category] = \
                    analytics['category_distribution'].get(category, 0) + 1
            
            # Update context distribution
            for context in item.get('context', []):
                analytics['context_distribution'][context] = \
                    analytics['context_distribution'].get(context, 0) + 1
            
            # Update project mentions
            for project in item.get('projects', []):
                project_name = project['name']
                if project_name not in analytics['project_mentions']:
                    analytics['project_mentions'][project_name] = {
                        'mentions': 0,
                        'priority_items': [],
                        'channels': set()  # Will be converted to list later
                    }
                
                analytics['project_mentions'][project_name]['mentions'] += 1
                analytics['project_mentions'][project_name]['channels'].add(item.get('channel', ''))
                
                # Add high priority items
                if item.get('priority_score', 0) >= 1.5:
                    analytics['project_mentions'][project_name]['priority_items'].append(item)
                    if item not in analytics['high_priority_items']:
                        analytics['high_priority_items'].append(item)
            
            # Update channel categories
            channel = item.get('channel')
            if channel:
                if channel not in analytics['channel_categories']:
                    analytics['channel_categories'][channel] = {
                        'messages': [],
                        'categories': {},
                        'top_categories': [],
                        'projects': set()  # Will be converted to list later
                    }
                
                channel_data = analytics['channel_categories'][channel]
                channel_data['messages'].append(item)
                
                # Update channel's category counts
                for category in item.get('categories', []):
                    channel_data['categories'][category] = \
                        channel_data['categories'].get(category, 0) + 1
                
                # Update channel's projects
                for project in item.get('projects', []):
                    channel_data['projects'].add(project['name'])
                
                # Update channel's top categories
                channel_data['top_categories'] = sorted(
                    channel_data['categories'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                channel_data['top_categories'] = [cat for cat, _ in channel_data['top_categories']]

            # Add to top engaging content if it has engagement
            if item.get('engagement_score', 0) > 0:
                analytics['top_engaging_content'].append(item)

        # Sort top engaging content
        analytics['top_engaging_content'].sort(
            key=lambda x: x.get('engagement_score', 0), 
            reverse=True
        )

        # Convert sets to lists for JSON serialization
        for project_data in analytics['project_mentions'].values():
            project_data['channels'] = list(project_data['channels'])

        for channel_data in analytics['channel_categories'].values():
            channel_data['projects'] = list(channel_data['projects'])

        return analytics
