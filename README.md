# CryptoFarm

CryptoFarm is an autonomous system for tracking and managing crypto/blockchain projects, allowing you to monitor opportunities, collect data, and streamline your crypto farming operations.

## Overview

CryptoFarm aims to automate the process of monitoring, analyzing, and acting upon crypto opportunities by collecting data from various sources like Telegram, Twitter, and Discord, classifying that data, and identifying high-value opportunities.

The system provides:

- **Automated data collection** from multiple sources (Telegram, Twitter, Discord)
- **Intelligent data classification** to identify relevant information
- **Opportunity scoring** to prioritize high-value farming opportunities
- **Alerts** for time-sensitive opportunities
- **Project tracking** for maintaining a database of blockchain projects

## System Architecture

CryptoFarm is built with a modular architecture:

1. **Data Collection Layer**
   - Telegram Scraper
   - Twitter Scraper
   - Discord Scraper

2. **Data Processing Layer**
   - Message Classification
   - Project Identification
   - Opportunity Analysis

3. **Storage Layer**
   - SQLite Database
   - JSON Configuration

4. **Interface Layer** (planned)
   - Command Line Interface
   - Web Dashboard
   - Notification System

## Key Components

### Data Collection

- `collection_service.py`: Orchestrates data collection from all sources
- `telegram_scraper.py`: Collects data from Telegram channels
- `twitter_scraper.py`: Collects data from Twitter accounts
- `discord_scraper.py`: Collects data from Discord channels

### Data Processing

- `data_processor/main.py`: Main processing pipeline
- `data_classifier.py`: Classifies collected messages
- `opportunity_analyzer.py`: Analyzes and scores opportunities

### Database Management

- `db_utils.py`: Database utility functions
- `setup_database.py`: Database initialization and setup

### Configuration

- `config/main.json`: Main application settings
- `config/sources.json`: Data source configuration
- `config/projects.json`: Project tracking configuration

## Getting Started

See the [QUICKSTART.md](QUICKSTART.md) guide for detailed setup and usage instructions.

### Quick Installation

```bash
# Clone the repository
git clone <repository-url> cryptofarm
cd cryptofarm

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
python cryptofarm/setup_database.py
```

### Basic Usage

```bash
# Collect data from Telegram
python cryptofarm/collection_service.py --telegram

# Process collected data
python cryptofarm/data_processor/main.py

# Run continuous data collection and processing
python cryptofarm/collection_service.py --continuous &
python cryptofarm/data_processor/main.py --continuous &
```

## Configuration

### Database Configuration

The system uses an SQLite database by default. Database settings can be adjusted in `config/main.json`.

### API Credentials

To use the data collectors, you need to set up the necessary API credentials:

1. **Telegram API**: Create a `.env` file with your Telegram API credentials:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_PHONE=your_phone_number
   ```

2. **Twitter API** (optional): Add Twitter API credentials to the `.env` file:
   ```
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
   ```

## Data Sources and Projects

### Adding Data Sources

Edit `config/sources.json` to add or modify data sources:

```json
{
  "telegram": [
    {
      "name": "Example Channel",
      "id": "example_channel",
      "username": "examplechannel",
      "priority": "high"
    }
  ]
}
```

### Adding Projects

Edit `config/projects.json` to add or modify projects:

```json
{
  "high_priority": [
    {
      "name": "Project Name",
      "symbol": "PJT",
      "keywords": ["keyword1", "keyword2"],
      "contracts": [
        {"chain": "ethereum", "address": "0x123..."}
      ],
      "official_channels": ["telegram:official_channel_id"]
    }
  ]
}
```

## Future Enhancements

- Web-based dashboard
- Advanced data analytics
- Automated farming actions
- Machine learning integration
- Integration with DeFi protocols

## License

[MIT License](LICENSE)

## Acknowledgements

- This project was inspired by the need for automated crypto farming opportunity detection
- Thanks to all the open source libraries that made this possible
