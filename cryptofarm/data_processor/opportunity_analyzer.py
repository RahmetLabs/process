import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional, Union
import math

# Import system modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database.db_utils import (
    get_project, get_all_projects, update_project, add_alert,
    db_manager, get_project_by_name
)

# Configure logging
logger = logging.getLogger("OpportunityAnalyzer")

class OpportunityAnalyzer:
    """Analyzer for blockchain project farming opportunities"""
    
    def __init__(self):
        """Initialize the opportunity analyzer"""
        # Opportunity scoring weights
        self.weights = {
            'activity_level': 0.25,       # Recent mentions and activity
            'community_growth': 0.15,     # Growth in mentions over time
            'sentiment': 0.15,           # Sentiment analysis
            'urgency': 0.20,             # Time sensitivity
            'roi_potential': 0.25        # Potential return on investment
        }
        
        # Opportunity categories with thresholds
        self.opportunity_categories = {
            'airdrop': {
                'keywords': ['airdrop', 'free', 'claim', 'distribution', 'eligible'],
                'effort_level': 'low',
                'time_sensitivity': 'high',
                'roi_potential': 'medium'
            },
            'testnet': {
                'keywords': ['testnet', 'test', 'validator', 'node', 'incentivized'],
                'effort_level': 'medium',
                'time_sensitivity': 'medium',
                'roi_potential': 'high'
            },
            'whitelist': {
                'keywords': ['whitelist', 'allowlist', 'wl', 'presale', 'early'],
                'effort_level': 'low',
                'time_sensitivity': 'high',
                'roi_potential': 'high'
            },
            'staking': {
                'keywords': ['stake', 'staking', 'locked', 'yield', 'reward', 'apr', 'apy'],
                'effort_level': 'low',
                'time_sensitivity': 'low',
                'roi_potential': 'medium'
            },
            'farming': {
                'keywords': ['farm', 'farming', 'liquidity', 'pool', 'yield'],
                'effort_level': 'medium',
                'time_sensitivity': 'medium',
                'roi_potential': 'medium'
            },
            'token_launch': {
                'keywords': ['launch', 'listing', 'ido', 'ico', 'public sale'],
                'effort_level': 'high',
                'time_sensitivity': 'high',
                'roi_potential': 'high'
            },
            'community_tasks': {
                'keywords': ['task', 'quest', 'mission', 'bounty', 'ambassador'],
                'effort_level': 'medium',
                'time_sensitivity': 'medium',
                'roi_potential': 'low'
            }
        }
        
        # Effort levels with estimated time
        self.effort_levels = {
            'low': 0.5,      # < 30 minutes
            'medium': 1.0,   # 30 min - 2 hours
            'high': 2.0      # > 2 hours
        }
        
        # ROI potential levels
        self.roi_levels = {
            'low': 1.0,      # 1-2x
            'medium': 2.0,   # 2-5x
            'high': 3.0      # > 5x
        }
        
        # Time sensitivity multipliers (higher = more urgent)
        self.time_sensitivity = {
            'low': 1.0,      # Weeks or longer
            'medium': 1.5,   # Days
            'high': 2.0      # Hours or immediate
        }
    
    def calculate_activity_score(self, project_id: int, days: int = 7) -> float:
        """Calculate project activity score based on recent mentions"""
        try:
            query = """
            SELECT COUNT(*) as mention_count
            FROM analyzed_data ad
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', ?)
            """
            
            results = db_manager.execute_query(query, (project_id, f'-{days} days'))
            
            if not results:
                return 0.0
                
            mention_count = results[0][0]
            
            # Normalize the score (sigmoid function)
            # 0 mentions = 0.0, 5 mentions = 0.5, 10+ mentions = ~1.0
            activity_score = 1.0 / (1.0 + math.exp(-0.4 * (mention_count - 5)))
            
            return activity_score
        except Exception as e:
            logger.error(f"Error calculating activity score for project {project_id}: {str(e)}")
            return 0.0
    
    def calculate_community_growth(self, project_id: int) -> float:
        """Calculate community growth score based on mention trends"""
        try:
            # Get mentions for last week
            query_recent = """
            SELECT COUNT(*) as recent_mentions
            FROM analyzed_data ad
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', '-7 days')
            """
            
            # Get mentions for previous week
            query_previous = """
            SELECT COUNT(*) as previous_mentions
            FROM analyzed_data ad
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', '-14 days')
            AND ad.analysis_timestamp < datetime('now', '-7 days')
            """
            
            recent_results = db_manager.execute_query(query_recent, (project_id,))
            previous_results = db_manager.execute_query(query_previous, (project_id,))
            
            if not recent_results or not previous_results:
                return 0.0
                
            recent_mentions = recent_results[0][0]
            previous_mentions = previous_results[0][0]
            
            # Calculate growth rate
            if previous_mentions == 0:
                # If no previous mentions, use 1 to avoid division by zero
                # Still rewards new projects but doesn't give excessive scores
                growth_rate = recent_mentions
            else:
                growth_rate = recent_mentions / previous_mentions
            
            # Normalize growth score (sigmoid function)
            # growth_rate of 1.0 = 0.5 (no change)
            # growth_rate < 1.0 = below 0.5 (shrinking)
            # growth_rate > 1.0 = above 0.5 (growing)
            growth_score = 1.0 / (1.0 + math.exp(-1.5 * (growth_rate - 1.0)))
            
            return growth_score
        except Exception as e:
            logger.error(f"Error calculating community growth for project {project_id}: {str(e)}")
            return 0.0
    
    def calculate_sentiment_score(self, project_id: int) -> float:
        """Calculate sentiment score based on context analysis"""
        try:
            # Get context data from analyzed data
            query = """
            SELECT ad.context
            FROM analyzed_data ad
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', '-14 days')
            """
            
            results = db_manager.execute_query(query, (project_id,))
            
            if not results:
                return 0.5  # Neutral if no data
            
            # Count positive and negative contexts
            positive_contexts = ['opportunity', 'alpha']
            negative_contexts = ['risk']
            
            positive_count = 0
            negative_count = 0
            total_count = len(results)
            
            for row in results:
                context_str = row[0]
                if not context_str:
                    continue
                    
                try:
                    contexts = json.loads(context_str)
                    
                    # Check for positive and negative contexts
                    if any(context in positive_contexts for context in contexts):
                        positive_count += 1
                    
                    if any(context in negative_contexts for context in contexts):
                        negative_count += 1
                except:
                    continue
            
            # Calculate sentiment ratio
            if total_count == 0:
                return 0.5  # Neutral if no context data
                
            # Calculate baseline positive ratio (0.0 to 1.0)
            positive_ratio = positive_count / total_count
            
            # Calculate baseline negative ratio (0.0 to 1.0)
            negative_ratio = negative_count / total_count
            
            # Calculate sentiment score
            # Scale from 0.0 (all negative) to 1.0 (all positive)
            # With a neutral baseline of 0.5
            sentiment_score = 0.5 + (positive_ratio * 0.5) - (negative_ratio * 0.5)
            sentiment_score = max(0.0, min(1.0, sentiment_score))  # Clamp to 0.0-1.0 range
            
            return sentiment_score
        except Exception as e:
            logger.error(f"Error calculating sentiment score for project {project_id}: {str(e)}")
            return 0.5  # Neutral score on error
    
    def calculate_urgency_score(self, project_id: int) -> float:
        """Calculate urgency score based on time-sensitive contexts"""
        try:
            # Get recent high priority items
            query = """
            SELECT ad.context, ad.categories, ad.priority_score
            FROM analyzed_data ad
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', '-7 days')
            AND ad.priority_score >= 1.3
            ORDER BY ad.priority_score DESC
            LIMIT 10
            """
            
            results = db_manager.execute_query(query, (project_id,))
            
            if not results:
                return 0.0  # No urgency if no high priority items
            
            # Check time-sensitive indicators in contexts and categories
            time_sensitive_count = 0
            total_count = len(results)
            max_priority_score = 0.0
            
            for row in results:
                context_str, categories_str, priority_score = row
                
                if priority_score > max_priority_score:
                    max_priority_score = priority_score
                
                try:
                    contexts = json.loads(context_str) if context_str else []
                    categories = json.loads(categories_str) if categories_str else []
                    
                    # Check for time-sensitive indicators
                    if ('time_sensitive' in contexts or 
                        'urgent_action' in categories or 
                        'upcoming_opportunity' in categories):
                        time_sensitive_count += 1
                except:
                    continue
            
            # Calculate urgency score
            # Combine ratio of time-sensitive items with max priority score
            time_sensitive_ratio = time_sensitive_count / total_count if total_count > 0 else 0.0
            
            # Normalize max priority score to 0.0-1.0 range
            # 1.0 = baseline, 2.0 = highly urgent
            normalized_priority = (max_priority_score - 1.0) / 1.0 if max_priority_score > 1.0 else 0.0
            normalized_priority = min(1.0, normalized_priority)  # Cap at 1.0
            
            # Combine metrics (weighted)
            urgency_score = (time_sensitive_ratio * 0.6) + (normalized_priority * 0.4)
            
            return urgency_score
        except Exception as e:
            logger.error(f"Error calculating urgency score for project {project_id}: {str(e)}")
            return 0.0
    
    def detect_opportunity_type(self, project_id: int) -> Tuple[str, float]:
        """Detect the type of opportunity for a project"""
        try:
            # Get recent messages to analyze for opportunity types
            query = """
            SELECT rd.content, ad.categories
            FROM analyzed_data ad
            JOIN raw_data rd ON ad.raw_data_id = rd.id
            WHERE ad.project_id = ?
            AND ad.analysis_timestamp >= datetime('now', '-7 days')
            """
            
            results = db_manager.execute_query(query, (project_id,))
            
            if not results:
                return "unknown", 0.0
            
            # Track opportunity type counts
            opportunity_counts = {opp_type: 0 for opp_type in self.opportunity_categories.keys()}
            total_items = len(results)
            
            # Analyze content for opportunity keywords
            for row in results:
                content, categories_str = row
                
                # Skip if no content
                if not content:
                    continue
                    
                content = content.lower()
                
                # Check each opportunity type
                for opp_type, opp_data in self.opportunity_categories.items():
                    # Look for keywords in the content
                    if any(keyword in content for keyword in opp_data['keywords']):
                        opportunity_counts[opp_type] += 1
                
                # Also check categories
                try:
                    categories = json.loads(categories_str) if categories_str else []
                    
                    # Map certain categories to opportunity types
                    category_to_opp = {
                        'upcoming_opportunity': ['whitelist', 'airdrop', 'token_launch'],
                        'active_investment': ['staking', 'farming'],
                        'testnet_participation': ['testnet'],
                        'community': ['community_tasks']
                    }
                    
                    for category, opp_types in category_to_opp.items():
                        if category in categories:
                            for opp_type in opp_types:
                                opportunity_counts[opp_type] += 0.5  # Partial weight from category match
                except:
                    pass
            
            # Find the most frequent opportunity type
            max_count = 0
            primary_opportunity = "unknown"
            
            for opp_type, count in opportunity_counts.items():
                if count > max_count:
                    max_count = count
                    primary_opportunity = opp_type
            
            # Calculate confidence (normalized by total items)
            confidence = max_count / total_items if total_items > 0 else 0.0
            confidence = min(1.0, confidence)  # Cap at 1.0
            
            return primary_opportunity, confidence
        except Exception as e:
            logger.error(f"Error detecting opportunity type for project {project_id}: {str(e)}")
            return "unknown", 0.0
    
    def calculate_roi_potential(self, project_id: int, opportunity_type: str) -> float:
        """Calculate ROI potential based on opportunity type and other factors"""
        try:
            project = get_project(project_id)
            
            if not project:
                return 0.0
                
            # Start with base ROI score from opportunity type
            if opportunity_type in self.opportunity_categories:
                roi_level = self.opportunity_categories[opportunity_type]['roi_potential']
                base_roi = self.roi_levels.get(roi_level, 1.0)
            else:
                base_roi = 1.0  # Default to low ROI potential
            
            # Adjust ROI based on activity and sentiment
            activity_score = self.calculate_activity_score(project_id)
            sentiment_score = self.calculate_sentiment_score(project_id)
            
            # Projects with high activity and positive sentiment have higher ROI potential
            adjusted_roi = base_roi * (1.0 + ((activity_score - 0.5) * 0.5) + ((sentiment_score - 0.5) * 0.5))
            
            # Normalize to 0.0-1.0 range
            normalized_roi = adjusted_roi / 3.0  # Max ROI level is 3.0
            normalized_roi = max(0.0, min(1.0, normalized_roi))  # Clamp to 0.0-1.0 range
            
            return normalized_roi
        except Exception as e:
            logger.error(f"Error calculating ROI potential for project {project_id}: {str(e)}")
            return 0.0
    
    def calculate_opportunity_score(self, project_id: int) -> Dict[str, Any]:
        """Calculate overall opportunity score for a project"""
        try:
            # Get base project information
            project = get_project(project_id)
            
            if not project:
                return {
                    'project_id': project_id,
                    'opportunity_score': 0.0,
                    'error': 'Project not found'
                }
            
            # Calculate component scores
            activity_score = self.calculate_activity_score(project_id)
            community_growth = self.calculate_community_growth(project_id)
            sentiment_score = self.calculate_sentiment_score(project_id)
            urgency_score = self.calculate_urgency_score(project_id)
            
            # Detect opportunity type
            opportunity_type, opportunity_confidence = self.detect_opportunity_type(project_id)
            
            # Calculate ROI potential
            roi_potential = self.calculate_roi_potential(project_id, opportunity_type)
            
            # Combine scores with weights
            weighted_score = (
                (activity_score * self.weights['activity_level']) +
                (community_growth * self.weights['community_growth']) +
                (sentiment_score * self.weights['sentiment']) +
                (urgency_score * self.weights['urgency']) +
                (roi_potential * self.weights['roi_potential'])
            )
            
            # Scale to 0-100 range for better readability
            opportunity_score = weighted_score * 100
            
            # Get effort level for opportunity type
            effort_level = 'medium'  # Default
            if opportunity_type in self.opportunity_categories:
                effort_level = self.opportunity_categories[opportunity_type]['effort_level']
            
            # Get time sensitivity for opportunity type
            time_sensitivity_level = 'medium'  # Default
            if opportunity_type in self.opportunity_categories:
                time_sensitivity_level = self.opportunity_categories[opportunity_type]['time_sensitivity']
            
            # Create result object
            result = {
                'project_id': project_id,
                'project_name': project['name'],
                'opportunity_score': opportunity_score,
                'opportunity_type': opportunity_type,
                'opportunity_confidence': opportunity_confidence,
                'component_scores': {
                    'activity': activity_score,
                    'community_growth': community_growth,
                    'sentiment': sentiment_score,
                    'urgency': urgency_score,
                    'roi_potential': roi_potential
                },
                'effort_level': effort_level,
                'time_sensitivity': time_sensitivity_level,
                'worth_participating': opportunity_score >= 70  # Consider above 70 worth participating
            }
            
            return result
        except Exception as e:
            logger.error(f"Error calculating opportunity score for project {project_id}: {str(e)}")
            return {
                'project_id': project_id,
                'opportunity_score': 0.0,
                'error': str(e)
            }
    
    def update_project_opportunity(self, project_id: int) -> Dict[str, Any]:
        """Update a project's opportunity score and details in the database"""
        try:
            # Calculate opportunity score
            opportunity = self.calculate_opportunity_score(project_id)
            
            if 'error' in opportunity:
                return opportunity
            
            # Prepare update data
            update_data = {
                'score': opportunity['opportunity_score'],
                'roi_potential': opportunity['opportunity_type'],
                'roi_score': opportunity['component_scores']['roi_potential'] * 100,  # Scale to 0-100
                'worth_participating': 1 if opportunity['worth_participating'] else 0
            }
            
            # Update the project in the database
            updated = update_project(project_id, update_data)
            
            if not updated:
                logger.warning(f"Failed to update project {project_id} with opportunity data")
            
            # Create an alert if this is a high-value opportunity
            if opportunity['opportunity_score'] >= 80:
                add_alert(
                    project_id=project_id,
                    alert_type='opportunity',
                    alert_message=f"High-value {opportunity['opportunity_type']} opportunity detected for {opportunity['project_name']} (Score: {opportunity['opportunity_score']:.1f})",
                    priority='high'
                )
            elif opportunity['opportunity_score'] >= 70:
                add_alert(
                    project_id=project_id,
                    alert_type='opportunity',
                    alert_message=f"Good {opportunity['opportunity_type']} opportunity detected for {opportunity['project_name']} (Score: {opportunity['opportunity_score']:.1f})",
                    priority='medium'
                )
            
            return opportunity
        except Exception as e:
            logger.error(f"Error updating opportunity for project {project_id}: {str(e)}")
            return {
                'project_id': project_id,
                'error': str(e)
            }
    
    def analyze_all_projects(self, min_activity: float = 0.3) -> List[Dict[str, Any]]:
        """Analyze all active projects and update their opportunity scores"""
        try:
            # Get all active projects
            projects = get_all_projects(active_only=True)
            
            results = []
            
            for project in projects:
                project_id = project['id']
                
                # First check if the project has enough activity to warrant full analysis
                activity_score = self.calculate_activity_score(project_id)
                
                # Skip projects with low activity
                if activity_score < min_activity:
                    results.append({
                        'project_id': project_id,
                        'project_name': project['name'],
                        'skipped': True,
                        'activity_score': activity_score,
                        'min_activity_threshold': min_activity
                    })
                    continue
                
                # Perform full opportunity analysis and update
                opportunity = self.update_project_opportunity(project_id)
                results.append(opportunity)
            
            # Sort results by opportunity score (descending)
            results.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
            
            return results
        except Exception as e:
            logger.error(f"Error analyzing all projects: {str(e)}")
            return []


