"""
MySQL Connection Manager for Java Peer Review Training System.
FIXED: SSL connection error handling
"""

import mysql.connector
from mysql.connector import Error
import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLConnection:
    """
    MySQL Connection Manager with improved error handling and connection pooling.
    FIXED: SSL connection issues
    """
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(MySQLConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the MySQL connection manager."""
        if self._initialized:
            return
            
        load_dotenv(override=True)
        
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DATABASE", "java_review_system")
        
        # FIXED: SSL configuration - disable SSL to avoid protocol errors
        self.use_ssl = os.getenv("MYSQL_USE_SSL", "false").lower() == "true"
        
        self._initialized = True
        logger.debug("MySQLConnection initialized")
    
    def get_connection(self):
        """
        Get MySQL connection with improved error handling and SSL fix.
        
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection
        """
        try:
            # Check if connection exists and is alive
            if self._connection and self._connection.is_connected():
                return self._connection
            
            # Create new connection with SSL disabled to fix protocol error
            connection_config = {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database,
                'autocommit': True,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'connection_timeout': 10,
                'pool_reset_session': True
            }
            
            # FIXED: Disable SSL to prevent protocol errors
            if not self.use_ssl:
                connection_config['ssl_disabled'] = True
            
            logger.debug(f"Connecting to MySQL at {self.host}:{self.port}")
            self._connection = mysql.connector.connect(**connection_config)
            
            if self._connection.is_connected():
                db_info = self._connection.get_server_info()
                logger.debug(f"Successfully connected to MySQL Server version {db_info}")
                return self._connection
            else:
                logger.error("Failed to connect to MySQL")
                return None
                
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            self._connection = None
            return None
        except Exception as e:
            logger.error(f"Unexpected error connecting to MySQL: {e}")
            self._connection = None
            return None
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False) -> Optional[Any]:
        """
        Execute a SQL query with improved error handling.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Whether to fetch only one result
            
        Returns:
            Query results or affected rows count
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            
            if not connection:
                logger.error("No database connection available")
                return None
            
            cursor = connection.cursor(dictionary=True, buffered=True)
            
            # Execute query with or without parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Handle different query types
            if query.strip().upper().startswith('SELECT'):
                if fetch_one:
                    result = cursor.fetchone()
                    return result
                else:
                    results = cursor.fetchall()
                    return results
            else:
                # For INSERT, UPDATE, DELETE
                connection.commit()
                return cursor.rowcount
                
        except Error as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            if connection:
                connection.rollback()
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if connection:
                connection.rollback()
            return None
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
    
    def execute_many(self, query: str, data: List[tuple]) -> Optional[int]:
        """
        Execute multiple queries with the same structure.
        
        Args:
            query: SQL query template
            data: List of parameter tuples
            
        Returns:
            Number of affected rows or None on error
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            
            if not connection:
                logger.error("No database connection available")
                return None
            
            cursor = connection.cursor(buffered=True)
            cursor.executemany(query, data)
            connection.commit()
            
            return cursor.rowcount
            
        except Error as e:
            logger.error(f"Error executing batch query: {e}")
            if connection:
                connection.rollback()
            return None
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
    
    def close_connection(self):
        """Close the database connection."""
        if self._connection and self._connection.is_connected():
            try:
                self._connection.close()
                logger.debug("MySQL connection closed")
            except Error as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._connection = None
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            connection = self.get_connection()
            
            if connection and connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
                logger.info("✅ Database connection test successful")
                return True
            else:
                logger.error("❌ Database connection test failed")
                return False
                
        except Error as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_connection()