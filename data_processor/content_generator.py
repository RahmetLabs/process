import re
import os
import json
from datetime import datetime
import random

class ContentGenerator:
    def __init__(self):
        # Templates for different types of social media posts
        self.social_templates = {
            'testnet': [
                "🚀 New Testnet Alert: {project_name} has launched their testnet! Join now to earn potential rewards. #Web3 #Crypto #Testnet",
                "⚙️ {project_name} Testnet is LIVE! Set up your node and participate in this exciting project. #Blockchain #Testnet #Crypto",
                "🔍 Just discovered {project_name}'s testnet! This {category} project looks promising with {roi_level} potential. #Crypto #Testnet"
            ],
            'airdrop': [
                "💰 Airdrop Opportunity: {project_name} is distributing tokens! Check eligibility and participate now. #Airdrop #Crypto #FreeTokens",
                "🎁 Don't miss out on {project_name}'s token airdrop! Potential {roi_level} ROI opportunity. #Airdrop #Crypto #DeFi",
                "⚡ New Airdrop Alert: {project_name} is rewarding early supporters. Act fast before deadline: {deadline}. #Airdrop #Crypto"
            ],
            'nft': [
                "🖼️ {project_name} NFT mint is live! This collection has {roi_level} potential in the NFT space. #NFT #Crypto #Web3",
                "🎭 Just discovered {project_name}'s NFT project! Mint is {deadline}. #NFT #Crypto #DigitalArt",
                "🔥 Hot NFT Alert: {project_name} is dropping a new collection with unique utility. #NFT #Crypto #Web3Art"
            ],
            'defi': [
                "📈 {project_name} just launched their DeFi protocol with {roi_level} yield potential. #DeFi #Crypto #Yield",
                "💸 New yield opportunity on {project_name}! This {category} project offers competitive APY. #DeFi #Yield #Crypto",
                "🏦 {project_name} DeFi protocol is now live with innovative features. Worth exploring! #DeFi #Crypto #Finance"
            ],
            'dao': [
                "🏛️ {project_name} DAO is now accepting new members! Join this community-governed project. #DAO #Governance #Crypto",
                "🗳️ Governance Alert: {project_name} DAO is voting on important proposals. Get involved! #DAO #Crypto #Web3",
                "🌐 {project_name} launches DAO with unique governance model. Participation could yield {roi_level} returns. #DAO #Crypto"
            ],
            'layer2': [
                "⚡ {project_name} Layer 2 solution is now live! Faster and cheaper transactions for {blockchain}. #Layer2 #Scaling #Crypto",
                "🔗 {project_name} just launched their L2 network! This scaling solution has {roi_level} potential. #Layer2 #Blockchain",
                "📊 New Layer 2 Alert: {project_name} offers impressive TPS and low fees. Worth exploring! #Layer2 #Crypto #Scaling"
            ]
        }
        
        # Generic templates for any category
        self.generic_templates = [
            "📢 Project Update: {project_name} has new developments in the #Web3 space. Stay tuned for more information!",
            "👀 Keep an eye on {project_name}! This {category} project has {roi_level} potential. #Crypto #Web3",
            "🔎 Just researched {project_name} - an interesting project in the {category} space with {roi_level} ROI potential. #Crypto #Web3"
        ]
        
        # Templates for project guides
        self.guide_templates = {
            'testnet': """# {project_name} Testnet Participation Guide

## Overview
{project_name} is a {category} project that has recently launched its testnet phase. This guide will help you participate and potentially earn rewards.

## Requirements
{requirements}

## Setup Instructions
{setup_instructions}

## Verification
{verification}

## Rewards
Participants will be eligible for token rewards based on node uptime and participation metrics.

## Deadline
{deadline}

## Resources
- Official Website: {website}
- Twitter: {twitter}
- Discord: {discord}
- Documentation: {docs}
""",
            'airdrop': """# {project_name} Airdrop Guide

## Overview
{project_name} is distributing tokens through an airdrop campaign. This guide will help you check eligibility and claim your tokens.

## Eligibility
{eligibility}

## Claim Process
{claim_process}

## Token Information
{token_info}

## Deadline
{deadline}

## Resources
- Official Website: {website}
- Twitter: {twitter}
- Discord: {discord}
- Claim Page: {claim_page}
"""
        }
        
        # Templates for automation scripts
        self.script_templates = {
            'social_engagement': """
# Playwright script for {project_name} social engagement
from playwright.sync_api import sync_playwright
import time
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Login to Twitter
    page.goto('https://twitter.com/login')
    page.fill('input[name="text"]', os.getenv('TWITTER_USERNAME'))
    page.click('div[role="button"]:has-text("Next")')
    page.fill('input[name="password"]', os.getenv('TWITTER_PASSWORD'))
    page.click('div[role="button"]:has-text("Log in")')
    
    # Wait for login to complete
    page.wait_for_timeout(5000)
    
    # Engage with project
    page.goto('{project_url}')
    page.wait_for_timeout(3000)
    
    # Like the post
    try:
        page.click('div[data-testid="like"]')
        print("✅ Liked the post")
    except:
        print("❌ Could not like the post")
    
    # Retweet
    try:
        page.click('div[data-testid="retweet"]')
        page.wait_for_timeout(1000)
        page.click('div[role="menuitem"][data-testid="retweetConfirm"]')
        print("✅ Retweeted the post")
    except:
        print("❌ Could not retweet the post")
    
    # Follow if needed
    try:
        follow_button = page.query_selector('div[data-testid="followButton"]')
        if follow_button:
            follow_button.click()
            print("✅ Followed the account")
        else:
            print("ℹ️ Already following or follow button not found")
    except:
        print("❌ Could not follow the account")
    
    # Add a comment if required
    if {comment_required}:
        try:
            page.click('div[data-testid="reply"]')
            page.wait_for_timeout(1000)
            page.fill('div[data-testid="tweetTextarea_0"]', '{comment_text}')
            page.wait_for_timeout(1000)
            page.click('div[data-testid="tweetButton"]')
            print("✅ Added a comment")
        except:
            print("❌ Could not add a comment")
    
    # Take a screenshot for verification
    page.screenshot(path='{project_name}_engagement.png')
    print(f"✅ Screenshot saved as {project_name}_engagement.png")
    
    # Close browser
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
""",
            'node_setup': """
#!/bin/bash
# Automated setup script for {project_name} node

echo "Starting {project_name} node setup..."

# Create directory
mkdir -p {project_name}
cd {project_name}

# Clone repository
echo "Cloning repository..."
git clone {repo_url} .

# Install dependencies
echo "Installing dependencies..."
{install_dependencies}

# Configure node
echo "Configuring node..."
{configure_node}

# Start node
echo "Starting node..."
{start_node}

echo "Setup complete! Check logs for any errors."
echo "Node status command: {status_command}"
"""
        }
    
    def generate_social_post(self, project_data):
        """Generate a social media post based on project data"""
        # Get project information
        project_name = project_data.get('project_name', 'Unknown Project')
        categories = project_data.get('categories', [])
        roi_level = project_data.get('roi_potential', {}).get('level', 'Medium')
        
        # Get deadline if available
        deadline = next(iter(project_data.get('deadlines', {}).values()), 'soon')
        
        # Select template based on primary category
        template = None
        for category in categories:
            if category in self.social_templates:
                templates = self.social_templates[category]
                template = random.choice(templates)
                break
        
        # If no matching category, use generic template
        if not template:
            template = random.choice(self.generic_templates)
        
        # Format template with project data
        post = template.format(
            project_name=project_name,
            category=categories[0] if categories else 'blockchain',
            roi_level=roi_level,
            deadline=deadline,
            blockchain='Ethereum'  # Default, could be extracted from text
        )
        
        # Add URL if available
        url = project_data.get('url', project_data.get('message_link', ''))
        if url:
            post += f"\n\n{url}"
        
        # Add hashtags based on categories
        hashtags = []
        for category in categories:
            hashtags.append(f"#{category.title()}")
        
        if hashtags and not any(tag in post for tag in hashtags):
            post += f"\n\n{' '.join(hashtags)}"
        
        return post
    
    def generate_project_guide(self, project_data):
        """Generate a detailed project guide based on project data"""
        # Get project information
        project_name = project_data.get('project_name', 'Unknown Project')
        categories = project_data.get('categories', [])
        
        # Select template based on primary category
        template = None
        for category in categories:
            if category in self.guide_templates:
                template = self.guide_templates[category]
                break
        
        # If no matching category, return empty string
        if not template:
            return ""
        
        # Get requirements
        requirements_data = project_data.get('requirements', {})
        requirements_text = "### Hardware\n"
        if 'cpu' in requirements_data:
            requirements_text += f"- CPU: {requirements_data['cpu']} cores\n"
        else:
            requirements_text += "- CPU: 4 cores (recommended)\n"
            
        if 'ram' in requirements_data:
            requirements_text += f"- RAM: {requirements_data['ram']}\n"
        else:
            requirements_text += "- RAM: 8GB (recommended)\n"
            
        if 'storage' in requirements_data:
            requirements_text += f"- Storage: {requirements_data['storage']}\n"
        else:
            requirements_text += "- Storage: 100GB SSD (recommended)\n"
        
        requirements_text += "\n### Software\n"
        requirements_text += "- Ubuntu 20.04 or later\n"
        requirements_text += "- Docker (latest version)\n"
        requirements_text += "- Git\n"
        
        if 'social' in requirements_data:
            requirements_text += "\n### Social\n"
            for req in requirements_data['social']:
                requirements_text += f"- {req}\n"
        
        # Setup instructions
        setup_instructions = """1. Clone the repository:
```
git clone https://github.com/{project_name_lower}/testnet
```

2. Install dependencies:
```
cd testnet
./install.sh
```

3. Configure your node:
```
./configure.sh --wallet YOUR_WALLET_ADDRESS
```

4. Start the node:
```
./start.sh
```""".format(project_name_lower=project_name.lower().replace(' ', ''))
        
        # Verification
        verification = "Check your node status on the dashboard: https://testnet.{domain}/dashboard".format(
            domain=project_name.lower().replace(' ', '') + '.io'
        )
        
        # Deadline
        deadline = next(iter(project_data.get('deadlines', {}).values()), 'Not specified')
        
        # Format template with project data
        guide = template.format(
            project_name=project_name,
            category=categories[0] if categories else 'blockchain',
            requirements=requirements_text,
            setup_instructions=setup_instructions,
            verification=verification,
            deadline=deadline,
            website=f"https://{project_name.lower().replace(' ', '')}.io",
            twitter=f"https://twitter.com/{project_name.lower().replace(' ', '')}",
            discord=f"https://discord.gg/{project_name.lower().replace(' ', '')}",
            docs=f"https://docs.{project_name.lower().replace(' ', '')}.io",
            eligibility="Eligibility criteria will be announced on the project's official channels.",
            claim_process="The claim process will be detailed on the project's official website.",
            token_info="Token information will be provided by the project team.",
            claim_page=f"https://{project_name.lower().replace(' ', '')}.io/claim"
        )
        
        return guide
    
    def generate_automation_script(self, project_data, script_type):
        """Generate an automation script based on project data and script type"""
        # Get project information
        project_name = project_data.get('project_name', 'Unknown Project')
        
        # Select template based on script type
        if script_type not in self.script_templates:
            return ""
        
        template = self.script_templates[script_type]
        
        if script_type == 'social_engagement':
            # Get project URL
            url = project_data.get('url', '')
            if not url:
                url = f"https://twitter.com/search?q={project_name.replace(' ', '%20')}"
            
            # Generate random comment
            comments = [
                f"Excited to see what {project_name} brings to the ecosystem! #Crypto",
                f"This looks promising! Looking forward to the launch of {project_name}.",
                f"Great initiative by {project_name}! Can't wait to see more developments."
            ]
            
            # Format template with project data
            script = template.format(
                project_name=project_name,
                project_url=url,
                comment_required=str(random.choice([True, False])).lower(),
                comment_text=random.choice(comments)
            )
        
        elif script_type == 'node_setup':
            # Format template with project data
            project_name_lower = project_name.lower().replace(' ', '')
            
            # Generate install dependencies command based on likely requirements
            install_deps = """
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "package.json" ]; then
    npm install
elif [ -f "Dockerfile" ]; then
    docker build -t {project_name_lower} .
else
    echo "No dependency file found, attempting common installations..."
    apt-get update && apt-get install -y build-essential
fi""".format(project_name_lower=project_name_lower)
            
            # Generate configure node command
            configure_node = """
if [ -f "configure.sh" ]; then
    ./configure.sh --wallet $WALLET_ADDRESS
elif [ -f "config.json" ]; then
    cp config.example.json config.json
    # Replace wallet address placeholder
    sed -i 's/WALLET_ADDRESS/$WALLET_ADDRESS/g' config.json
else
    echo "No configuration file found, please check documentation."
fi""".format(project_name_lower=project_name_lower)
            
            # Generate start node command
            start_node = """
if [ -f "start.sh" ]; then
    ./start.sh
elif [ -f "docker-compose.yml" ]; then
    docker-compose up -d
elif [ -f "Dockerfile" ]; then
    docker run -d --name {project_name_lower}-node {project_name_lower}
else
    echo "No start script found, please check documentation."
fi""".format(project_name_lower=project_name_lower)
            
            # Format template with project data
            script = template.format(
                project_name=project_name,
                repo_url=f"https://github.com/{project_name_lower}/{project_name_lower}",
                install_dependencies=install_deps,
                configure_node=configure_node,
                start_node=start_node,
                status_command=f"docker logs {project_name_lower}-node" if "docker" in install_deps else f"./status.sh"
            )
        
        return script
    
    def generate_project_update(self, project_data):
        """Generate a project update based on project data"""
        # Get project information
        project_name = project_data.get('project_name', 'Unknown Project')
        categories = project_data.get('categories', [])
        roi_level = project_data.get('roi_potential', {}).get('level', 'Medium')
        text = project_data.get('text', '')
        
        # Extract key information
        investment_info = project_data.get('investment_info')
        participation_strategies = project_data.get('participation_strategies', [])
        
        update = f"# {project_name} Project Update\n\n"
        
        # Project category
        if categories:
            update += f"## Category\n{', '.join(c.title() for c in categories)}\n\n"
        
        # Investment information
        if investment_info:
            update += f"## Investment\n${investment_info:,.0f}\n\n"
        
        # ROI potential
        update += f"## ROI Potential\n{roi_level}\n\n"
        
        # Participation methods
        if participation_strategies:
            update += "## How to Participate\n"
            for strategy in participation_strategies:
                strategy_type = strategy.get('type', '').title()
                action = strategy.get('action', '').replace('_', ' ').title()
                difficulty = strategy.get('difficulty', '').title()
                update += f"- {strategy_type}: {action} (Difficulty: {difficulty})\n"
            update += "\n"
        
        # Deadlines
        deadlines = project_data.get('deadlines', {})
        if deadlines:
            update += "## Deadlines\n"
            for deadline_type, date in deadlines.items():
                update += f"- {deadline_type.title()}: {date}\n"
            update += "\n"
        
        # Extract key points from text
        update += "## Key Points\n"
        
        # Look for sentences with key information
        key_patterns = [
            r'[^.!?]*\b(launch|release|announce|introduce|unveil)\b[^.!?]*[.!?]',
            r'[^.!?]*\b(partner|collaboration|team up)\b[^.!?]*[.!?]',
            r'[^.!?]*\b(reward|incentive|earn|distribute)\b[^.!?]*[.!?]',
            r'[^.!?]*\b(require|need|must have)\b[^.!?]*[.!?]'
        ]
        
        key_points = []
        for pattern in key_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            key_points.extend(matches)
        
        # If no key points found, extract first 2-3 sentences
        if not key_points:
            sentences = re.split(r'[.!?]', text)
            key_points = [s.strip() + '.' for s in sentences[:3] if s.strip()]
        
        # Add key points to update
        for point in key_points:
            update += f"- {point}\n"
        
        return update
    
    def generate_all_content(self, project_data):
        """Generate all possible content for a project"""
        project_name = project_data.get('project_name', 'Unknown Project')
        
        # Create directory for project content
        dir_name = os.path.join('project_content', project_name.replace(' ', '_'))
        os.makedirs(dir_name, exist_ok=True)
        
        # Generate social media post
        social_post = self.generate_social_post(project_data)
        with open(os.path.join(dir_name, 'social_post.md'), 'w') as f:
            f.write(social_post)
        
        # Generate project guide
        guide = self.generate_project_guide(project_data)
        if guide:
            with open(os.path.join(dir_name, 'project_guide.md'), 'w') as f:
                f.write(guide)
        
        # Generate automation scripts
        participation_strategies = project_data.get('participation_strategies', [])
        for strategy in participation_strategies:
            action = strategy.get('action')
            if action in ['social_engagement', 'node_setup']:
                script = self.generate_automation_script(project_data, action)
                if script:
                    with open(os.path.join(dir_name, f'{action}_script.{"py" if action == "social_engagement" else "sh"}'), 'w') as f:
                        f.write(script)
        
        # Generate project update
        update = self.generate_project_update(project_data)
        with open(os.path.join(dir_name, 'project_update.md'), 'w') as f:
            f.write(update)
        
        return {
            'social_post': social_post,
            'guide': guide,
            'update': update,
            'directory': dir_name
        }

