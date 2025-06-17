# db/mysql_connection.py
import mysql.connector
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLConnection:
    """
    MySQL database connection manager for the Java Peer Review Training System.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(MySQLConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the database connection."""
        if self._initialized:
            return
            
        # Get database configuration from environment variables
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_user = os.getenv("DB_USER", "java_review_user")
        self.db_password = os.getenv("DB_PASSWORD", "Thomas123!")
        self.db_name = os.getenv("DB_NAME", "java_review_db")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        
        # Initialize connection to None
        self.connection = None
        self._initialized = True
        
        # Try to initialize database safely
        self._safe_initialize_database()
    
    def _get_connection(self):
        """Get a database connection with improved error handling."""
        try:
            if self.connection is None or not self.connection.is_connected():
                # Log connection attempt
                logger.debug(f"Connecting to MySQL: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}")
                
                # Add authentication_plugin parameter for compatibility
                self.connection = mysql.connector.connect(
                    host=self.db_host,
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name,
                    port=self.db_port,
                    auth_plugin='mysql_native_password',  # Try alternative auth method
                    use_pure=True,  # Use pure Python implementation for better compatibility
                    charset='utf8mb4',
                    collation='utf8mb4_unicode_ci'
                )
                logger.debug("Connected to MySQL successfully")
            return self.connection
        except mysql.connector.Error as e:
            logger.error(f"Error connecting to MySQL: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _safe_initialize_database(self):
        """Safely initialize database without failing if tables don't exist."""
        try:
            # Check if we can connect to the database
            connection = self._get_connection()
            if connection and connection.is_connected():
                logger.debug("Database connection verified successfully")
            else:
                logger.warning("Database connection could not be established")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {str(e)}")

    def test_admin_connection(self):
        """Test connection with admin credentials for setup."""
        try:
            admin_user = os.getenv("ADMIN_DB_USER", "root")
            admin_password = os.getenv("ADMIN_DB_PASSWORD", self.db_password)
            
            connection = mysql.connector.connect(
                host=self.db_host,
                user=admin_user,
                password=admin_password,
                port=self.db_port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            if connection.is_connected():
                connection.close()
                return True
            return False
            
        except mysql.connector.Error:
            return False
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False):
        """
        Execute a query and return the results.
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            connection = self._get_connection()
            if not connection:
                logger.error("Failed to get database connection")
                time.sleep(1)  # Wait before retry
                retry_count += 1
                continue
                
            try:
                cursor = connection.cursor(dictionary=True)
                
                # Log query with parameters
                if params:
                    param_str = str(params)
                    logger.debug(f"Executing query: {query} with params: {param_str}")
                else:
                    logger.debug(f"Executing query: {query}")
                
                cursor.execute(query, params or ())
                
                if query.strip().upper().startswith(("SELECT", "SHOW")):
                    if fetch_one:
                        result = cursor.fetchone()
                    else:
                        result = cursor.fetchall()
                    cursor.close()
                    return result
                else:
                    connection.commit()
                    affected_rows = cursor.rowcount
                    cursor.close()
                    logger.debug(f"Query executed successfully. Affected rows: {affected_rows}")
                    return affected_rows
            except mysql.connector.Error as e:
                logger.error(f"Error executing query: {str(e)}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                logger.error(traceback.format_exc())
                
                # Check for connection-related errors to retry
                should_retry = False
                if "2006" in str(e) or "2013" in str(e):  # Common MySQL connection lost error codes
                    logger.debug("Connection lost, attempting to reconnect...")
                    self.connection = None  # Force reconnection
                    should_retry = True
                
                if should_retry and retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    return None
            except Exception as e:
                logger.error(f"Unexpected error executing query: {str(e)}")
                #logger.error(traceback.format_exc())
                return None
    
    def test_connection_only(self):
        """Test database connection without creating tables."""
        try:
            connection = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                port=self.db_port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            if connection.is_connected():
                connection.close()
                return True
            return False
            
        except mysql.connector.Error:
            return False
    
    def get_admin_connection(self):
        """Get connection using admin credentials for setup purposes."""
        try:
            admin_user = os.getenv("ADMIN_DB_USER", "root")
            admin_password = os.getenv("ADMIN_DB_PASSWORD", self.db_password)
            
            connection = mysql.connector.connect(
                host=self.db_host,
                user=admin_user,
                password=admin_password,
                database=self.db_name,
                port=self.db_port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            return connection
            
        except mysql.connector.Error as e:
            logger.error(f"Admin connection failed: {str(e)}")
            return None