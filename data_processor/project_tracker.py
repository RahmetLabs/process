import sqlite3
import json
import os
import logging
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import csv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("project_tracker.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ProjectTracker")

class ProjectTracker:
    def __init__(self, db_path='projects.db'):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Set up SQLite database for project tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create projects table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            score REAL,
            roi_potential TEXT,
            roi_score REAL,
            investment_amount REAL,
            participation_status TEXT,
            date_added TEXT,
            deadline TEXT,
            source TEXT,
            source_url TEXT,
            worth_participating INTEGER
        )
        ''')
        
        # Create participation table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS participation (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            method TEXT,
            status TEXT,
            date_started TEXT,
            date_completed TEXT,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        ''')
        
        # Create content table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            content_type TEXT,
            content_path TEXT,
            date_created TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        ''')
        
        # Create ROI tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roi_tracking (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            date TEXT,
            metric_type TEXT,
            metric_value REAL,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database setup complete at {self.db_path}")
    
    def add_project(self, project_data):
        """Add a new project to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if project already exists
        cursor.execute("SELECT id FROM projects WHERE name = ?", (project_data.get('project_name', ''),))
        existing = cursor.fetchone()
        
        # Extract categories
        categories = project_data.get('categories', [])
        categories_str = ','.join(categories) if categories else ''
        
        # Extract ROI potential
        roi_potential = project_data.get('roi_potential', {})
        roi_level = roi_potential.get('level', 'Unknown')
        roi_score = roi_potential.get('score', 0)
        
        if existing:
            # Update existing project
            cursor.execute('''
            UPDATE projects SET
                description = ?,
                category = ?,
                score = ?,
                roi_potential = ?,
                roi_score = ?,
                investment_amount = ?,
                source = ?,
                source_url = ?,
                worth_participating = ?
            WHERE id = ?
            ''', (
                project_data.get('text', '')[:500],  # Limit description length
                categories_str,
                project_data.get('score', 0),
                roi_level,
                roi_score,
                project_data.get('investment_info', 0),
                project_data.get('source', ''),
                project_data.get('url', project_data.get('message_link', '')),
                1 if project_data.get('worth_participating', False) else 0,
                existing[0]
            ))
            
            project_id = existing[0]
            logger.info(f"Updated existing project: {project_data.get('project_name', '')}")
        else:
            # Insert new project
            cursor.execute('''
            INSERT INTO projects (
                name, description, category, score, roi_potential, roi_score,
                investment_amount, participation_status, date_added, deadline,
                source, source_url, worth_participating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_data.get('project_name', 'Unknown Project'),
                project_data.get('text', '')[:500],  # Limit description length
                categories_str,
                project_data.get('score', 0),
                roi_level,
                roi_score,
                project_data.get('investment_info', 0),
                'identified',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                next(iter(project_data.get('deadlines', {}).values()), ''),
                project_data.get('source', ''),
                project_data.get('url', project_data.get('message_link', '')),
                1 if project_data.get('worth_participating', False) else 0
            ))
            
            project_id = cursor.lastrowid
            logger.info(f"Added new project: {project_data.get('project_name', '')}")
        
        conn.commit()
        
        # Add participation methods
        participation_strategies = project_data.get('participation_strategies', [])
        for strategy in participation_strategies:
            strategy_type = strategy.get('type', '')
            action = strategy.get('action', '')
            
            if strategy_type and action:
                cursor.execute('''
                INSERT INTO participation (
                    project_id, method, status, date_started
                ) VALUES (?, ?, ?, ?)
                ''', (
                    project_id,
                    f"{strategy_type}:{action}",
                    'identified',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
        
        conn.commit()
        conn.close()
        
        return project_id
    
    def add_content(self, project_id, content_type, content_path):
        """Add content for a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO content (
            project_id, content_type, content_path, date_created
        ) VALUES (?, ?, ?, ?)
        ''', (
            project_id,
            content_type,
            content_path,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added {content_type} content for project ID {project_id}")
    
    def update_participation_status(self, project_id, method, status, notes=None):
        """Update participation status for a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find participation entry
        cursor.execute('''
        SELECT id FROM participation 
        WHERE project_id = ? AND method LIKE ?
        ''', (project_id, f"%{method}%"))
        
        participation = cursor.fetchone()
        
        if participation:
            # Update existing participation
            update_fields = ['status = ?']
            update_values = [status]
            
            if status == 'completed':
                update_fields.append('date_completed = ?')
                update_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            if notes:
                update_fields.append('notes = ?')
                update_values.append(notes)
            
            update_values.append(participation[0])  # ID for WHERE clause
            
            cursor.execute(f'''
            UPDATE participation SET
                {', '.join(update_fields)}
            WHERE id = ?
            ''', update_values)
            
            # Also update project status if all participation methods are completed
            cursor.execute('''
            SELECT COUNT(*) FROM participation 
            WHERE project_id = ? AND status != 'completed'
            ''', (project_id,))
            
            incomplete_count = cursor.fetchone()[0]
            
            if incomplete_count == 0:
                cursor.execute('''
                UPDATE projects SET
                    participation_status = 'completed'
                WHERE id = ?
                ''', (project_id,))
            else:
                cursor.execute('''
                UPDATE projects SET
                    participation_status = 'in_progress'
                WHERE id = ?
                ''', (project_id,))
            
            conn.commit()
            logger.info(f"Updated participation status for project ID {project_id}, method {method} to {status}")
        else:
            logger.warning(f"No participation entry found for project ID {project_id}, method {method}")
        
        conn.close()
    
    def add_roi_metric(self, project_id, metric_type, metric_value, notes=None):
        """Add ROI tracking metric for a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO roi_tracking (
            project_id, date, metric_type, metric_value, notes
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            project_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            metric_type,
            metric_value,
            notes
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added ROI metric for project ID {project_id}: {metric_type} = {metric_value}")
    
    def get_project_by_name(self, project_name):
        """Get project by name"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects WHERE name = ?
        ''', (project_name,))
        
        project = cursor.fetchone()
        
        if project:
            # Convert to dict
            project_dict = dict(project)
            
            # Get participation methods
            cursor.execute('''
            SELECT * FROM participation WHERE project_id = ?
            ''', (project['id'],))
            
            participation = [dict(p) for p in cursor.fetchall()]
            project_dict['participation'] = participation
            
            # Get content
            cursor.execute('''
            SELECT * FROM content WHERE project_id = ?
            ''', (project['id'],))
            
            content = [dict(c) for c in cursor.fetchall()]
            project_dict['content'] = content
            
            # Get ROI metrics
            cursor.execute('''
            SELECT * FROM roi_tracking WHERE project_id = ?
            ''', (project['id'],))
            
            roi_metrics = [dict(r) for r in cursor.fetchall()]
            project_dict['roi_metrics'] = roi_metrics
            
            conn.close()
            return project_dict
        
        conn.close()
        return None
    
    def get_project_by_id(self, project_id):
        """Get project by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects WHERE id = ?
        ''', (project_id,))
        
        project = cursor.fetchone()
        
        if project:
            # Convert to dict
            project_dict = dict(project)
            
            # Get participation methods
            cursor.execute('''
            SELECT * FROM participation WHERE project_id = ?
            ''', (project['id'],))
            
            participation = [dict(p) for p in cursor.fetchall()]
            project_dict['participation'] = participation
            
            # Get content
            cursor.execute('''
            SELECT * FROM content WHERE project_id = ?
            ''', (project['id'],))
            
            content = [dict(c) for c in cursor.fetchall()]
            project_dict['content'] = content
            
            # Get ROI metrics
            cursor.execute('''
            SELECT * FROM roi_tracking WHERE project_id = ?
            ''', (project['id'],))
            
            roi_metrics = [dict(r) for r in cursor.fetchall()]
            project_dict['roi_metrics'] = roi_metrics
            
            conn.close()
            return project_dict
        
        conn.close()
        return None
    
    def get_all_projects(self):
        """Get all projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects ORDER BY roi_score DESC
        ''')
        
        projects = [dict(p) for p in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def get_projects_by_category(self, category):
        """Get projects by category"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects WHERE category LIKE ? ORDER BY roi_score DESC
        ''', (f'%{category}%',))
        
        projects = [dict(p) for p in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def get_projects_by_status(self, status):
        """Get projects by participation status"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects WHERE participation_status = ? ORDER BY roi_score DESC
        ''', (status,))
        
        projects = [dict(p) for p in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def get_high_roi_projects(self, min_score=70):
        """Get high ROI potential projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM projects WHERE roi_score >= ? ORDER BY roi_score DESC
        ''', (min_score,))
        
        projects = [dict(p) for p in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def get_projects_with_upcoming_deadlines(self, days=7):
        """Get projects with upcoming deadlines"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # This is a simplified approach - in a real system, you'd want to parse dates properly
        cursor.execute('''
        SELECT * FROM projects 
        WHERE deadline != '' AND participation_status != 'completed'
        ORDER BY deadline ASC
        ''')
        
        projects = [dict(p) for p in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def generate_project_report(self, project_id):
        """Generate a detailed report for a project"""
        project = self.get_project_by_id(project_id)
        
        if not project:
            return f"No project found with ID {project_id}"
        
        report = f"# {project['name']} Project Report\n\n"
        
        # Basic information
        report += "## Overview\n"
        report += f"- **Category**: {project['category']}\n"
        report += f"- **ROI Potential**: {project['roi_potential']} ({project['roi_score']:.1f})\n"
        report += f"- **Worth Participating**: {'Yes' if project['worth_participating'] else 'No'}\n"
        report += f"- **Current Status**: {project['participation_status']}\n"
        
        if project['investment_amount']:
            report += f"- **Investment Amount**: ${project['investment_amount']:,.0f}\n"
        
        if project['deadline']:
            report += f"- **Deadline**: {project['deadline']}\n"
        
        report += f"- **Source**: {project['source']}\n"
        if project['source_url']:
            report += f"- **Source URL**: {project['source_url']}\n"
        
        report += "\n"
        
        # Description
        if project['description']:
            report += "## Description\n"
            report += f"{project['description']}\n\n"
        
        # Participation methods
        if project.get('participation'):
            report += "## Participation Methods\n"
            for method in project['participation']:
                method_parts = method['method'].split(':')
                method_type = method_parts[0] if len(method_parts) > 0 else 'Unknown'
                method_action = method_parts[1] if len(method_parts) > 1 else 'Unknown'
                
                report += f"- **{method_type.title()}**: {method_action.replace('_', ' ').title()}\n"
                report += f"  - Status: {method['status']}\n"
                
                if method['date_started']:
                    report += f"  - Started: {method['date_started']}\n"
                
                if method['date_completed']:
                    report += f"  - Completed: {method['date_completed']}\n"
                
                if method['notes']:
                    report += f"  - Notes: {method['notes']}\n"
            
            report += "\n"
        
        # Content
        if project.get('content'):
            report += "## Generated Content\n"
            for content in project['content']:
                report += f"- **{content['content_type']}**: {content['content_path']}\n"
                report += f"  - Created: {content['date_created']}\n"
            
            report += "\n"
        
        # ROI metrics
        if project.get('roi_metrics'):
            report += "## ROI Tracking\n"
            for metric in project['roi_metrics']:
                report += f"- **{metric['metric_type']}**: {metric['metric_value']}\n"
                report += f"  - Date: {metric['date']}\n"
                
                if metric['notes']:
                    report += f"  - Notes: {metric['notes']}\n"
            
            report += "\n"
        
        return report
    
    def generate_summary_report(self):
        """Generate a summary report of all projects"""
        projects = self.get_all_projects()
        
        if not projects:
            return "No projects found in the database."
        
        report = "# Project Summary Report\n\n"
        
        # Count by category
        categories = {}
        for project in projects:
            for category in project['category'].split(','):
                if category:
                    categories[category] = categories.get(category, 0) + 1
        
        report += "## Projects by Category\n"
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report += f"- {category}: {count}\n"
        
        report += "\n"
        
        # Count by status
        statuses = {}
        for project in projects:
            status = project['participation_status'] or 'unknown'
            statuses[status] = statuses.get(status, 0) + 1
        
        report += "## Projects by Status\n"
        for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
            report += f"- {status}: {count}\n"
        
        report += "\n"
        
        # Top projects by ROI potential
        report += "## Top Projects by ROI Potential\n"
        top_projects = sorted(projects, key=lambda x: x['roi_score'] or 0, reverse=True)[:10]
        for i, project in enumerate(top_projects, 1):
            report += f"{i}. **{project['name']}** - {project['roi_potential']} ({project['roi_score']:.1f})\n"
        
        report += "\n"
        
        # Projects with upcoming deadlines
        upcoming_projects = self.get_projects_with_upcoming_deadlines()
        if upcoming_projects:
            report += "## Projects with Upcoming Deadlines\n"
            for project in upcoming_projects[:10]:
                report += f"- **{project['name']}** - Deadline: {project['deadline']}\n"
        
        report += "\n"
        
        # Projects by worth participating
        worth_participating = [p for p in projects if p['worth_participating']]
        report += f"## Projects Worth Participating: {len(worth_participating)}/{len(projects)}\n"
        
        return report
    
    def export_to_csv(self, filename='projects_export.csv'):
        """Export projects to CSV"""
        projects = self.get_all_projects()
        
        if not projects:
            logger.warning("No projects to export")
            return False
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            # Get field names from first project
            fieldnames = projects[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write rows
            for project in projects:
                writer.writerow(project)
        
        logger.info(f"Exported {len(projects)} projects to {filename}")
        return True
    
    def import_from_csv(self, filename):
        """Import projects from CSV"""
        if not os.path.exists(filename):
            logger.error(f"File not found: {filename}")
            return False
        
        try:
            projects = []
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    projects.append(row)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for row in projects:
                # Check if project already exists
                cursor.execute("SELECT id FROM projects WHERE name = ?", (row['name'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing project
                    cursor.execute('''
                    UPDATE projects SET
                        description = ?,
                        category = ?,
                        score = ?,
                        roi_potential = ?,
                        roi_score = ?,
                        investment_amount = ?,
                        participation_status = ?,
                        deadline = ?,
                        source = ?,
                        source_url = ?,
                        worth_participating = ?
                    WHERE id = ?
                    ''', (
                        row.get('description', ''),
                        row.get('category', ''),
                        float(row.get('score', 0)),
                        row.get('roi_potential', 'Unknown'),
                        float(row.get('roi_score', 0)),
                        float(row.get('investment_amount', 0)),
                        row.get('participation_status', 'identified'),
                        row.get('deadline', ''),
                        row.get('source', ''),
                        row.get('source_url', ''),
                        int(row.get('worth_participating', 0)),
                        existing[0]
                    ))
                else:
                    # Insert new project
                    cursor.execute('''
                    INSERT INTO projects (
                        name, description, category, score, roi_potential, roi_score,
                        investment_amount, participation_status, date_added, deadline,
                        source, source_url, worth_participating
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['name'],
                        row.get('description', ''),
                        row.get('category', ''),
                        float(row.get('score', 0)),
                        row.get('roi_potential', 'Unknown'),
                        float(row.get('roi_score', 0)),
                        float(row.get('investment_amount', 0)),
                        row.get('participation_status', 'identified'),
                        row.get('date_added', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        row.get('deadline', ''),
                        row.get('source', ''),
                        row.get('source_url', ''),
                        int(row.get('worth_participating', 0))
                    ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Imported {len(projects)} projects from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing from CSV: {str(e)}")
            return False
    
    def generate_roi_chart(self, output_dir='charts'):
        """Generate ROI potential distribution chart using Plotly"""
        projects = self.get_all_projects()
        
        if not projects:
            logger.warning("No projects to generate chart")
            return False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Count ROI levels
        roi_levels = {}
        for project in projects:
            level = project['roi_potential'] or 'Unknown'
            roi_levels[level] = roi_levels.get(level, 0) + 1
        
        # Create pie chart with Plotly
        labels = list(roi_levels.keys())
        values = list(roi_levels.values())
        
        fig = px.pie(
            names=labels, 
            values=values, 
            title='Projects by ROI Potential',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        # Save chart
        chart_path = os.path.join(output_dir, 'roi_distribution.html')
        fig.write_html(chart_path)
        
        logger.info(f"Generated ROI chart at {chart_path}")
        
        # Create category distribution chart
        categories = {}
        for project in projects:
            for category in project['category'].split(','):
                if category:
                    categories[category] = categories.get(category, 0) + 1
        
        # Sort by count
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 10 categories
        top_categories = sorted_categories[:10]
        
        # Create bar chart with Plotly
        x = [c[0] for c in top_categories]
        y = [c[1] for c in top_categories]
        
        fig = px.bar(
            x=x, 
            y=y, 
            title='Top Project Categories',
            labels={'x': 'Category', 'y': 'Number of Projects'},
            color_discrete_sequence=[px.colors.qualitative.Pastel[0]]
        )
        
        # Save chart
        chart_path = os.path.join(output_dir, 'category_distribution.html')
        fig.write_html(chart_path)
        
        logger.info(f"Generated category chart at {chart_path}")
        
        return True
    
    def process_analyzed_opportunities(self, opportunities, content_dir='project_content'):
        """Process a list of analyzed opportunities and add them to the database"""
        for opportunity in opportunities:
            # Add project to database
            project_id = self.add_project(opportunity)
            
            # Check if content directory exists for this project
            project_name = opportunity.get('project_name', 'Unknown Project')
            project_dir = os.path.join(content_dir, project_name.replace(' ', '_'))
            
            if os.path.exists(project_dir):
                # Add content to database
                for content_type in ['social_post', 'project_guide', 'project_update']:
                    content_file = os.path.join(project_dir, f"{content_type}.md")
                    if os.path.exists(content_file):
                        self.add_content(project_id, content_type, content_file)
                
                # Add automation scripts to database
                for script_type in ['social_engagement', 'node_setup']:
                    script_ext = 'py' if script_type == 'social_engagement' else 'sh'
                    script_file = os.path.join(project_dir, f"{script_type}_script.{script_ext}")
                    if os.path.exists(script_file):
                        self.add_content(project_id, f"{script_type}_script", script_file)
        
        logger.info(f"Processed {len(opportunities)} opportunities")

# Example usage
if __name__ == "__main__":
    tracker = ProjectTracker()
    
    # Sample project data
    sample_project = {
        'project_name': 'Quantum Chain',
        'categories': ['testnet', 'layer2'],
        'text': "Join the Quantum Chain testnet and earn rewards! $10M raised from a16z and Binance Labs. Mainnet launch in June 2025.",
        'score': 85,
        'roi_potential': {'level': 'High', 'score': 85},
        'participation_strategies': [
            {'type': 'technical', 'action': 'node_setup', 'difficulty': 'high'},
            {'type': 'social', 'action': 'social_engagement', 'difficulty': 'low'}
        ],
        'requirements': {
            'cpu': '4',
            'ram': '8GB',
            'storage': '100GB'
        },
        'deadlines': {'submission': 'April 15, 2025'},
        'investment_info': 10000000,
        'source': 'twitter',
        'url': 'https://twitter.com/QuantumChain/status/1234567890',
        'worth_participating': True
    }
    
    # Add project
    project_id = tracker.add_project(sample_project)
    
    # Add content
    tracker.add_content(project_id, 'social_post', 'project_content/Quantum_Chain/social_post.md')
    tracker.add_content(project_id, 'project_guide', 'project_content/Quantum_Chain/project_guide.md')
    
    # Update participation status
    tracker.update_participation_status(project_id, 'social_engagement', 'completed', 'Completed social engagement tasks')
    
    # Add ROI metric
    tracker.add_roi_metric(project_id, 'token_allocation', 5000, 'Estimated token allocation based on participation')
    
    # Generate report
    report = tracker.generate_project_report(project_id)
    print(report)
    
    # Generate summary report
    summary = tracker.generate_summary_report()
    print(summary)
