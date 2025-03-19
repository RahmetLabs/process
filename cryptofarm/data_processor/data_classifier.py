import re
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union

# Import system modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database.db_utils import (
    add_analyzed_data, mark_data_processed, get_project_by_name, 
    add_project, add_alert, db_manager
)

# Configure logging
logger = logging.getLogger("DataClassifier")

class DataClassifier:
    """Advanced classifier for blockchain project data"""
    
    def __init__(self, project_config=None):
        """Initialize the classifier with priority-based categorization"""
        # Load project configuration
        self.config = project_config or config.project_config
        
        # Load all tracked channels and keywords
        self.tracked_channels = self.config.get_all_channels()
        self.tracked_keywords = self.config.get_all_keywords()
        
        # Core classification categories
        self.categories = {
            # Project Status Categories
            'active_investment': ['staked', 'locked', 'holding', 'position', 'invested', 'farming'],
            'testnet_participation': ['validator', 'node', 'testnet', 'валидатор', 'нода', 'тестнет'],
            'project_launch': ['launch', 'mainnet', 'going live', 'запуск', 'мейннет'],
            'research_phase': ['research', 'analysis', 'potential', 'исследование', 'анализ'],
            
            # Action Categories
            'urgent_action': ['claim', 'mint', 'stake', 'deadline', 'срочно', 'клейм', 'минт', 'last chance'],
            'upcoming_opportunity': ['whitelist', 'presale', 'airdrop', 'вайтлист', 'пресейл', 'раздача'],
            'monitoring_needed': ['proposal', 'update', 'change', 'обновление', 'announcement'],
            
            # Financial Categories
            'tokenomics': ['token', 'supply', 'allocation', 'vesting', 'токен', 'эмиссия'],
            'fundraising': ['funding', 'investment', 'seed', 'raise', 'инвестиции', 'раунд'],
            'trading': ['exchange', 'listing', 'market', 'биржа', 'листинг', 'market cap', 'price', 'up', 'down'],
            
            # Standard Categories (Lower Priority)
            'defi': ['yield', 'liquidity', 'pool', 'farm', 'lp', 'стейкинг', 'пул', 'фарм', 'yield'],
            'nft': ['nft', 'collection', 'нфт', 'коллекция', 'mint'],
            'tech': ['protocol', 'chain', 'layer', 'протокол', 'чейн', 'layer', 'zk', 'rollup', 'consensus'],
            'community': ['community', 'holder', 'ambassador', 'сообщество', 'амбассадор'],
            'gaming': ['game', 'play', 'quest', 'игр', 'quest'],
            'social': ['social', 'profile', 'account', 'социальн', 'профиль']
        }
        
        # Context and priority indicators
        self.priority_indicators = {
            'high_impact': ['important', 'critical', 'major', 'significant', 'важно', 'критично'],
            'time_sensitive': ['today', 'tomorrow', 'hours', 'deadline', 'сегодня', 'завтра', 'часов'],
            'alpha': ['alpha', 'insider', 'exclusive', 'альфа', 'инсайд', 'early'],
            'risk': ['warning', 'alert', 'scam', 'fake', 'предупреждение', 'скам'],
            'opportunity': ['profit', 'gain', 'earn', 'rewards', 'прибыль', 'заработок', 'free']
        }
        
        # Project discovery patterns
        self.discovery_patterns = [
            r'new project[:\s]+([A-Za-z0-9_]+)',
            r'upcoming project[:\s]+([A-Za-z0-9_]+)',
            r'([A-Za-z0-9_]+) is launching',
            r'([A-Za-z0-9_]+) token launch',
            r'([A-Za-z0-9_]+) airdrop',
            r'\$([A-Z]{2,10}) launch'
        ]

    def preprocess_text(self, text: str) -> str:
        """Preprocess text for better categorization"""
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Handle common abbreviations and variations
        text = text.replace('$', ' ')  # Handle token symbols
        text = text.replace('#', ' ')  # Handle hashtags
        text = text.replace('@', ' ')  # Handle mentions
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def get_source_weight(self, source_type: str = 'general', channel: str = None) -> float:
        """Get weight for a data source"""
        if channel and channel in self.tracked_channels:
            return self.tracked_channels[channel]['weight']
        return self.config.source_weights.get(source_type, 0.4)

    def identify_projects(self, text: str, channel: str = None) -> List[Dict[str, Any]]:
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
        
        # Check symbols with $ prefix - common in crypto discussions
        symbols = re.findall(r'\$([A-Z]{2,10})\b', text)
        for symbol in symbols:
            # Check if the symbol matches any known project
            for project in self.config.get_all_projects():
                if symbol.lower() == project.get('symbol', '').lower():
                    projects.append({
                        'name': project['name'],
                        'priority': project.get('priority', 'medium_priority'),
                        'confidence': 0.7,
                        'source': 'symbol'
                    })
        
        # Check for contract addresses
        contracts = re.findall(r'0x[a-fA-F0-9]{40}', text)
        for contract in contracts:
            for project in self.config.get_all_projects():
                if contract.lower() in [c.lower() for c in project.get('contracts', [])]:
                    projects.append({
                        'name': project['name'],
                        'priority': project.get('priority', 'medium_priority'),
                        'confidence': 0.9,  # High confidence with contract match
                        'source': 'contract'
                    })
        
        # Deduplicate projects
        unique_projects = []
        for project in projects:
            if not any(p['name'] == project['name'] for p in unique_projects):
                unique_projects.append(project)
        
        return unique_projects

    def categorize_text(self, text: str, channel: str = None) -> Dict[str, Any]:
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
            for keyword in keywords:
                if keyword in text:
                    result['categories'].append(category)
                    break  # Found a match for this category, move to next
        
        # Check priority indicators
        for indicator, keywords in self.priority_indicators.items():
            for keyword in keywords:
                if keyword in text:
                    result['context'].append(indicator)
                    break  # Found a match for this indicator, move to next
        
        # Infer categories from context
        if not result['categories']:
            if any(word in text for word in ['update', 'new', 'release', 'version']):
                result['categories'].append('monitoring_needed')
            
            if any(char.isdigit() for char in text):
                if 'x' in text or '%' in text or 'apy' in text:
                    result['categories'].append('defi')
                elif 'holder' in text or 'supply' in text:
                    result['categories'].append('tokenomics')
        
        # Detect potential new projects
        result['new_projects'] = self.detect_new_projects(text)
        
        return result

    def calculate_priority_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate priority score based on various factors"""
        score = 1.0
        
        # Project priority multiplier
        if analysis['projects']:
            max_project_score = max(
                1.5 if p.get('priority') == 'high_priority' else 1.2
                for p in analysis['projects']
            ) if any('priority' in p for p in analysis['projects']) else 1.0
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
        if 'opportunity' in analysis['context']:
            score *= 1.25
        
        # Category multiplier
        if 'urgent_action' in analysis['categories']:
            score *= 1.5
        if 'active_investment' in analysis['categories']:
            score *= 1.3
        if 'project_launch' in analysis['categories']:
            score *= 1.25
        if 'upcoming_opportunity' in analysis['categories']:
            score *= 1.35
        
        # Source weight multiplier
        score *= analysis['source_weight']
        
        return score

    def detect_new_projects(self, text: str) -> List[Dict[str, Any]]:
        """Detect mentions of new/unknown projects"""
        new_projects = []
        
        # Apply discovery patterns
        for pattern in self.discovery_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Check if this is already a known project
                if not any(p['name'].lower() == match.lower() for p in self.config.get_all_projects()):
                    # Calculate confidence based on pattern and message content
                    confidence = 0.6  # Base confidence
                    
                    # Higher confidence if mentioned multiple times
                    mention_count = text.lower().count(match.lower())
                    if mention_count > 1:
                        confidence += min(0.2, mention_count * 0.05)
                        
                    # Higher confidence if there are certain keywords nearby
                    nearby_keywords = ['launch', 'token', 'project', 'airdrop', 'whitelist']
                    nearby_count = sum(1 for keyword in nearby_keywords if keyword in text.lower())
                    confidence += min(0.2, nearby_count * 0.04)
                    
                    new_projects.append({
                        'name': match,
                        'confidence': confidence,
                        'source': 'discovery'
                    })
        
        # Deduplicate
        unique_projects = []
        for project in new_projects:
            if not any(p['name'].lower() == project['name'].lower() for p in unique_projects):
                unique_projects.append(project)
        
        return unique_projects

    def process_raw_data(self, raw_data_id: int, content: str, 
                        metadata: str, source_type: str = None) -> Dict[str, Any]:
        """Process raw data and store the analysis"""
        try:
            # Parse metadata from JSON string if needed
            if isinstance(metadata, str):
                try:
                    metadata_dict = json.loads(metadata)
                except:
                    metadata_dict = {'source': source_type}
            else:
                metadata_dict = metadata or {'source': source_type}
            
            # Get channel/source name for better classification
            channel = None
            if source_type and source_type.startswith('telegram'):
                channel = metadata_dict.get('channel_name')
            elif source_type and source_type.startswith('twitter'):
                channel = metadata_dict.get('username')
            
            # Categorize the content
            analysis = self.categorize_text(content, channel)
            
            # Calculate priority score
            priority_score = self.calculate_priority_score(analysis)
            analysis['priority_score'] = priority_score
            
            # Handle detected projects
            self.handle_projects(analysis, content, raw_data_id)
            
            # Mark the data as processed
            mark_data_processed(raw_data_id)
            
            return analysis
        except Exception as e:
            logger.error(f"Error processing raw data {raw_data_id}: {str(e)}")
            return None

    def handle_projects(self, analysis: Dict[str, Any], content: str, raw_data_id: int) -> None:
        """Handle detected projects including storing analysis and creating alerts"""
        # Process known projects
        for project in analysis.get('projects', []):
            project_name = project.get('name')
            if not project_name:
                continue
                
            # Get project from database or create if doesn't exist
            db_project = get_project_by_name(project_name)
            if not db_project:
                # Skip if the confidence is low
                if project.get('confidence', 0) < 0.7:
                    continue
                    
                # Create new project entry
                project_id = add_project({
                    'name': project_name,
                    'symbol': '',  # Will be updated later
                    'category': analysis.get('categories', ['unknown'])[0] if analysis.get('categories') else 'unknown',
                    'score': 0.0,
                    'participation_status': 'monitoring',
                    'source': 'auto-detection',
                    'source_url': '',
                    'worth_participating': 1 if analysis.get('priority_score', 0) > 1.3 else 0
                })
                
                # Create alert for new detected project
                add_alert(
                    project_id=project_id,
                    alert_type='new_project',
                    alert_message=f"New project detected: {project_name}. Content: {content[:100]}...",
                    priority='high'
                )
            else:
                project_id = db_project['id']
            
            # Store analysis data
            categories_json = json.dumps(analysis.get('categories', []))
            context_json = json.dumps(analysis.get('context', []))
            
            add_analyzed_data(
                raw_data_id=raw_data_id,
                project_id=project_id,
                categories=categories_json,
                priority_score=analysis.get('priority_score', 0.0),
                context=context_json
            )
            
            # Create alerts for high priority items
            if analysis.get('priority_score', 0.0) > 1.3:
                alert_type = 'opportunity' if 'opportunity' in analysis.get('context', []) else 'update'
                
                if 'urgent_action' in analysis.get('categories', []):
                    alert_type = 'urgent'
                elif 'risk' in analysis.get('context', []):
                    alert_type = 'risk'
                
                add_alert(
                    project_id=project_id,
                    alert_type=alert_type,
                    alert_message=f"High priority {alert_type} for {project_name}: {content[:100]}...",
                    priority='high' if analysis.get('priority_score', 0.0) > 1.5 else 'medium'
                )
        
        # Process potential new projects
        for new_project in analysis.get('new_projects', []):
            project_name = new_project.get('name')
            confidence = new_project.get('confidence', 0.0)
            
            # Only process high-confidence discoveries
            if confidence >= 0.7:
                # Check if this project already exists
                db_project = get_project_by_name(project_name)
                if not db_project:
                    # Create new project entry
                    project_id = add_project({
                        'name': project_name,
                        'symbol': '',  # Will be updated later
                        'category': analysis.get('categories', ['unknown'])[0] if analysis.get('categories') else 'unknown',
                        'score': confidence,
                        'participation_status': 'discovery',
                        'source': 'discovery',
                        'source_url': '',
                        'worth_participating': 1 if confidence > 0.8 else 0
                    })
                    
                    # Create alert for new discovered project
                    add_alert(
                        project_id=project_id,
                        alert_type='discovery',
                        alert_message=f"New project discovered: {project_name}. Confidence: {confidence:.2f}. Content: {content[:100]}...",
                        priority='medium'
                    )
                    
                    # Also store this as an analysis
                    add_analyzed_data(
                        raw_data_id=raw_data_id,
                        project_id=project_id,
                        categories=json.dumps(analysis.get('categories', [])),
                        priority_score=confidence,
                        context=json.dumps(analysis.get('context', []) + ['discovery'])
                    )

    def process_unprocessed_data(self, limit: int = 100) -> int:
        """Process all unprocessed data in the database"""
        try:
            # Get unprocessed data
            query = """
            SELECT rd.id, rd.content, rd.metadata, ds.source_type 
            FROM raw_data rd
            JOIN data_sources ds ON rd.source_id = ds.id
            WHERE rd.processed = 0
            LIMIT ?
            """
            results = db_manager.execute_query(query, (limit,))
            
            processed_count = 0
            for row in results:
                raw_data_id, content, metadata, source_type = row
                self.process_raw_data(raw_data_id, content, metadata, source_type)
                processed_count += 1
            
            return processed_count
        except Exception as e:
            logger.error(f"Error processing unprocessed data: {str(e)}")
            return 0

    def generate_analytics(self, project_id: Optional[int] = None, 
                         time_period: Optional[str] = None) -> Dict[str, Any]:
        """Generate analytics about processed data"""
        try:
            # Build base query
            base_query = """
            SELECT ad.id, ad.categories, ad.context, ad.priority_score, 
                   p.name as project_name, p.id as project_id, 
                   rd.content, rd.metadata, ds.source_type
            FROM analyzed_data ad
            JOIN projects p ON ad.project_id = p.id
            JOIN raw_data rd ON ad.raw_data_id = rd.id
            JOIN data_sources ds ON rd.source_id = ds.id
            """
            
            # Add filters
            filters = []
            params = []
            
            if project_id:
                filters.append("ad.project_id = ?")
                params.append(project_id)
            
            if time_period:
                # Convert time period to timestamp range
                if time_period == 'today':
                    filters.append("ad.analysis_timestamp >= date('now', 'start of day')")
                elif time_period == 'week':
                    filters.append("ad.analysis_timestamp >= date('now', '-7 days')")
                elif time_period == 'month':
                    filters.append("ad.analysis_timestamp >= date('now', '-30 days')")
            
            # Compose final query
            query = base_query
            if filters:
                query += " WHERE " + " AND ".join(filters)
            
            # Execute query
            results = db_manager.execute_query(query, params)
            
            # Process results for analytics
            analytics = {
                'total_items': 0,
                'project_mentions': {},
                'category_distribution': {},
                'context_distribution': {},
                'priority_distribution': {
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'source_distribution': {},
                'high_priority_items': []
            }
            
            for row in results:
                try:
                    # Extract data
                    id, categories, context, priority_score, project_name, project_id, content, metadata, source_type = row
                    
                    # Parse JSON fields
                    categories_list = json.loads(categories) if categories else []
                    context_list = json.loads(context) if context else []
                    metadata_dict = json.loads(metadata) if metadata else {}
                    
                    # Count total
                    analytics['total_items'] += 1
                    
                    # Project mentions
                    if project_name not in analytics['project_mentions']:
                        analytics['project_mentions'][project_name] = {
                            'mentions': 0,
                            'categories': {},
                            'contexts': {},
                            'priority_items': [],
                            'sources': {}
                        }
                    
                    project_analytics = analytics['project_mentions'][project_name]
                    project_analytics['mentions'] += 1
                    
                    # Categories
                    for category in categories_list:
                        # Global category distribution
                        if category not in analytics['category_distribution']:
                            analytics['category_distribution'][category] = 0
                        analytics['category_distribution'][category] += 1
                        
                        # Project category distribution
                        if category not in project_analytics['categories']:
                            project_analytics['categories'][category] = 0
                        project_analytics['categories'][category] += 1
                    
                    # Context
                    for ctx in context_list:
                        # Global context distribution
                        if ctx not in analytics['context_distribution']:
                            analytics['context_distribution'][ctx] = 0
                        analytics['context_distribution'][ctx] += 1
                        
                        # Project context distribution
                        if ctx not in project_analytics['contexts']:
                            project_analytics['contexts'][ctx] = 0
                        project_analytics['contexts'][ctx] += 1
                    
                    # Source distribution
                    if source_type not in analytics['source_distribution']:
                        analytics['source_distribution'][source_type] = 0
                    analytics['source_distribution'][source_type] += 1
                    
                    # Project source distribution
                    if source_type not in project_analytics['sources']:
                        project_analytics['sources'][source_type] = 0
                    project_analytics['sources'][source_type] += 1
                    
                    # Priority distribution
                    if priority_score >= 1.5:
                        analytics['priority_distribution']['high'] += 1
                    elif priority_score >= 1.0:
                        analytics['priority_distribution']['medium'] += 1
                    else:
                        analytics['priority_distribution']['low'] += 1
                    
                    # High priority items
                    if priority_score >= 1.3:
                        # Truncate content for brevity
                        truncated_content = content[:200] + ('...' if len(content) > 200 else '')
                        
                        high_priority_item = {
                            'id': id,
                            'project_id': project_id,
                            'project_name': project_name,
                            'priority_score': priority_score,
                            'categories': categories_list,
                            'context': context_list,
                            'content': truncated_content,
                            'source_type': source_type
                        }
                        
                        analytics['high_priority_items'].append(high_priority_item)
                        project_analytics['priority_items'].append(high_priority_item)
                        
                except Exception as e:
                    logger.error(f"Error processing analytics row {id}: {str(e)}")
                    continue
            
            # Sort high priority items by score
            analytics['high_priority_items'].sort(key=lambda x: x['priority_score'], reverse=True)
            
            # Sort project priority items by score
            for project_name, project_data in analytics['project_mentions'].items():
                project_data['priority_items'].sort(key=lambda x: x['priority_score'], reverse=True)
            
            return analytics
        except Exception as e:
            logger.error(f"Error generating analytics: {str(e)}")
            return {
                'error': str(e),
                'total_items': 0,
                'project_mentions': {},
                'category_distribution': {},
                'context_distribution': {},
                'priority_distribution': {
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'source_distribution': {},
                'high_priority_items': []
            }


# Main function for running as script
def process_data():
    """Process unprocessed data and generate analytics"""
    classifier = DataClassifier()
    
    # Process unprocessed data
    processed_count = classifier.process_unprocessed_data()
    logger.info(f"Processed {processed_count} items.")
    
    # Generate overall analytics
    analytics = classifier.generate_analytics(time_period='week')
    logger.info(f"Generated analytics for {analytics['total_items']} items.")
    
    # Print high priority items
    high_priority_count = len(analytics['high_priority_items'])
    logger.info(f"Found {high_priority_count} high priority items.")
    for item in analytics['high_priority_items'][:5]:  # Print top 5
        logger.info(f"High Priority Item: {item['project_name']} - Score: {item['priority_score']:.2f}")
        logger.info(f"Categories: {', '.join(item['categories'])}")
        logger.info(f"Context: {', '.join(item['context'])}")
        logger.info(f"Content: {item['content']}")
        logger.info("---")
    
    return {
        'processed_count': processed_count,
        'analytics': analytics
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process data and generate analytics")
    parser.add_argument("--process-only", action="store_true", help="Only process data without analytics")
    parser.add_argument("--analytics-only", action="store_true", help="Only generate analytics without processing data")
    parser.add_argument("--project", type=str, help="Generate analytics for a specific project")
    parser.add_argument("--period", type=str, choices=['today', 'week', 'month', 'all'], default='week',
                       help="Time period for analytics")
    args = parser.parse_args()
    
    classifier = DataClassifier()
    
    if not args.analytics_only:
        processed_count = classifier.process_unprocessed_data()
        print(f"Processed {processed_count} items.")
    
    if not args.process_only:
        project_id = None
        if args.project:
            project = get_project_by_name(args.project)
            if project:
                project_id = project['id']
                print(f"Generating analytics for project: {args.project} (ID: {project_id})")
            else:
                print(f"Project not found: {args.project}")
                exit(1)
        
        analytics = classifier.generate_analytics(project_id=project_id, time_period=args.period)
        
        print(f"\nAnalytics for period: {args.period}")
        print(f"Total analyzed items: {analytics['total_items']}")
        print(f"High priority items: {analytics['priority_distribution']['high']}")
        print(f"Medium priority items: {analytics['priority_distribution']['medium']}")
        print(f"Low priority items: {analytics['priority_distribution']['low']}")
        
        print("\nTop mentioned projects:")
        sorted_projects = sorted(
            analytics['project_mentions'].items(),
            key=lambda x: x[1]['mentions'],
            reverse=True
        )
        for project_name, data in sorted_projects[:10]:  # Top 10
            print(f"- {project_name}: {data['mentions']} mentions, {len(data['priority_items'])} priority items")
        
        print("\nTop categories:")
        sorted_categories = sorted(
            analytics['category_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for category, count in sorted_categories[:10]:  # Top 10
            print(f"- {category}: {count}")
        
        print("\nHigh priority items:")
        for item in analytics['high_priority_items'][:5]:  # Top 5
            print(f"\n- {item['project_name']} (Score: {item['priority_score']:.2f})")
            print(f"  Categories: {', '.join(item['categories'])}")
            print(f"  Context: {', '.join(item['context'])}")
            print(f"  Content: {item['content']}") 