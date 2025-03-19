# CryptoFarm Quick Start Guide

This guide will help you get the CryptoFarm system up and running quickly.

## 1. Prerequisites

- Python 3.9+ installed
- Git installed
- Basic knowledge of terminal/command line
- Telegram API credentials (for Telegram scraping)
- Twitter API credentials (for Twitter scraping, optional)

## 2. Installation

### Clone the repository

```bash
git clone <your-repository-url> cryptofarm
cd cryptofarm
```

### Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configuration

### Create environment file

Create a `.env` file in the root directory with your API credentials:

```
# Telegram API credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone_number

# Twitter API credentials (optional)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# OpenAI API key (optional, for LLM features)
OPENAI_API_KEY=your_openai_api_key
```

### Configure data sources

Edit the files in the `config` directory:

- `config/main.json` - Main application settings
- `config/sources.json` - Data sources (Telegram channels, Twitter accounts)
- `config/projects.json` - Projects to track (high and medium priority)

## 4. Setup Database

Initialize the database:

```bash
python cryptofarm/setup_database.py
```

To reset the database at any time:

```bash
python cryptofarm/setup_database.py --reset
```

## 5. Running the System

### Data Collection

To collect data from Telegram:

```bash
python cryptofarm/collection_service.py --telegram
```

To collect data from all available sources:

```bash
python cryptofarm/collection_service.py --all
```

To run continuous collection:

```bash
python cryptofarm/collection_service.py --continuous --interval 300
```

### Data Processing

To process collected data:

```bash
python cryptofarm/data_processor/main.py
```

To only analyze opportunities without processing new data:

```bash
python cryptofarm/data_processor/main.py --analyze-only
```

To run continuous processing:

```bash
python cryptofarm/data_processor/main.py --continuous --interval 900
```

### Full System (Recommended Setup)

For production use, run these two services in separate terminals:

Terminal 1 (Data Collection):
```bash
python cryptofarm/collection_service.py --continuous --interval 300
```

Terminal 2 (Data Processing):
```bash
python cryptofarm/data_processor/main.py --continuous --interval 900
```

## 6. Analyzing Results

### Check Alerts

All high-priority alerts will be logged in the database. You can view these by running:

```bash
python cryptofarm/data_processor/main.py --process-only
```

### View Opportunities

To see the current farming opportunities:

```bash
python cryptofarm/data_processor/opportunity_analyzer.py
```

To analyze a specific project:

```bash
python cryptofarm/data_processor/opportunity_analyzer.py --project "Ethereum"
```

## 7. Adding New Projects

1. Add the project to `config/projects.json`
2. Add relevant data sources to `config/sources.json`
3. Restart the collection and processing services

## 8. Troubleshooting

### Logs

Check the log files for errors:

- `collection_service.log` - Collection service logs
- `data_processor.log` - Data processing logs
- `setup_database.log` - Database setup logs

### Common Issues

1. **API Authentication Failures**: Ensure your API credentials are correct in the `.env` file
2. **Database Errors**: Try resetting the database with `--reset` flag
3. **Data Collection Issues**: Check network connectivity and API rate limits

## 9. Next Steps

- Explore the API functionality (once implemented)
- Set up the dashboard (coming soon)
- Configure notifications for high-priority opportunities
- Implement custom workflows for automated farming 