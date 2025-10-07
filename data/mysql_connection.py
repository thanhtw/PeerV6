"""
MySQL Connection Manager for Java Peer Review Training System.
FIXED: Robust connection handling with fallback mechanisms
"""

import mysql.connector
from mysql.connector import Error, pooling
import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLConnection:
    """
    MySQL Connection Manager with connection pooling and fallback mechanisms.
    """
    
    _instance = None
    _pool = None
    _use_pool = True  # Can be disabled if pooling fails
    
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
        self.use_ssl = os.getenv("MYSQL_USE_SSL", "false").lower() == "true"
        
        # Try to initialize connection pool, but don't fail if it doesn't work
        self._try_init_pool()
        self._initialized = True
        
        logger.info(f"MySQLConnection initialized (Pool: {'enabled' if self._use_pool else 'disabled'})")
    
    def _try_init_pool(self):
        """Try to initialize the connection pool, disable if it fails."""
        try:
            pool_config = {
                'pool_name': 'java_review_pool',
                'pool_size': 20,  # Increased from 5
                'pool_reset_session': True,
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True,
                'connect_timeout': 10,
            }
            
            if not self.use_ssl:
                pool_config['ssl_disabled'] = True
            
            self._pool = pooling.MySQLConnectionPool(**pool_config)
            self._use_pool = True
            logger.info(f"✅ Connection pool created (size: 20)")
            
        except Error as e:
            logger.warning(f"⚠️ Could not create connection pool: {e}")
            logger.warning("⚠️ Falling back to direct connections")
            self._pool = None
            self._use_pool = False
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error creating pool: {e}")
            self._pool = None
            self._use_pool = False
    
    def get_connection(self, retry=3):
        """
        Get a database connection with retry logic.
        
        Args:
            retry: Number of retry attempts
            
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection
        """
        last_error = None
        
        for attempt in range(retry):
            try:
                # Try pool first if available
                if self._use_pool and self._pool:
                    try:
                        connection = self._pool.get_connection()
                        if connection and connection.is_connected():
                            return connection
                        else:
                            if connection:
                                connection.close()
                    except pooling.PoolError as e:
                        logger.warning(f"Pool error: {e}, switching to direct connection")
                        self._use_pool = False
                
                # Fallback to direct connection
                connection = self._create_direct_connection()
                if connection and connection.is_connected():
                    return connection
                    
            except Error as e:
                last_error = e
                logger.error(f"Connection attempt {attempt + 1}/{retry} failed: {e}")
                if attempt < retry - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}/{retry}: {e}")
                if attempt < retry - 1:
                    time.sleep(0.5 * (attempt + 1))
        
        logger.error(f"Failed to get connection after {retry} attempts. Last error: {last_error}")
        return None
    
    def _create_direct_connection(self):
        """Create a direct connection without pooling."""
        try:
            connection_config = {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database,
                'autocommit': True,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'connect_timeout': 10,
            }
            
            if not self.use_ssl:
                connection_config['ssl_disabled'] = True
            
            connection = mysql.connector.connect(**connection_config)
            return connection
            
        except Error as e:
            logger.error(f"Error creating direct connection: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating connection: {e}")
            return None
    
    @contextmanager
    def get_cursor(self, dictionary=True):
        """
        Context manager for getting a cursor.
        Ensures proper cleanup of connection and cursor.
        
        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                results = cursor.fetchall()
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            if not connection:
                raise Error("Could not establish database connection")
            
            cursor = connection.cursor(dictionary=dictionary, buffered=True)
            yield cursor
            connection.commit()
            
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise e
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()
                except:
                    pass
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False) -> Optional[Any]:
        """
        Execute a SQL query with proper resource management.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Whether to fetch only one result
            
        Returns:
            Query results or affected rows count
        """
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Handle different query types
                if query.strip().upper().startswith('SELECT'):
                    if fetch_one:
                        return cursor.fetchone()
                    else:
                        return cursor.fetchall()
                else:
                    # For INSERT, UPDATE, DELETE
                    return cursor.rowcount
                    
        except Error as e:
            logger.error(f"Database error: {e}")
            logger.error(f"Query: {query[:200]}...")
            return None
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            return None
    
    def execute_many(self, query: str, data: List[tuple]) -> Optional[int]:
        """
        Execute multiple queries with the same structure.
        
        Args:
            query: SQL query template
            data: List of parameter tuples
            
        Returns:
            Number of affected rows or None on error
        """
        try:
            with self.get_cursor(dictionary=False) as cursor:
                cursor.executemany(query, data)
                return cursor.rowcount
                
        except Error as e:
            logger.error(f"Error executing batch query: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in execute_many: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the database connection with detailed diagnostics.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("=" * 50)
            logger.info("Testing database connection...")
            logger.info(f"Host: {self.host}:{self.port}")
            logger.info(f"Database: {self.database}")
            logger.info(f"User: {self.user}")
            logger.info(f"Pool enabled: {self._use_pool}")
            
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()
                
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                
                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                max_conn = cursor.fetchone()
                
                logger.info("✅ Connection successful!")
                logger.info(f"   Database: {db_name[0] if db_name else 'Unknown'}")
                logger.info(f"   MySQL Version: {version[0] if version else 'Unknown'}")
                logger.info(f"   Max Connections: {max_conn[1] if max_conn else 'Unknown'}")
                logger.info("=" * 50)
                
                return True
                
        except Error as e:
            logger.error("=" * 50)
            logger.error(f"❌ Connection test failed!")
            logger.error(f"   Error: {e}")
            logger.error(f"   Error Code: {e.errno if hasattr(e, 'errno') else 'N/A'}")
            logger.error("=" * 50)
            return False
        except Exception as e:
            logger.error("=" * 50)
            logger.error(f"❌ Unexpected error: {e}")
            logger.error("=" * 50)
            return False
    
    def test_connection_only(self) -> bool:
        """
        Quick connection test without verbose logging.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
        except:
            return False
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get the current status of the connection pool."""
        if not self._use_pool:
            return {"status": "disabled", "mode": "direct_connections"}
        
        if not self._pool:
            return {"status": "not_initialized"}
        
        try:
            return {
                "status": "active",
                "pool_name": self._pool.pool_name,
                "pool_size": self._pool._pool_size,
                "mode": "pooled"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close_all_connections(self):
        """Close all connections."""
        try:
            if self._pool:
                self._pool = None
                logger.info("Connection pool closed")
            self._use_pool = False
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close_all_connections()