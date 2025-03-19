import pandas as pd
import re
import json
import os
from datetime import datetime
from data_classifier import DataClassifier

class OpportunityAnalyzer:
    def __init__(self):
        self.classifier = DataClassifier()
        
        # Define ROI potential criteria
        self.roi_criteria = {
            'investment_size': {
                'ranges': [
                    (0, 1_000_000, 1),           # < $1M: Low
                    (1_000_000, 10_000_000, 2),  # $1M-$10M: Medium
                    (10_000_000, float('inf'), 3) # > $10M: High
                ],
                'weight': 3
            },
            'investor_quality': {
                'tier1': ['a16z', 'andreessen', 'horowitz', 'paradigm', 'polychain', 
                         'binance labs', 'coinbase ventures', 'sequoia', 'dragonfly'],
                'weight': 4
            },
            'community_engagement': {
                'ranges': [
                    (0, 100, 1),      # Low engagement
                    (100, 1000, 2),    # Medium engagement
                    (1000, float('inf'), 3)  # High engagement
                ],
                'weight': 2
            },
            'project_category': {
                'high_value': ['layer2', 'defi', 'ai'],
                'medium_value': ['dao', 'nft', 'grant'],
                'low_value': ['social', 'event'],
                'weight': 2
            }
        }
        
        # Define participation difficulty levels
        self.difficulty_levels = {
            'node_setup': {
                'complexity': 'high',
                'resource_intensive': True,
                'time_commitment': 'ongoing',
                'technical_skill': 'high'
            },
            'social_engagement': {
                'complexity': 'low',
                'resource_intensive': False,
                'time_commitment': 'one-time',
                'technical_skill': 'low'
            },
            'form_submission': {
                'complexity': 'low',
                'resource_intensive': False,
                'time_commitment': 'one-time',
                'technical_skill': 'low'
            },
            'transaction': {
                'complexity': 'medium',
                'resource_intensive': False,
                'time_commitment': 'one-time',
                'technical_skill': 'medium'
            },
            'content_creation': {
                'complexity': 'medium',
                'resource_intensive': False,
                'time_commitment': 'one-time',
                'technical_skill': 'medium'
            }
        }
    
    def calculate_roi_potential(self, project_data):
        """Calculate ROI potential score based on various factors"""
        roi_score = 0
        
        # Investment size
        investment_amount = project_data.get('investment_info', 0)
        if investment_amount:
            for min_val, max_val, score in self.roi_criteria['investment_size']['ranges']:
                if min_val <= investment_amount < max_val:
                    roi_score += score * self.roi_criteria['investment_size']['weight']
                    break
        
        # Investor quality
        text = project_data.get('text', '')
        if text:
            for investor in self.roi_criteria['investor_quality']['tier1']:
                if investor in text.lower():
                    roi_score += 3 * self.roi_criteria['investor_quality']['weight']
                    break
        
        # Community engagement
        engagement = 0
        if project_data.get('source') == 'twitter':
            engagement = project_data.get('likes', 0) + (project_data.get('retweets', 0) * 3)
        
        for min_val, max_val, score in self.roi_criteria['community_engagement']['ranges']:
            if min_val <= engagement < max_val:
                roi_score += score * self.roi_criteria['community_engagement']['weight']
                break
        
        # Project category
        categories = project_data.get('categories', [])
        category_score = 0
        
        for category in categories:
            if category in self.roi_criteria['project_category']['high_value']:
                category_score = 3
                break
            elif category in self.roi_criteria['project_category']['medium_value']:
                category_score = max(category_score, 2)
            elif category in self.roi_criteria['project_category']['low_value']:
                category_score = max(category_score, 1)
        
        roi_score += category_score * self.roi_criteria['project_category']['weight']
        
        # Normalize to 0-100 scale
        normalized_score = min(100, roi_score * 5)
        
        # Determine ROI level
        if normalized_score >= 70:
            roi_level = 'High'
        elif normalized_score >= 40:
            roi_level = 'Medium'
        else:
            roi_level = 'Low'
        
        return {
            'score': normalized_score,
            'level': roi_level
        }
    
    def determine_participation_strategy(self, project_data):
        """Determine the best participation strategy for a project"""
        opportunity_types = project_data.get('opportunity_types', [])
        categories = project_data.get('categories', [])
        
        strategies = []
        
        # Technical participation (node setup, testnet)
        if 'node_setup' in opportunity_types or 'testnet' in categories:
            strategies.append({
                'type': 'technical',
                'action': 'node_setup',
                'difficulty': self.difficulty_levels['node_setup']['complexity'],
                'resource_intensive': self.difficulty_levels['node_setup']['resource_intensive'],
                'time_commitment': self.difficulty_levels['node_setup']['time_commitment']
            })
        
        # Social participation
        if 'social_engagement' in opportunity_types or 'social' in categories:
            strategies.append({
                'type': 'social',
                'action': 'social_engagement',
                'difficulty': self.difficulty_levels['social_engagement']['complexity'],
                'resource_intensive': self.difficulty_levels['social_engagement']['resource_intensive'],
                'time_commitment': self.difficulty_levels['social_engagement']['time_commitment']
            })
        
        # Form submission
        if 'form_submission' in opportunity_types:
            strategies.append({
                'type': 'administrative',
                'action': 'form_submission',
                'difficulty': self.difficulty_levels['form_submission']['complexity'],
                'resource_intensive': self.difficulty_levels['form_submission']['resource_intensive'],
                'time_commitment': self.difficulty_levels['form_submission']['time_commitment']
            })
        
        # Transaction/on-chain interaction
        if 'transaction' in opportunity_types or any(cat in categories for cat in ['defi', 'nft', 'airdrop']):
            strategies.append({
                'type': 'financial',
                'action': 'transaction',
                'difficulty': self.difficulty_levels['transaction']['complexity'],
                'resource_intensive': self.difficulty_levels['transaction']['resource_intensive'],
                'time_commitment': self.difficulty_levels['transaction']['time_commitment']
            })
        
        # Content creation
        if 'content_creation' in opportunity_types:
            strategies.append({
                'type': 'creative',
                'action': 'content_creation',
                'difficulty': self.difficulty_levels['content_creation']['complexity'],
                'resource_intensive': self.difficulty_levels['content_creation']['resource_intensive'],
                'time_commitment': self.difficulty_levels['content_creation']['time_commitment']
            })
        
        # If no specific strategies identified, default to social
        if not strategies:
            strategies.append({
                'type': 'social',
                'action': 'social_engagement',
                'difficulty': 'low',
                'resource_intensive': False,
                'time_commitment': 'one-time'
            })
        
        return strategies
    
    def extract_requirements(self, project_data):
        """Extract participation requirements from project data"""
        text = project_data.get('text', '')
        requirements = {}
        
        # Hardware requirements for node setup
        if 'node_setup' in project_data.get('opportunity_types', []) or 'testnet' in project_data.get('categories', []):
            # CPU requirements
            cpu_match = re.search(r'(\d+)\s*(?:CPU|cores?|processors?)', text, re.IGNORECASE)
            if cpu_match:
                requirements['cpu'] = cpu_match.group(1)
            
            # RAM requirements
            ram_match = re.search(r'(\d+)\s*(?:GB|G|RAM|memory)', text, re.IGNORECASE)
            if ram_match:
                requirements['ram'] = ram_match.group(1) + ' GB'
            
            # Storage requirements
            storage_match = re.search(r'(\d+)\s*(?:GB|G|TB|T|storage|disk)', text, re.IGNORECASE)
            if storage_match:
                requirements['storage'] = storage_match.group(1) + (' TB' if 'T' in storage_match.group() else ' GB')
        
        # Social requirements
        social_requirements = []
        if re.search(r'follow|twitter|tweet|retweet', text, re.IGNORECASE):
            social_requirements.append('Twitter engagement')
        if re.search(r'discord|server', text, re.IGNORECASE):
            social_requirements.append('Discord participation')
        if re.search(r'telegram|channel', text, re.IGNORECASE):
            social_requirements.append('Telegram membership')
        
        if social_requirements:
            requirements['social'] = social_requirements
        
        # Financial requirements
        if re.search(r'stake|deposit|send|transfer', text, re.IGNORECASE):
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ETH|BTC|USDT|USDC|\$)', text, re.IGNORECASE)
            if amount_match:
                requirements['financial'] = amount_match.group()
        
        # KYC requirements
        if re.search(r'KYC|verify|verification|identity', text, re.IGNORECASE):
            requirements['kyc'] = True
        
        return requirements
    
    def extract_deadlines(self, project_data):
        """Extract deadlines from project data"""
        text = project_data.get('text', '')
        dates = project_data.get('dates', [])
        
        deadlines = {}
        
        # Look for specific deadline keywords
        deadline_keywords = ['deadline', 'due', 'ends', 'closing', 'last day', 'until']
        for keyword in deadline_keywords:
            pattern = rf'{keyword}\s+(?:is|on|by)?\s+([A-Za-z]+\s+\d+(?:st|nd|rd|th)?,?\s+\d{{4}}|\d{{1,2}}[-/\.]\d{{1,2}}[-/\.]\d{{2,4}})'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadlines['submission'] = match.group(1)
                break
        
        # If no specific deadline found but dates are available, use the latest date
        if not deadlines and dates:
            # Simple approach - just use the last date mentioned
            # In a real system, you'd want to parse and compare dates properly
            deadlines['estimated'] = dates[-1]
        
        return deadlines
    
    def analyze_opportunity(self, project_data):
        """Analyze an opportunity and provide comprehensive assessment"""
        # Calculate ROI potential
        roi_potential = self.calculate_roi_potential(project_data)
        
        # Determine participation strategy
        participation_strategies = self.determine_participation_strategy(project_data)
        
        # Extract requirements
        requirements = self.extract_requirements(project_data)
        
        # Extract deadlines
        deadlines = self.extract_deadlines(project_data)
        
        # Determine if worth participating
        # Simple rule: High ROI or Medium ROI with easy participation
        worth_participating = (
            roi_potential['level'] == 'High' or 
            (roi_potential['level'] == 'Medium' and 
             any(s['difficulty'] == 'low' for s in participation_strategies))
        )
        
        # Generate recommendation
        if worth_participating:
            if roi_potential['level'] == 'High':
                recommendation = "High priority. Strongly recommended to participate using all available strategies."
            else:
                recommendation = "Medium priority. Recommended to participate using low-effort strategies."
        else:
            recommendation = "Low priority. Only participate if resources are available."
        
        return {
            'project_name': project_data.get('project_name', 'Unknown Project'),
            'roi_potential': roi_potential,
            'participation_strategies': participation_strategies,
            'requirements': requirements,
            'deadlines': deadlines,
            'worth_participating': worth_participating,
            'recommendation': recommendation
        }
    
    def process_data_source(self, data_source, data):
        """Process data from a specific source and analyze opportunities"""
        # Use the classifier to process the data
        classified_data = self.classifier.process_data(data_source, data)
        
        # Analyze each opportunity
        analyzed_opportunities = []
        for item in classified_data:
            # Skip items with no categories or low score
            if not item.get('categories') or item.get('score', 0) < 10:
                continue
            
            analysis = self.analyze_opportunity(item)
            
            # Combine the original data with the analysis
            item.update(analysis)
            analyzed_opportunities.append(item)
        
        return analyzed_opportunities
    
    def generate_summary_report(self, opportunities):
        """Generate a summary report of analyzed opportunities"""
        # Sort opportunities by ROI potential score
        sorted_opps = sorted(opportunities, key=lambda x: x.get('roi_potential', {}).get('score', 0), reverse=True)
        
        report = "# Web3 Opportunity Analysis Report\n\n"
        
        # Top opportunities
        report += "## Top Opportunities\n"
        for i, opp in enumerate(sorted_opps[:5], 1):
            project_name = opp.get('project_name', 'Unknown Project')
            roi_level = opp.get('roi_potential', {}).get('level', 'Unknown')
            roi_score = opp.get('roi_potential', {}).get('score', 0)
            categories = ', '.join(opp.get('categories', []))
            
            report += f"{i}. **{project_name}** (Score: {roi_score:.1f}, ROI: {roi_level})\n"
            report += f"   - Categories: {categories}\n"
            
            # Add investment info if available
            investment_info = opp.get('investment_info')
            if investment_info:
                report += f"   - Investment: ${investment_info:,.0f}\n"
            
            # Add participation strategies
            strategies = opp.get('participation_strategies', [])
            if strategies:
                strategy_types = [s['type'] for s in strategies]
                report += f"   - Participation: {', '.join(strategy_types)}\n"
            
            # Add deadlines if available
            deadlines = opp.get('deadlines', {})
            if deadlines:
                deadline = next(iter(deadlines.values()))
                report += f"   - Deadline: {deadline}\n"
            
            report += "\n"
        
        # Categorized opportunities
        categories = {
            'testnet': "Testnet Opportunities",
            'airdrop': "Airdrop Opportunities",
            'nft': "NFT Opportunities",
            'defi': "DeFi Opportunities",
            'dao': "DAO Opportunities",
            'grant': "Grant Opportunities",
            'layer2': "Layer 2 Opportunities"
        }
        
        for category, title in categories.items():
            category_opps = [opp for opp in opportunities if category in opp.get('categories', [])]
            if category_opps:
                report += f"## {title}\n"
                for opp in category_opps[:3]:  # Top 3 in each category
                    project_name = opp.get('project_name', 'Unknown Project')
                    roi_level = opp.get('roi_potential', {}).get('level', 'Unknown')
                    
                    report += f"- **{project_name}** (ROI: {roi_level})\n"
                    
                    # Add brief description based on opportunity type
                    if category == 'testnet':
                        report += f"  - Testnet participation opportunity with {roi_level.lower()} potential rewards\n"
                    elif category == 'airdrop':
                        report += f"  - Token airdrop with {roi_level.lower()} estimated value\n"
                    elif category == 'nft':
                        report += f"  - NFT opportunity with {roi_level.lower()} potential value\n"
                    elif category == 'defi':
                        report += f"  - DeFi opportunity with {roi_level.lower()} yield potential\n"
                    
                report += "\n"
        
        # Recommended actions
        report += "## Recommended Actions\n"
        high_priority = [opp for opp in opportunities if opp.get('worth_participating') and opp.get('roi_potential', {}).get('level') == 'High']
        medium_priority = [opp for opp in opportunities if opp.get('worth_participating') and opp.get('roi_potential', {}).get('level') == 'Medium']
        
        for i, opp in enumerate(high_priority[:3], 1):
            project_name = opp.get('project_name', 'Unknown Project')
            strategies = opp.get('participation_strategies', [])
            if strategies:
                main_strategy = strategies[0]['action'].replace('_', ' ').title()
                report += f"{i}. {main_strategy} for {project_name} (High Priority)\n"
        
        for i, opp in enumerate(medium_priority[:3], len(high_priority[:3])+1):
            project_name = opp.get('project_name', 'Unknown Project')
            strategies = opp.get('participation_strategies', [])
            if strategies:
                main_strategy = strategies[0]['action'].replace('_', ' ').title()
                report += f"{i}. {main_strategy} for {project_name} (Medium Priority)\n"
        
        return report

# Example usage
if __name__ == "__main__":
    analyzer = OpportunityAnalyzer()
    
    # Test with a sample project data
    sample_project = {
        'text': "Join the XYZ testnet and earn rewards! $10M raised from a16z and Binance Labs. Mainnet launch in June 2025. Node requirements: 4 CPU cores, 8GB RAM, 100GB storage. Deadline is April 15, 2025.",
        'categories': ['testnet', 'layer2'],
        'project_name': 'XYZ Protocol',
        'score': 85,
        'opportunity_types': ['node_setup', 'social_engagement'],
        'investment_info': 10000000,
        'dates': ['June 2025', 'April 15, 2025']
    }
    
    analysis = analyzer.analyze_opportunity(sample_project)
    print(f"Project: {analysis['project_name']}")
    print(f"ROI Potential: {analysis['roi_potential']['level']} ({analysis['roi_potential']['score']:.1f})")
    print(f"Worth Participating: {analysis['worth_participating']}")
    print(f"Recommendation: {analysis['recommendation']}")
    print(f"Participation Strategies: {[s['type'] for s in analysis['participation_strategies']]}")
    print(f"Requirements: {analysis['requirements']}")
    print(f"Deadlines: {analysis['deadlines']}")
