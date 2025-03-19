import os
import json
import subprocess
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("automation_engine.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AutomationEngine")

class AutomationEngine:
    def __init__(self, config_path=None):
        # Default configuration
        self.config = {
            'social_accounts': {
                'twitter': {
                    'username': os.environ.get('TWITTER_USERNAME', ''),
                    'password': os.environ.get('TWITTER_PASSWORD', '')
                },
                'telegram': {
                    'phone': os.environ.get('TELEGRAM_PHONE', ''),
                    'api_id': os.environ.get('TELEGRAM_API_ID', ''),
                    'api_hash': os.environ.get('TELEGRAM_API_HASH', '')
                },
                'discord': {
                    'token': os.environ.get('DISCORD_TOKEN', '')
                }
            },
            'wallets': {
                'ethereum': {
                    'address': os.environ.get('ETH_ADDRESS', ''),
                    'private_key': os.environ.get('ETH_PRIVATE_KEY', '')
                },
                'solana': {
                    'address': os.environ.get('SOL_ADDRESS', ''),
                    'private_key': os.environ.get('SOL_PRIVATE_KEY', '')
                }
            },
            'node_servers': [
                {
                    'name': 'main-server',
                    'ip': os.environ.get('SERVER_IP', ''),
                    'username': os.environ.get('SERVER_USERNAME', ''),
                    'ssh_key': os.environ.get('SERVER_SSH_KEY', '')
                }
            ],
            'execution_limits': {
                'max_concurrent_tasks': 5,
                'max_daily_social_actions': 20,
                'max_daily_transactions': 10
            },
            'priority_categories': ['testnet', 'airdrop', 'defi', 'layer2'],
            'blacklisted_projects': [],
            'notification_email': os.environ.get('NOTIFICATION_EMAIL', '')
        }
        
        # Load configuration if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        
        # Initialize task queue and worker threads
        self.task_queue = queue.Queue()
        self.workers = []
        self.running = False
        
        # Initialize counters for daily limits
        self.daily_social_actions = 0
        self.daily_transactions = 0
        self.last_reset_date = datetime.now().date()
        
        # Create directories for scripts and logs
        os.makedirs('automation/scripts', exist_ok=True)
        os.makedirs('automation/logs', exist_ok=True)
        
        # Initialize task history
        self.task_history = []
    
    def reset_daily_counters(self):
        """Reset daily counters if it's a new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info(f"Resetting daily counters. Previous counts - Social: {self.daily_social_actions}, Transactions: {self.daily_transactions}")
            self.daily_social_actions = 0
            self.daily_transactions = 0
            self.last_reset_date = today
    
    def start_workers(self, num_workers=3):
        """Start worker threads to process tasks from the queue"""
        self.running = True
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker_thread, daemon=True)
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {num_workers} worker threads")
    
    def stop_workers(self):
        """Stop all worker threads"""
        self.running = False
        for _ in range(len(self.workers)):
            # Add None to queue to signal workers to exit
            self.task_queue.put(None)
        
        for worker in self.workers:
            worker.join()
        
        self.workers = []
        logger.info("All worker threads stopped")
    
    def _worker_thread(self):
        """Worker thread to process tasks from the queue"""
        while self.running:
            task = self.task_queue.get()
            if task is None:
                break
            
            try:
                task_type = task.get('type')
                project_name = task.get('project_name')
                logger.info(f"Processing {task_type} task for {project_name}")
                
                if task_type == 'social_engagement':
                    self._execute_social_task(task)
                elif task_type == 'node_setup':
                    self._execute_node_task(task)
                elif task_type == 'transaction':
                    self._execute_transaction_task(task)
                elif task_type == 'form_submission':
                    self._execute_form_task(task)
                else:
                    logger.warning(f"Unknown task type: {task_type}")
                
                # Record task in history
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                self.task_history.append(task)
                
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                task['status'] = 'failed'
                task['error'] = str(e)
                self.task_history.append(task)
            
            finally:
                self.task_queue.task_done()
    
    def schedule_task(self, task, execution_time=None):
        """Schedule a task for execution"""
        # Check if project is blacklisted
        if task.get('project_name') in self.config['blacklisted_projects']:
            logger.warning(f"Project {task.get('project_name')} is blacklisted. Task not scheduled.")
            return False
        
        # Check daily limits
        self.reset_daily_counters()
        
        if task.get('type') == 'social_engagement' and self.daily_social_actions >= self.config['execution_limits']['max_daily_social_actions']:
            logger.warning("Daily social actions limit reached. Task not scheduled.")
            return False
        
        if task.get('type') == 'transaction' and self.daily_transactions >= self.config['execution_limits']['max_daily_transactions']:
            logger.warning("Daily transactions limit reached. Task not scheduled.")
            return False
        
        # Add task to history
        task['status'] = 'scheduled'
        task['scheduled_at'] = datetime.now().isoformat()
        if execution_time:
            task['execution_time'] = execution_time.isoformat()
        self.task_history.append(task)
        
        # If execution time is provided, schedule the task
        if execution_time:
            delay = (execution_time - datetime.now()).total_seconds()
            if delay > 0:
                threading.Timer(delay, lambda: self.task_queue.put(task)).start()
                logger.info(f"Task for {task.get('project_name')} scheduled at {execution_time}")
                return True
        
        # Otherwise, add to queue immediately
        self.task_queue.put(task)
        logger.info(f"Task for {task.get('project_name')} added to queue")
        return True
    
    def _execute_social_task(self, task):
        """Execute a social engagement task"""
        platform = task.get('platform', 'twitter')
        script_path = task.get('script_path')
        
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Execute the script
        if platform == 'twitter':
            # Check if we need to increment the counter
            self.daily_social_actions += 1
            
            # Run the script
            result = subprocess.run(['python', script_path], 
                                   capture_output=True, 
                                   text=True,
                                   env={
                                       **os.environ,
                                       'TWITTER_USERNAME': self.config['social_accounts']['twitter']['username'],
                                       'TWITTER_PASSWORD': self.config['social_accounts']['twitter']['password']
                                   })
            
            if result.returncode != 0:
                raise Exception(f"Script execution failed: {result.stderr}")
            
            logger.info(f"Social task completed for {task.get('project_name')}")
            return result.stdout
        
        elif platform == 'telegram':
            # Implementation for Telegram
            pass
        
        elif platform == 'discord':
            # Implementation for Discord
            pass
        
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def _execute_node_task(self, task):
        """Execute a node setup task"""
        script_path = task.get('script_path')
        server_name = task.get('server_name', 'main-server')
        
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Find server configuration
        server = next((s for s in self.config['node_servers'] if s['name'] == server_name), None)
        if not server:
            raise ValueError(f"Server configuration not found for: {server_name}")
        
        # Copy script to server
        scp_command = [
            'scp', 
            '-i', server['ssh_key'],
            script_path,
            f"{server['username']}@{server['ip']}:~/node_setup.sh"
        ]
        
        result = subprocess.run(scp_command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to copy script to server: {result.stderr}")
        
        # Execute script on server
        ssh_command = [
            'ssh',
            '-i', server['ssh_key'],
            f"{server['username']}@{server['ip']}",
            'bash ~/node_setup.sh'
        ]
        
        result = subprocess.run(ssh_command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to execute script on server: {result.stderr}")
        
        logger.info(f"Node setup task completed for {task.get('project_name')}")
        return result.stdout
    
    def _execute_transaction_task(self, task):
        """Execute a blockchain transaction task"""
        blockchain = task.get('blockchain', 'ethereum')
        script_path = task.get('script_path')
        
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Check if we need to increment the counter
        self.daily_transactions += 1
        
        # Get wallet information
        wallet = self.config['wallets'].get(blockchain)
        if not wallet:
            raise ValueError(f"Wallet configuration not found for: {blockchain}")
        
        # Execute the script
        result = subprocess.run(['python', script_path], 
                               capture_output=True, 
                               text=True,
                               env={
                                   **os.environ,
                                   f'{blockchain.upper()}_ADDRESS': wallet['address'],
                                   f'{blockchain.upper()}_PRIVATE_KEY': wallet['private_key']
                               })
        
        if result.returncode != 0:
            raise Exception(f"Script execution failed: {result.stderr}")
        
        logger.info(f"Transaction task completed for {task.get('project_name')}")
        return result.stdout
    
    def _execute_form_task(self, task):
        """Execute a form submission task"""
        script_path = task.get('script_path')
        
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Execute the script
        result = subprocess.run(['python', script_path], 
                               capture_output=True, 
                               text=True,
                               env=os.environ)
        
        if result.returncode != 0:
            raise Exception(f"Script execution failed: {result.stderr}")
        
        logger.info(f"Form submission task completed for {task.get('project_name')}")
        return result.stdout
    
    def create_social_engagement_task(self, project_data, script_path, platform='twitter', execution_time=None):
        """Create a social engagement task"""
        task = {
            'type': 'social_engagement',
            'project_name': project_data.get('project_name', 'Unknown Project'),
            'platform': platform,
            'script_path': script_path,
            'project_url': project_data.get('url', ''),
            'created_at': datetime.now().isoformat()
        }
        
        return self.schedule_task(task, execution_time)
    
    def create_node_setup_task(self, project_data, script_path, server_name='main-server', execution_time=None):
        """Create a node setup task"""
        task = {
            'type': 'node_setup',
            'project_name': project_data.get('project_name', 'Unknown Project'),
            'server_name': server_name,
            'script_path': script_path,
            'requirements': project_data.get('requirements', {}),
            'created_at': datetime.now().isoformat()
        }
        
        return self.schedule_task(task, execution_time)
    
    def create_transaction_task(self, project_data, script_path, blockchain='ethereum', execution_time=None):
        """Create a blockchain transaction task"""
        task = {
            'type': 'transaction',
            'project_name': project_data.get('project_name', 'Unknown Project'),
            'blockchain': blockchain,
            'script_path': script_path,
            'amount': project_data.get('amount', 0),
            'created_at': datetime.now().isoformat()
        }
        
        return self.schedule_task(task, execution_time)
    
    def create_form_submission_task(self, project_data, script_path, execution_time=None):
        """Create a form submission task"""
        task = {
            'type': 'form_submission',
            'project_name': project_data.get('project_name', 'Unknown Project'),
            'script_path': script_path,
            'form_url': project_data.get('form_url', ''),
            'created_at': datetime.now().isoformat()
        }
        
        return self.schedule_task(task, execution_time)
    
    def generate_task_report(self):
        """Generate a report of all tasks"""
        if not self.task_history:
            return "No tasks have been scheduled or executed."
        
        report = "# Task Execution Report\n\n"
        
        # Group tasks by status
        tasks_by_status = {
            'completed': [],
            'scheduled': [],
            'failed': []
        }
        
        for task in self.task_history:
            status = task.get('status')
            if status in tasks_by_status:
                tasks_by_status[status].append(task)
        
        # Report on completed tasks
        report += "## Completed Tasks\n\n"
        if tasks_by_status['completed']:
            for task in tasks_by_status['completed']:
                project_name = task.get('project_name', 'Unknown Project')
                task_type = task.get('type', 'Unknown Type')
                completed_at = task.get('completed_at', 'Unknown Time')
                
                report += f"- {project_name}: {task_type.replace('_', ' ').title()} completed at {completed_at}\n"
        else:
            report += "No completed tasks.\n"
        
        report += "\n"
        
        # Report on scheduled tasks
        report += "## Scheduled Tasks\n\n"
        if tasks_by_status['scheduled']:
            for task in tasks_by_status['scheduled']:
                project_name = task.get('project_name', 'Unknown Project')
                task_type = task.get('type', 'Unknown Type')
                execution_time = task.get('execution_time', 'As soon as possible')
                
                report += f"- {project_name}: {task_type.replace('_', ' ').title()} scheduled for {execution_time}\n"
        else:
            report += "No scheduled tasks.\n"
        
        report += "\n"
        
        # Report on failed tasks
        report += "## Failed Tasks\n\n"
        if tasks_by_status['failed']:
            for task in tasks_by_status['failed']:
                project_name = task.get('project_name', 'Unknown Project')
                task_type = task.get('type', 'Unknown Type')
                error = task.get('error', 'Unknown error')
                
                report += f"- {project_name}: {task_type.replace('_', ' ').title()} failed - {error}\n"
        else:
            report += "No failed tasks.\n"
        
        return report
    
    def save_task_history(self, filename='task_history.json'):
        """Save task history to a file"""
        with open(filename, 'w') as f:
            json.dump(self.task_history, f, indent=2)
        
        logger.info(f"Task history saved to {filename}")
    
    def load_task_history(self, filename='task_history.json'):
        """Load task history from a file"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                self.task_history = json.load(f)
            
            logger.info(f"Task history loaded from {filename}")
    
    def process_analyzed_opportunities(self, opportunities):
        """Process a list of analyzed opportunities and create appropriate tasks"""
        for opportunity in opportunities:
            # Skip if not worth participating
            if not opportunity.get('worth_participating', False):
                continue
            
            project_name = opportunity.get('project_name', 'Unknown Project')
            participation_strategies = opportunity.get('participation_strategies', [])
            
            # Create directory for project scripts
            project_dir = os.path.join('automation/scripts', project_name.replace(' ', '_'))
            os.makedirs(project_dir, exist_ok=True)
            
            # Process each participation strategy
            for strategy in participation_strategies:
                strategy_type = strategy.get('type')
                action = strategy.get('action')
                
                # Skip if no action defined
                if not action:
                    continue
                
                # Generate script path
                script_filename = f"{action}_script.{'py' if action != 'node_setup' else 'sh'}"
                script_path = os.path.join(project_dir, script_filename)
                
                # Check if script exists
                if not os.path.exists(script_path):
                    logger.warning(f"Script not found for {project_name} - {action}: {script_path}")
                    continue
                
                # Schedule task based on strategy type
                if action == 'social_engagement':
                    self.create_social_engagement_task(opportunity, script_path)
                
                elif action == 'node_setup':
                    self.create_node_setup_task(opportunity, script_path)
                
                elif action == 'transaction':
                    self.create_transaction_task(opportunity, script_path)
                
                elif action == 'form_submission':
                    self.create_form_submission_task(opportunity, script_path)
                
                logger.info(f"Created {action} task for {project_name}")
        
        logger.info(f"Processed {len(opportunities)} opportunities")