# Example usage
if __name__ == "__main__":
    generator = ContentGenerator()
    
    # Test with a sample project data
    sample_project = {
        'project_name': 'Quantum Chain',
        'categories': ['testnet', 'layer2'],
        'text': "Join the Quantum Chain testnet and earn rewards! $10M raised from a16z and Binance Labs. Mainnet launch in June 2025. Node requirements: 4 CPU cores, 8GB RAM, 100GB storage. Deadline is April 15, 2025.",
        'url': 'https://twitter.com/QuantumChain/status/1234567890',
        'roi_potential': {'level': 'High', 'score': 85},
        'participation_strategies': [
            {'type': 'technical', 'action': 'node_setup', 'difficulty': 'high'},
            {'type': 'social', 'action': 'social_engagement', 'difficulty': 'low'}
        ],
        'requirements': {
            'cpu': '4',
            'ram': '8GB',
            'storage': '100GB',
            'social': ['Twitter engagement']
        },
        'deadlines': {'submission': 'April 15, 2025'},
        'investment_info': 10000000
    }
    
    # Generate social post
    social_post = generator.generate_social_post(sample_project)
    print("=== Social Media Post ===")
    print(social_post)
    print("\n")
    
    # Generate project guide
    guide = generator.generate_project_guide(sample_project)
    print("=== Project Guide ===")
    print(guide[:200] + "...")  # Print just the beginning
    print("\n")
    
    # Generate automation script
    script = generator.generate_automation_script(sample_project, 'node_setup')
    print("=== Automation Script ===")
    print(script[:200] + "...")  # Print just the beginning