# Main function for running as script
def analyze_opportunities():
    """Analyze opportunities for all projects"""
    analyzer = OpportunityAnalyzer()
    
    # Analyze all projects
    results = analyzer.analyze_all_projects()
    
    # Log high-opportunity projects
    high_opp_count = sum(1 for r in results if r.get('opportunity_score', 0) >= 70)
    logger.info(f"Found {high_opp_count} high-opportunity projects.")
    
    # Print top opportunities
    print(f"\nTop Opportunities:")
    for result in results[:10]:  # Top 10
        if 'opportunity_score' in result:
            print(f"- {result['project_name']}: {result['opportunity_score']:.1f} ({result['opportunity_type']})")
    
    return {
        'total_projects': len(results),
        'high_opportunity_projects': high_opp_count,
        'top_opportunities': results[:10]
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze project opportunities")
    parser.add_argument("--project", type=str, help="Analyze a specific project")
    parser.add_argument("--min-activity", type=float, default=0.3, 
                       help="Minimum activity score threshold (0.0-1.0)")
    parser.add_argument("--update-db", action="store_true", 
                       help="Update project records in database")
    args = parser.parse_args()
    
    analyzer = OpportunityAnalyzer()
    
    if args.project:
        # Analyze specific project
        project = get_project_by_name(args.project)
        if project:
            if args.update_db:
                opportunity = analyzer.update_project_opportunity(project['id'])
            else:
                opportunity = analyzer.calculate_opportunity_score(project['id'])
                
            print(f"\nOpportunity Analysis for {args.project}:")
            print(f"Overall Score: {opportunity.get('opportunity_score', 0):.1f}/100")
            print(f"Opportunity Type: {opportunity.get('opportunity_type', 'unknown')}")
            print(f"Confidence: {opportunity.get('opportunity_confidence', 0):.2f}")
            print(f"Effort Level: {opportunity.get('effort_level', 'unknown')}")
            print(f"Time Sensitivity: {opportunity.get('time_sensitivity', 'unknown')}")
            print(f"Worth Participating: {'Yes' if opportunity.get('worth_participating') else 'No'}")
            
            print("\nComponent Scores:")
            if 'component_scores' in opportunity:
                for name, score in opportunity['component_scores'].items():
                    print(f"- {name.replace('_', ' ').title()}: {score:.2f}")
        else:
            print(f"Project not found: {args.project}")
    else:
        # Analyze all projects
        results = analyzer.analyze_all_projects(min_activity=args.min_activity)
        
        if args.update_db:
            print(f"Updated {len(results)} projects in database.")
        
        # Count by opportunity type
        opp_types = {}
        for result in results:
            if 'opportunity_type' in result:
                opp_type = result['opportunity_type']
                if opp_type not in opp_types:
                    opp_types[opp_type] = 0
                opp_types[opp_type] += 1
        
        print("\nOpportunity Types:")
        for opp_type, count in sorted(opp_types.items(), key=lambda x: x[1], reverse=True):
            print(f"- {opp_type}: {count}")
        
        # Print top opportunities
        print(f"\nTop Opportunities:")
        for i, result in enumerate(results[:10], 1):  # Top 10
            if 'opportunity_score' in result:
                print(f"{i}. {result['project_name']}: {result['opportunity_score']:.1f} ({result['opportunity_type']})")
                print(f"   Time Sensitivity: {result.get('time_sensitivity', 'unknown')}, Effort: {result.get('effort_level', 'unknown')}")
                print(f"   Worth Participating: {'Yes' if result.get('worth_participating') else 'No'}")
            elif 'skipped' in result and result['skipped']:
                print(f"{i}. {result['project_name']}: Skipped (Activity: {result['activity_score']:.2f})")
            else:
                print(f"{i}. {result['project_name']}: Error - {result.get('error', 'Unknown error')}") 