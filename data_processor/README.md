# Web3 Opportunity Automation System

A comprehensive system for automating the analysis, content generation, and participation in Web3 opportunities based on scraped Twitter and Telegram data.

## Overview

This system processes data from Twitter and Telegram to:

1. **Identify valuable opportunities** in the Web3 space
2. **Generate content** for social media and project guides
3. **Automate participation** in testnets, airdrops, and other activities
4. **Track projects** and calculate ROI

## Components

The system consists of five main components:

1. **Data Classifier** (`data_classifier.py`): Categorizes and scores opportunities from scraped data
2. **Opportunity Analyzer** (`opportunity_analyzer.py`): Evaluates projects for participation worthiness
3. **Content Generator** (`content_generator.py`): Creates social media posts, guides, and automation scripts
4. **Automation Engine** (`automation_engine.py`): Executes participation tasks across platforms
5. **Project Tracker** (`project_tracker.py`): Maintains a database of projects and participation status

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/web3-opportunity-automation.git
cd web3-opportunity-automation

# Install dependencies
pip install -r requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm

# Install Playwright browsers
playwright install
```

## Usage

### Basic Usage

```bash
python main.py --twitter path/to/tweets.csv --telegram path/to/telegram_messages.csv
```

### Analysis Only

```bash
python main.py --twitter path/to/tweets.csv --telegram path/to/telegram_messages.csv --analyze-only
```

### Content Generation Only

```bash
python main.py --twitter path/to/tweets.csv --telegram path/to/telegram_messages.csv --generate-only
```

### Report Generation Only

```bash
python main.py --report-only
```

## Configuration

Create a `config.json` file with the following structure:

```json
{
  "social_accounts": {
    "twitter": {
      "username": "your_username",
      "password": "your_password"
    },
    "telegram": {
      "phone": "your_phone",
      "api_id": "your_api_id",
      "api_hash": "your_api_hash"
    },
    "discord": {
      "token": "your_token"
    }
  },
  "wallets": {
    "ethereum": {
      "address": "your_eth_address",
      "private_key": "your_private_key"
    },
    "solana": {
      "address": "your_sol_address",
      "private_key": "your_private_key"
    }
  },
  "node_servers": [
    {
      "name": "main-server",
      "ip": "server_ip",
      "username": "server_username",
      "ssh_key": "path/to/ssh_key"
    }
  ],
  "execution_limits": {
    "max_concurrent_tasks": 5,
    "max_daily_social_actions": 20,
    "max_daily_transactions": 10
  },
  "priority_categories": ["testnet", "airdrop", "defi", "layer2"],
  "blacklisted_projects": [],
  "notification_email": "your_email@example.com"
}
```

Alternatively, set environment variables with the same names.

## Output

The system generates the following outputs:

1. **Project Content**: Social media posts, guides, and automation scripts for each project
2. **Reports**: Summary reports of opportunities and task execution
3. **Database**: SQLite database tracking projects and participation
4. **Charts**: Visualizations of ROI potential and project categories

## Security Notes

- **NEVER** store your private keys or passwords directly in the code
- Use environment variables or a secure configuration file
- Consider using a dedicated wallet for automated transactions

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
