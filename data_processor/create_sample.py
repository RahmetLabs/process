import pandas as pd
import random

def create_sample_data(input_file, output_file, sample_size=20):
    """Create a sample dataset with a mix of recent entries"""
    # Read the input CSV
    df = pd.read_csv(input_file)
    
    # Take a random sample of entries
    if len(df) > sample_size:
        sample_data = df.sample(n=sample_size, random_state=42)  # Fixed seed for reproducibility
    else:
        sample_data = df
    
    # Sort by timestamp/created_at to maintain chronological order
    date_column = 'created_at' if 'created_at' in df.columns else 'Timestamp'
    sample_data = sample_data.sort_values(by=date_column, ascending=False)
    
    # Save to new CSV
    sample_data.to_csv(output_file, index=False)
    print(f"Created sample file {output_file} with {len(sample_data)} entries")

if __name__ == "__main__":
    # Create sample Twitter data
    create_sample_data(
        "tweets_rows.csv",
        "data_processor/sample_tweets_recent.csv"
    )
    
    # Create sample Telegram data
    create_sample_data(
        "Telegram Data - Messages (1).csv",
        "data_processor/sample_telegram_recent.csv"
    )
