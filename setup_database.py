"""
Main Database Setup Script for Java Peer Review Training System.

This script orchestrates the complete database setup process:
1. Creates database schema and tables
2. Automatically imports data from SQL files
3. Verifies the complete setup

Run this script to set up the entire database automatically.
"""
import mysql.connector
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Add project root to path
sys.path.append(str(Path(__file__).parent))
from data.mysql_connection import MySQLConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    """Handle database setup and configuration."""
    
    def __init__(self):
        """Initialize database setup with configuration."""
        # Get database configuration from environment variables with defaults
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_user = os.getenv("DB_USER", "root")  # Default to root for setup
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_name = os.getenv("DB_NAME", "java_review_db")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        
        # Application user credentials
        self.app_user = os.getenv("APP_DB_USER", "java_review_user")
        self.app_password = os.getenv("APP_DB_PASSWORD", "Thomas123!")
        
        logger.debug(f"Database setup initialized:")
        logger.debug(f"  Host: {self.db_host}:{self.db_port}")
        logger.debug(f"  Database: {self.db_name}")
        logger.debug(f"  App User: {self.app_user}")

    def test_connection(self):
        """Test database connection without specifying database."""
        try:
            logger.debug("Testing database connection...")
            
            connection = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            if connection.is_connected():
                db_info = connection.server_info
                logger.debug(f"Successfully connected to MySQL Server version {db_info}")
                cursor = connection.cursor()
                cursor.execute("SELECT DATABASE();")
                current_db = cursor.fetchone()
                logger.debug(f"Current database: {current_db}")
                cursor.close()
                connection.close()
                return True
            else:
                logger.error("Failed to connect to database")
                return False
                
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            logger.error(f"Error code: {e.errno}")
            logger.error(f"SQL state: {e.sqlstate}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def create_database(self):
        """Create the database if it doesn't exist."""
        try:
            logger.debug(f"Creating database '{self.db_name}' if it doesn't exist...")
            
            connection = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            cursor = connection.cursor()
            
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.debug(f"Database '{self.db_name}' created or already exists")
            
            # Switch to the database
            cursor.execute(f"USE `{self.db_name}`")
            logger.debug(f"Switched to database '{self.db_name}'")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating database: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating database: {str(e)}")
            return False
    
    def create_application_user(self):
        """Create application user with proper permissions."""
        try:
            logger.debug(f"Creating application user '{self.app_user}'...")
            
            connection = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port,
                database=self.db_name,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            
            cursor = connection.cursor()
            
            # Create user if not exists
            try:
                cursor.execute(f"CREATE USER IF NOT EXISTS '{self.app_user}'@'%' IDENTIFIED BY '{self.app_password}'")
                logger.debug(f"User '{self.app_user}' created or already exists")
            except mysql.connector.Error as e:
                if e.errno == 1396:  # User already exists
                    logger.debug(f"User '{self.app_user}' already exists")
                else:
                    raise e
            
            # Grant permissions
            cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON `{self.db_name}`.* TO '{self.app_user}'@'%'")
            cursor.execute("FLUSH PRIVILEGES")
            
            logger.debug(f"Permissions granted to user '{self.app_user}'")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating application user: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}")
            return False

    def execute_sql_file_automated(self, db, file_path, description):
        """Execute a SQL file with improved automation and error handling."""
        try:
            logger.debug(f"Executing {description}: {file_path.name}")
            
            if not file_path.exists():
                logger.error(f"SQL file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # Split SQL content into individual statements
            statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('--') or line.startswith('/*'):
                    continue
                
                # Handle multi-line statements
                current_statement += line + " "
                
                # Check if statement is complete (ends with semicolon)
                if line.endswith(';'):
                    statement = current_statement.strip()
                    if len(statement) > 10:  # Skip very short statements
                        statements.append(statement)
                    current_statement = ""
            
            logger.debug(f"Found {len(statements)} SQL statements to execute")
            
            success_count = 0
            error_count = 0
            
            for i, statement in enumerate(statements, 1):
                try:
                    # Execute the statement
                    result = db.execute_query(statement)
                    success_count += 1
                    
                    # Show progress for large files
                    if i % 10 == 0 or i == len(statements):
                        logger.debug(f"Processed {i}/{len(statements)} statements")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    # Ignore certain expected errors
                    if any(ignore_phrase in error_msg for ignore_phrase in [
                        "duplicate entry", "already exists", "table doesn't exist"
                    ]):
                        logger.debug(f"Statement {i}: {str(e)[:100]}... (ignored)")
                    else:
                        logger.warning(f"Statement {i} error: {str(e)[:150]}")
                        error_count += 1
            
            logger.debug(f"✅ {description} completed: {success_count}/{len(statements)} statements successful")
            if error_count > 0:
                logger.warning(f"⚠️  {error_count} statements had non-critical errors")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error executing {description}: {str(e)}")
            return False

    def find_sql_files(self):
        """Find SQL files in the data directory."""
        data_folder = Path(__file__).parent / "data"
        
        create_sql = data_folder / "Create_db.sql"
        insert_sql = data_folder / "Insert_data.sql"
        
        files = {}
        
        if create_sql.exists():
            files['create'] = create_sql
            logger.debug(f"✅ Found table creation SQL: {create_sql}")
        else:
            logger.error(f"❌ Create_db.sql not found: {create_sql}")
        
        if insert_sql.exists():
            files['insert'] = insert_sql
            logger.debug(f"✅ Found data insertion SQL: {insert_sql}")
        else:
            logger.error(f"❌ Insert_data.sql not found: {insert_sql}")
        
        return files

    def verify_complete_setup(self):
        """Comprehensive verification of the database setup."""
        try:
            logger.debug("🔍 Performing comprehensive setup verification...")
            
            db = MySQLConnection()
            
            # Check tables exist
            required_tables = [
                'users', 'error_categories', 'java_errors', 'activity_log','badges', 'user_badges']
            
            tables_status = {}
            for table in required_tables:
                try:
                    result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
                    count = result['count'] if result and 'count' in result else 0
                    tables_status[table] = count
                except Exception as e:
                    logger.error(f"Error checking table {table}: {str(e)}")
                    tables_status[table] = -1
            
            # Display results
            all_tables_ok = True
            total_records = 0
            
            logger.debug("📊 Database Verification Results:")
            for table, count in tables_status.items():
                if count == -1:
                    logger.error(f"❌ {table}: Table missing or error")
                    all_tables_ok = False
                elif count == 0:
                    logger.warning(f"⚠️  {table}: Table exists but empty")
                    if table in ['error_categories', 'java_errors', 'badges']:
                        all_tables_ok = False
                else:
                    logger.debug(f"✅ {table}: {count} records")
                    total_records += count
            
            # Check critical data - Updated expected counts
            if all_tables_ok:
                try:
                    # Verify we have all expected data
                    expected_counts = {
                        'error_categories': 8,
                        'java_errors': 41,  # Updated from limited count to full JSON count
                        'badges': 7
                    }
                    
                    for table, expected in expected_counts.items():
                        actual = tables_status.get(table, 0)
                        if actual < expected:
                            logger.warning(f"⚠️  {table}: Expected at least {expected}, got {actual}")
                        else:
                            logger.debug(f"✅ {table}: {actual} records (expected ≥{expected})")
                    
                    # Verify active categories
                    active_cats = db.execute_query(
                        "SELECT COUNT(*) as count FROM error_categories",
                        fetch_one=True
                    )
                    active_count = active_cats['count'] if active_cats else 0
                    
                    if active_count > 0:
                        logger.debug(f"✅ Active error categories: {active_count}")
                    else:
                        logger.error("❌ No active error categories found")
                        all_tables_ok = False
                    
                    # Verify Java errors have proper categories
                    errors_with_cats = db.execute_query("""
                        SELECT COUNT(*) as count 
                        FROM java_errors je 
                        JOIN error_categories ec ON je.category_id = ec.id
                    """, fetch_one=True)
                    
                    if errors_with_cats and errors_with_cats['count'] > 0:
                        logger.debug(f"✅ Java errors with categories: {errors_with_cats['count']}")
                    else:
                        logger.error("❌ No Java errors properly linked to categories")
                        all_tables_ok = False
                    
                    # Check error distribution across categories
                    cat_distribution = db.execute_query("""
                        SELECT ec.name_en, COUNT(je.id) as error_count
                        FROM error_categories ec
                        LEFT JOIN java_errors je ON ec.id = je.category_id
                        GROUP BY ec.id, ec.name_en
                        ORDER BY ec.sort_order
                    """)
                    
                    if cat_distribution:
                        logger.debug("📊 Error distribution by category:")
                        for row in cat_distribution:
                            logger.debug(f"   {row['name_en']}: {row['error_count']} errors")
                        
                except Exception as e:
                    logger.error(f"Error verifying data relationships: {str(e)}")
                    all_tables_ok = False
            
            if all_tables_ok and total_records > 50:  # Updated minimum expected records
                logger.debug(f"🎉 Database setup verification PASSED! Total records: {total_records}")
                return True
            else:
                logger.error("❌ Database setup verification FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification error: {str(e)}")
            return False

    def automated_database_setup(self):
        """Fully automated database setup process."""
        logger.debug("🚀 Starting Automated Database Setup")
        logger.debug("=" * 70)
        
        try:
            # Step 1: Initialize setup
            setup = DatabaseSetup()
            
            if not setup.test_connection():
                logger.error("❌ Cannot connect to MySQL server")
                return False
            
            logger.debug("✅ Database connection verified")
            
            # Step 2: Create database and user
            if not setup.create_database():
                logger.error("❌ Failed to create database")
                return False
            
            if not setup.create_application_user():
                logger.error("❌ Failed to create application user")
                return False
            
            logger.debug("✅ Database and user setup completed")
            
            # Step 3: Find SQL files
            sql_files = self.find_sql_files()
            if not sql_files:
                logger.error("❌ Required SQL files not found")
                return False
            
            # Step 4: Execute SQL files automatically
            db = MySQLConnection()
            
            # Execute table creation first
            if 'create' in sql_files:
                if not self.execute_sql_file_automated(db, sql_files['create'], "Table Creation"):
                    logger.error("❌ Table creation failed")
                    return False
            else:
                logger.error("❌ Create_db.sql file not found")
                return False
            
            # Execute data insertion
            if 'insert' in sql_files:
                if not self.execute_sql_file_automated(db, sql_files['insert'], "Data Insertion"):
                    logger.error("❌ Data insertion failed")
                    return False
            else:
                logger.error("❌ Insert_data.sql file not found")
                return False
            
            # Step 5: Comprehensive verification
            if not self.verify_complete_setup():
                logger.error("❌ Setup verification failed")
                return False
            
            # Step 6: Create/update .env file
            # if setup.create_env_file():
            #     logger.debug("✅ .env file updated")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Automated setup failed: {str(e)}")
            return False

    def main(self):
        """Main function with user interaction."""
        print("🚀 Java Peer Review Training System - Automated Database Setup")
        print("=" * 70)
        
        print("This script will:")
        print("✓ Create the database and application user")
        print("✓ Execute table creation SQL automatically")
        print("✓ Insert all data automatically")
        print("✓ Verify the complete setup")
        print("✓ Update configuration files")
        
        confirm = input("\nProceed with automated setup? (y/n): ")
        if confirm.lower() != 'y':
            print("Setup cancelled")
            return False
        
        # Run automated setup
        success = self.automated_database_setup()
        
        if success:
            print("\n🎉 AUTOMATED SETUP COMPLETED SUCCESSFULLY!")
            print("\n✅ Next steps:")
            print("1. Run verification: python verify_setup.py")
            print("2. Test the system: python examples/database_repository_usage.py")
            print("3. Start the application!")
            
        else:
            print("\n❌ AUTOMATED SETUP FAILED!")
            print("\n🔧 Troubleshooting:")
            print("1. Check database connection settings in .env")
            print("2. Ensure MySQL server is running")
            print("3. Verify SQL files exist in data/ folder")
            print("4. Check the logs above for specific errors")
        
        return success

if __name__ == "__main__":
    dbs = DatabaseSetup()
    success = dbs.main()
    sys.exit(0 if success else 1)
