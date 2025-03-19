import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger("Database")

class DatabaseManager:
    """Database management utility for CryptoFarm"""
    
    def __init__(self, db_path='database/cryptofarm.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Make sure the database file exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found at {self.db_path}. Run setup_database.py first.")
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            conn.commit()
            conn.close()
            
            return results
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            return []
    
    def execute_many(self, query, params_list):
        """Execute multiple queries with different parameters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.executemany(query, params_list)
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Database error in executemany: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"First params: {params_list[0] if params_list else None}")
            return False
    
    def insert(self, table, data):
        """Insert data into a table and return the inserted ID"""
        try:
            # Remove None values
            clean_data = {k: v for k, v in data.items() if v is not None}
            
            # Build the query
            columns = ', '.join(clean_data.keys())
            placeholders = ', '.join(['?' for _ in clean_data])
            values = list(clean_data.values())
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            
            # Get the inserted ID
            inserted_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            return inserted_id
        except Exception as e:
            logger.error(f"Insert error for table {table}: {str(e)}")
            logger.error(f"Data: {data}")
            return None
    
    def update(self, table, data, condition):
        """Update data in a table with a condition"""
        try:
            # Remove None values from data
            clean_data = {k: v for k, v in data.items() if v is not None}
            
            # Build the SET part
            set_clause = ', '.join([f"{k} = ?" for k in clean_data.keys()])
            set_values = list(clean_data.values())
            
            # Build the WHERE part
            where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
            where_values = list(condition.values())
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            values = set_values + where_values
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            
            # Get number of rows affected
            row_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return row_count
        except Exception as e:
            logger.error(f"Update error for table {table}: {str(e)}")
            logger.error(f"Data: {data}")
            logger.error(f"Condition: {condition}")
            return 0
    
    def delete(self, table, condition):
        """Delete data from a table with a condition"""
        try:
            # Build the WHERE part
            where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
            where_values = list(condition.values())
            
            query = f"DELETE FROM {table} WHERE {where_clause}"
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, where_values)
            
            # Get number of rows affected
            row_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return row_count
        except Exception as e:
            logger.error(f"Delete error for table {table}: {str(e)}")
            logger.error(f"Condition: {condition}")
            return 0
    
    def select(self, table, columns="*", condition=None, order_by=None, limit=None):
        """Select data from a table with optional condition, ordering and limit"""
        try:
            # Build the SELECT part
            if isinstance(columns, list):
                columns_str = ", ".join(columns)
            else:
                columns_str = columns
                
            query = f"SELECT {columns_str} FROM {table}"
            
            values = []
            
            # Build the WHERE part if condition is provided
            if condition:
                where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
                where_values = list(condition.values())
                query += f" WHERE {where_clause}"
                values = where_values
            
            # Add ORDER BY if provided
            if order_by:
                query += f" ORDER BY {order_by}"
            
            # Add LIMIT if provided
            if limit:
                query += f" LIMIT {limit}"
            
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
            
            # Fetch results and convert to dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            conn.close()
            
            return results
        except Exception as e:
            logger.error(f"Select error for table {table}: {str(e)}")
            logger.error(f"Query: {query if 'query' in locals() else 'Query not built'}")
            if 'values' in locals() and values:
                logger.error(f"Values: {values}")
            return []
    
    def backup_database(self, backup_dir='database/backups'):
        """Create a backup of the database file"""
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"cryptofarm_backup_{timestamp}.db")
            
            # Connect to the source database
            source_conn = self.get_connection()
            
            # Create a new database for backup
            backup_conn = sqlite3.connect(backup_path)
            
            # Backup the database
            source_conn.backup(backup_conn)
            
            # Close connections
            source_conn.close()
            backup_conn.close()
            
            logger.info(f"Database backup created at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            return None


# Create a default database manager
db_manager = DatabaseManager()

# Helper functions for common database operations

def add_project(project_data):
    """Add a new project to the database"""
    if 'date_added' not in project_data:
        project_data['date_added'] = datetime.now().isoformat()
    
    return db_manager.insert('projects', project_data)

def update_project(project_id, project_data):
    """Update a project in the database"""
    return db_manager.update('projects', project_data, {'id': project_id})

def get_project(project_id):
    """Get a project by ID"""
    results = db_manager.select('projects', condition={'id': project_id})
    return results[0] if results else None

def get_project_by_name(project_name):
    """Get a project by name"""
    results = db_manager.select('projects', condition={'name': project_name})
    return results[0] if results else None

def get_all_projects(active_only=True):
    """Get all projects"""
    if active_only:
        return db_manager.select('projects', condition={'is_active': 1})
    return db_manager.select('projects')

def add_data_source(source_data):
    """Add a new data source"""
    return db_manager.insert('data_sources', source_data)

def get_data_sources(source_type=None):
    """Get all data sources or filter by type"""
    if source_type:
        return db_manager.select('data_sources', condition={'source_type': source_type, 'is_active': 1})
    return db_manager.select('data_sources', condition={'is_active': 1})

def add_raw_data(source_id, content, metadata, content_hash=None):
    """Add raw data from a source"""
    data = {
        'source_id': source_id,
        'content': content,
        'content_hash': content_hash,
        'metadata': json.dumps(metadata) if isinstance(metadata, dict) else metadata,
        'timestamp': datetime.now().isoformat(),
        'processed': 0
    }
    return db_manager.insert('raw_data', data)

def mark_data_processed(raw_data_id):
    """Mark raw data as processed"""
    return db_manager.update('raw_data', {'processed': 1}, {'id': raw_data_id})

def add_analyzed_data(raw_data_id, project_id, categories, priority_score, context):
    """Add analyzed data results"""
    data = {
        'raw_data_id': raw_data_id,
        'project_id': project_id,
        'categories': json.dumps(categories) if isinstance(categories, list) else categories,
        'priority_score': priority_score,
        'context': json.dumps(context) if isinstance(context, list) else context,
        'analysis_timestamp': datetime.now().isoformat()
    }
    return db_manager.insert('analyzed_data', data)

def add_task(project_id, task_type, task_description, scheduled_for=None):
    """Add an automated task"""
    data = {
        'project_id': project_id,
        'task_type': task_type,
        'task_description': task_description,
        'status': 'scheduled',
        'created_at': datetime.now().isoformat(),
        'scheduled_for': scheduled_for or datetime.now().isoformat()
    }
    return db_manager.insert('automated_tasks', data)

def update_task_status(task_id, status, result=None):
    """Update task status"""
    data = {
        'status': status,
        'result': result
    }
    
    if status in ['completed', 'failed']:
        data['completed_at'] = datetime.now().isoformat()
        
    return db_manager.update('automated_tasks', data, {'id': task_id})

def add_alert(project_id, alert_type, alert_message, priority='medium'):
    """Add an alert"""
    data = {
        'project_id': project_id,
        'alert_type': alert_type,
        'alert_message': alert_message,
        'priority': priority,
        'created_at': datetime.now().isoformat(),
        'is_read': 0
    }
    return db_manager.insert('alerts', data)

def get_unread_alerts():
    """Get all unread alerts"""
    return db_manager.select('alerts', condition={'is_read': 0}, order_by='created_at DESC')

def mark_alert_read(alert_id):
    """Mark an alert as read"""
    return db_manager.update('alerts', {'is_read': 1}, {'id': alert_id}) 