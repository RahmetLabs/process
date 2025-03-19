import pandas as pd
from data_classifier import DataClassifier

def test_twitter_data():
    # Create sample Twitter data
    twitter_data = {
        'text': [
            "Join our testnet and become a validator!",
            "New NFT collection dropping soon! Get whitelisted.",
            "Stake your tokens for high yield in our DeFi protocol",
            "Participate in our airdrop campaign!"
        ],
        'created_at': ['2025-03-17'] * 4,
        'likes': [10, 20, 30, 40],
        'retweets': [5, 10, 15, 20]
    }
    
    df = pd.DataFrame(twitter_data)
    
    # Initialize classifier
    classifier = DataClassifier()
    
    # Process data
    results = classifier.process_twitter_data(df)
    
    # Print results
    print("\nTwitter Data Analysis:")
    print("-" * 50)
    for result in results:
        print(f"\nText: {result['text']}")
        print(f"Categories: {result['categories']}")
        print(f"Likes: {result['likes']}")
        print(f"Retweets: {result['retweets']}")

def test_telegram_data():
    # Create sample Telegram data
    telegram_data = {
        'Message Text': [
            "New testnet phase starting tomorrow!",
            "Don't miss our NFT mint event",
            "Earn high yields in our DeFi pools",
            "Token airdrop for early supporters"
        ],
        'Channel': ['Project A', 'Project B', 'Project C', 'Project D'],
        'Timestamp': ['2025-03-17'] * 4
    }
    
    df = pd.DataFrame(telegram_data)
    
    # Initialize classifier
    classifier = DataClassifier()
    
    # Process data
    results = classifier.process_telegram_data(df)
    
    # Print results
    print("\nTelegram Data Analysis:")
    print("-" * 50)
    for result in results:
        print(f"\nText: {result['text']}")
        print(f"Categories: {result['categories']}")
        print(f"Channel: {result['channel']}")

if __name__ == "__main__":
    print("Testing Data Classifier")
    print("=" * 50)
    
    # Test Twitter data processing
    test_twitter_data()
    
    # Test Telegram data processing
    test_telegram_data()
