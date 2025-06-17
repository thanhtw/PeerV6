# data/__init__.py
"""
Data access package for Java Peer Review Training System.

This package provides access to error data through both database and JSON-based repositories.
The database repository is now the primary method for accessing error data.
"""

# Import the main repositories
from data.database_error_repository import DatabaseErrorRepository
# Default to database repository for new code
ErrorRepository = DatabaseErrorRepository

# Create convenience functions
def create_error_repository(use_database=True):
    """
    Create an error repository instance.
    
    Args:
        use_database: If True, use DatabaseErrorRepository. If False, use JsonErrorRepository.
        
    Returns:
        Error repository instance    """
    
    return DatabaseErrorRepository()
   

def get_default_repository():
    """Get the default error repository (database-based)."""
    return DatabaseErrorRepository()

__all__ = [
    'DatabaseErrorRepository',
    'JsonErrorRepository', 
    'ErrorRepository',
    'create_error_repository',
    'get_default_repository'
]

# Version information
__version__ = "2.0.0"  # Updated for database support