# Example usage
if __name__ == "__main__":
    # Create automation engine
    engine = AutomationEngine()
    
    # Start worker threads
    engine.start_workers(2)
    
    # Sample project data
    sample_project = {
        'project_name': 'Quantum Chain',
        'categories': ['testnet', 'layer2'],
        'worth_participating': True,
        'participation_strategies': [
            {'type': 'technical', 'action': 'node_setup', 'difficulty': 'high'},
            {'type': 'social', 'action': 'social_engagement', 'difficulty': 'low'}
        ],
        'requirements': {
            'cpu': '4',
            'ram': '8GB',
            'storage': '100GB'
        },
        'url': 'https://twitter.com/QuantumChain/status/1234567890'
    }
    
    # Create sample scripts
    os.makedirs('automation/scripts/Quantum_Chain', exist_ok=True)
    
    # Sample social script
    with open('automation/scripts/Quantum_Chain/social_engagement_script.py', 'w') as f:
        f.write("""
# Sample social engagement script
print("Executing social engagement for Quantum Chain")
print("Success!")
""")
    
    # Sample node setup script
    with open('automation/scripts/Quantum_Chain/node_setup_script.sh', 'w') as f:
        f.write("""
#!/bin/bash
echo "Setting up Quantum Chain node"
echo "Success!"
""")
    
    # Create tasks
    engine.create_social_engagement_task(
        sample_project, 
        'automation/scripts/Quantum_Chain/social_engagement_script.py'
    )
    
    engine.create_node_setup_task(
        sample_project,
        'automation/scripts/Quantum_Chain/node_setup_script.sh'
    )
    
    # Wait for tasks to complete
    time.sleep(5)
    
    # Generate and print report
    report = engine.generate_task_report()
    print(report)
    
    # Stop worker threads
    engine.stop_workers()
