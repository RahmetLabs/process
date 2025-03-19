import argparse
import json
import sys
from datetime import datetime
from data_classifier import DataClassifier
from config import ProjectConfig
import pandas as pd

# Set UTF-8 encoding for stdout
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_data(file_path):
    """Load data from CSV file"""
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return None

def save_results(results, analytics):
    """Save processing results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"analysis_results_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'results': results,
                'analytics': analytics
            }, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to {output_file}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")

def print_analytics_summary(analytics):
    """Print a summary of the analytics"""
    print("\nAnalytics Summary")
    print("=" * 50 + "\n")

    # Print total items processed
    print("Total Items Processed:")
    print(f"- Twitter: {analytics['total_items']['twitter']}")
    print(f"- Telegram: {analytics['total_items']['telegram']}\n")

    # Print project mentions
    if analytics.get('project_mentions'):
        print("Project Activity:")
        for project, data in sorted(analytics['project_mentions'].items(), 
                                  key=lambda x: len(x[1]['priority_items']), reverse=True):
            print(f"\n- {project}")
            print(f"  Mentions: {data['mentions']}")
            print(f"  Active Channels: {len(data['channels'])}")
            print(f"  Priority Updates: {len(data['priority_items'])}")
        print()

    # Print high priority items
    if analytics.get('high_priority_items'):
        print("High Priority Updates:")
        for item in analytics['high_priority_items'][:5]:  # Show top 5
            print(f"\n- Source: {item['source'].title()} ({item['channel']})")
            print(f"  Priority Score: {item['priority_score']:.2f}")
            if item['projects']:
                print(f"  Projects: {', '.join(p['name'] for p in item['projects'])}")
            print(f"  Categories: {', '.join(item['categories'])}")
            if item['context']:
                print(f"  Context: {', '.join(item['context'])}")
            print(f"  Text: {item['text'][:100]}...")
        print()

    # Print category distribution
    print("Category Distribution:")
    for category, count in sorted(analytics['category_distribution'].items(), key=lambda x: x[1], reverse=True):
        if count > 0:  # Only show categories with items
            print(f"- {category}: {count}")
    print()

    # Print context distribution
    if analytics.get('context_distribution'):
        print("Context Indicators:")
        for context, count in sorted(analytics['context_distribution'].items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"- {context}: {count}")
        print()

    # Print most active channels with their focus
    if analytics.get('channel_categories'):
        print("Most Active Channels and Their Focus:")
        for channel, data in sorted(analytics['channel_categories'].items(), 
                                  key=lambda x: len(x[1]['messages']), reverse=True)[:5]:
            try:
                msg_count = len(data['messages'])
                categories = data['top_categories']
                projects = data['projects']
                
                print(f"\n- {channel} ({msg_count} messages)")
                if projects:
                    print(f"  Projects: {', '.join(projects)}")
                if categories:
                    print(f"  Top Categories: {', '.join(categories)}")
            except Exception as e:
                print(f"Error displaying channel {channel}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Process Web3 data from Twitter and Telegram')
    parser.add_argument('--twitter', help='Path to Twitter data CSV')
    parser.add_argument('--telegram', help='Path to Telegram data CSV')
    parser.add_argument('--config', help='Path to project configuration file')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze existing results')
    args = parser.parse_args()

    # Initialize configuration
    config = ProjectConfig()
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
                for priority, projects in config_data.items():
                    for project in projects:
                        config.add_project(priority, project)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            return

    classifier = DataClassifier(config)
    results = []
    
    if args.twitter:
        print("\nProcessing Twitter data...")
        twitter_data = load_data(args.twitter)
        if twitter_data is not None:
            twitter_results = classifier.process_twitter_data(twitter_data)
            results.extend(twitter_results)
            print(f"Processed {len(twitter_results)} Twitter entries")
    
    if args.telegram:
        print("\nProcessing Telegram data...")
        telegram_data = load_data(args.telegram)
        if telegram_data is not None:
            telegram_results = classifier.process_telegram_data(telegram_data)
            results.extend(telegram_results)
            print(f"Processed {len(telegram_results)} Telegram entries")
    
    # Generate and save analytics
    analytics = classifier.generate_analytics(
        twitter_data=[r for r in results if r['source'] == 'twitter'],
        telegram_data=[r for r in results if r['source'] == 'telegram']
    )
    
    save_results(results, analytics)
    print_analytics_summary(analytics)

if __name__ == "__main__":
    main()
