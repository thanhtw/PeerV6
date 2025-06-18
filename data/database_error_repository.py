# data/database_error_repository.py
"""
Database Error Repository module for Java Peer Review Training System.

This module provides access to error data from the database,
replacing the JSON file-based approach for better performance and maintainability.
"""

import logging
import random
import json
from typing import Dict, List, Any, Optional, Set, Union, Tuple
from data.mysql_connection import MySQLConnection
from utils.language_utils import get_current_language, t

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseErrorRepository:
    """
    Repository for accessing Java error data from the database.
    
    This class handles loading, categorizing, and providing access to
    error data stored in the database tables.
    """
    
    def __init__(self):
        """Initialize the Database Error Repository."""
        self.db = MySQLConnection()
        self.current_language = get_current_language()
        
        # Cache for frequently accessed data
        self._categories_cache = None
        self._cache_timestamp = None
        
        # Verify database connection and tables
        self._verify_database_setup()
    
    def _verify_database_setup(self):
        """Verify that the required database tables exist and have data."""
        try:
            # Test basic connection first
            if not self.db.test_connection_only():
                logger.debug("Database connection not available. Please run setup first.")
                return
            
            # Check if error_categories table exists and has data
            check_query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'error_categories'
            """
            result = self.db.execute_query(check_query, fetch_one=True)
            
            if not result or result.get('count', 0) == 0:
                logger.debug("Error categories table not found. Please run database setup first.")
                return
            
            # Check if categories have data
            data_query = "SELECT COUNT(*) as count FROM error_categories"
            data_result = self.db.execute_query(data_query, fetch_one=True)
            
            if not data_result or data_result.get('count', 0) == 0:
                logger.debug("No categories found. Please import data using the SQL file.")
                return
            
            # Check if java_errors table exists and has data  
            check_query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'java_errors'
            """
            result = self.db.execute_query(check_query, fetch_one=True)
            
            if not result or result.get('count', 0) == 0:
                logger.debug("Java errors table not found. Please run database setup first.")
                return
            
            # Check if errors have data
            data_query = "SELECT COUNT(*) as count FROM java_errors"
            data_result = self.db.execute_query(data_query, fetch_one=True)
            
            if not data_result or data_result.get('count', 0) == 0:
                logger.debug("No error data found. Please import data using the SQL file.")
                return
                
            logger.debug(f"Database verified: {data_result['count']} errors available")
            
        except Exception as e:
            logger.debug(f"Database not ready: {str(e)}. Please run setup and import data first.")
    
    def _get_language_fields(self, base_field: str) -> str:
        """Get the appropriate language field name."""
        if self.current_language == 'zh':
            return f"{base_field}_zh"
        else:
            return f"{base_field}_en"
    
    def _invalidate_cache(self):
        """Invalidate the categories cache."""
        self._categories_cache = None
        self._cache_timestamp = None
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """
        Get all error categories.
        
        Returns:
            Dictionary with 'java_errors' categories
        """
        try:
            self.current_language = get_current_language()
            name_field = self._get_language_fields('name')
            description_field = self._get_language_fields('description')
            
            query = f"""
            SELECT {name_field} as name, {description_field} as description
            FROM error_categories            
            ORDER BY sort_order
            """
            
            categories = self.db.execute_query(query)
            
            if categories:
                category_names = [cat['name'] for cat in categories]
                categories_descriptions = [cat['description'] for cat in categories]
                logger.debug(f"Found {len(category_names)} categories in database")
                return {"java_errors": category_names, "descriptions": categories_descriptions}
            else:
                logger.warning("No categories found in database")
                return {"java_errors": [], "descriptions": []}

        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return {"java_errors": [], "descriptions": []}

    def get_category_errors(self, category_name: str) -> List[Dict[str, str]]:
        try:
            self.current_language = get_current_language()
            
            # Get field names based on language
            name_field = self._get_language_fields('error_name')
            desc_field = self._get_language_fields('description')
            guide_field = self._get_language_fields('implementation_guide')
            
            # First, find the category by name in current language
            cat_name_field = self._get_language_fields('name')
            category_query = f"""
            SELECT id,name_en, name_zh 
            FROM error_categories 
            WHERE {cat_name_field} = %s
            """
            
            category = self.db.execute_query(category_query, (category_name,), fetch_one=True)
            
            if not category:
                logger.warning(f"Category not found: {category_name}")
                return []
            
            # Get errors for this category
            errors_query = f"""
            SELECT 
                {name_field} as error_name,
                {desc_field} as description,
                {guide_field} as implementation_guide,
                difficulty_level,
                error_code
            FROM java_errors 
            WHERE category_id = %s
            ORDER BY error_name_en
            """
            
            errors = self.db.execute_query(errors_query, (category['id'],))
            
            # Format the results to match the expected JSON structure
            formatted_errors = []
            for error in errors or []:
                formatted_errors.append({
                    t("error_name"): error.get('error_name', ''),
                    t("description"): error.get('description', ''),
                    t("implementation_guide"): error.get('implementation_guide', ''),
                    t("difficulty_level"): error.get('difficulty_level', 'medium'),
                    t("error_code"): error.get('error_code', '')
                })
            
            return formatted_errors
            
        except Exception as e:
            logger.error(f"Error getting category errors for {category_name}: {str(e)}")
            return []
    
    def get_errors_by_categories(self, selected_categories: Dict[str, List[str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Get errors for selected categories.
        
        Args:
            selected_categories: Dictionary with 'java_errors' key
                              containing a list of selected categories
            
        Returns:
            Dictionary with selected errors by category type
        """
        selected_errors = {"java_errors": []}
        
        if "java_errors" in selected_categories:
            for category in selected_categories["java_errors"]:
                category_errors = self.get_category_errors(category)
                selected_errors["java_errors"].extend(category_errors)
        
        return selected_errors
    
    def get_error_details(self, error_type: str, error_name: str) -> Optional[Dict[str, str]]:
        """
        Get details for a specific error.
        
        Args:
            error_type: Type of error ('java_error')
            error_name: Name of the error
            
        Returns:
            Error details dictionary or None if not found
        """
        if error_type != "java_error":
            return None
        
        try:
            self.current_language = get_current_language()
            
            name_field = self._get_language_fields('error_name')
            desc_field = self._get_language_fields('description')
            guide_field = self._get_language_fields('implementation_guide')
            
            query = f"""
            SELECT 
                {name_field} as error_name,
                {desc_field} as description,
                {guide_field} as implementation_guide,
                difficulty_level,
                error_code
            FROM java_errors 
            WHERE {name_field} = %s
            """
            
            error = self.db.execute_query(query, (error_name,), fetch_one=True)
            
            if error:
                return {
                    t("error_name"): error['error_name'],
                    t("description"): error['description'],
                    t("implementation_guide"): error.get('implementation_guide', ''),
                    t("difficulty_level"): error.get('difficulty_level', 'medium'),
                    t("error_code"): error.get('error_code', '')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting error details for {error_name}: {str(e)}")
            return None
    
    def get_random_errors_by_categories(self, selected_categories: Dict[str, List[str]], 
                                      count: int = 4) -> List[Dict[str, Any]]:
        """
        Get random errors from selected categories.
        
        Args:
            selected_categories: Dictionary with 'java_errors' key
                            containing a list of selected categories
            count: Number of errors to select
            
        Returns:
            List of selected errors with type and category information
        """
        try:
            self.current_language = get_current_language()
            
            java_error_categories = selected_categories.get("java_errors", [])
            if not java_error_categories:
                return []
            
            # Get field names based on language
            name_field = self._get_language_fields('error_name')
            desc_field = self._get_language_fields('description')
            guide_field = self._get_language_fields('implementation_guide')
            cat_name_field = self._get_language_fields('name')
            
            # Build query to get random errors from selected categories
            placeholders = ','.join(['%s'] * len(java_error_categories))
            
            query = f"""
            SELECT 
                je.{name_field} as error_name,
                je.{desc_field} as description,
                je.{guide_field} as implementation_guide,
                je.difficulty_level,
                je.error_code,
                ec.{cat_name_field} as category_name
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id
            WHERE ec.{cat_name_field} IN ({placeholders})            
            ORDER BY RAND()
            LIMIT %s
            """
            
            params = tuple(java_error_categories) + (count,)
            errors = self.db.execute_query(query, params)
            
            # Format results
            formatted_errors = []
            for error in errors or []:
                formatted_errors.append({
                    t("type"): "java_error",
                    t("category"): error['category_name'],
                    t("error_name"): error['error_name'],
                    t("description"): error['description'],
                    t("implementation_guide"): error.get('implementation_guide', ''),
                    t("difficulty_level"): error.get('difficulty_level', 'medium'),
                    t("error_code"): error.get('error_code', '')
                })
            
            return formatted_errors
            
        except Exception as e:
            logger.error(f"Error getting random errors: {str(e)}")
            return []
    
    def get_errors_for_llm(self, 
                          selected_categories: Dict[str, List[str]] = None, 
                          specific_errors: List[Dict[str, Any]] = None,
                          count: int = 4, 
                          difficulty: str = "medium") -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Get errors suitable for sending to the LLM for code generation.
        Can use either category-based selection or specific errors.
        Tries to always return errors if possible.
        """
        # Map difficulty levels properly
        difficulty_map = {
            "easy": "easy",
            "medium": "medium", 
            "hard": "hard",
            "簡單": "easy",
            "中等": "medium",
            "困難": "hard"
        }
        mapped_difficulty = difficulty_map.get(difficulty.lower(), "medium")
        adjusted_count = count
        # If specific errors are provided, use those
        if specific_errors and len(specific_errors) > 0:
            problem_descriptions = []
            selected_errors = []
            for error in specific_errors:
                processed_error = error.copy()
                name = processed_error.get(t("error_name_variable"), processed_error.get("name", "Unknown"))
                description = processed_error.get(t("description"), "")
                category = processed_error.get(t("category"), "")
                implementation_guide = self._get_implementation_guide(name, category)
                if implementation_guide:
                    processed_error[t("implementation_guide")] = implementation_guide
                problem_descriptions.append(f"{category}: {name} - {description}")
                selected_errors.append(processed_error)
            return selected_errors, problem_descriptions
        
        elif selected_categories:
            try:
                self.current_language = get_current_language()
                java_error_categories = selected_categories.get("java_errors", [])
                if not java_error_categories:
                    logger.warning("No categories specified, using defaults")
                    default_cats = self.get_all_categories()
                    java_error_categories = default_cats.get("java_errors", [])[:3]
                name_field = self._get_language_fields('error_name')
                desc_field = self._get_language_fields('description')
                guide_field = self._get_language_fields('implementation_guide')
                cat_name_field = self._get_language_fields('name')
                placeholders = ','.join(['%s'] * len(java_error_categories))
                # 1. Try with difficulty
                query = f"""
                SELECT 
                    je.{name_field} as error_name,
                    je.{desc_field} as description,
                    je.{guide_field} as implementation_guide,
                    je.difficulty_level,
                    je.error_code,
                    ec.{cat_name_field} as category_name
                FROM java_errors je
                JOIN error_categories ec ON je.category_id = ec.id
                WHERE ec.{cat_name_field} IN ({placeholders})               
                AND je.difficulty_level = %s
                ORDER BY RAND()
                LIMIT %s
                """
                params = tuple(java_error_categories) + (mapped_difficulty, adjusted_count)
                errors = self.db.execute_query(query, params)
                if errors and len(errors) >= adjusted_count:
                    logger.debug(f"Selected {len(errors)} errors for LLM (with difficulty)")
                
                # Format results
                selected_errors = []
                problem_descriptions = []
                for error in errors or []:
                    error_data = {
                        t("category"): error['category_name'],
                        t("error_name"): error['error_name'],
                        t("description"): error['description'],
                        t("implementation_guide"): error.get('implementation_guide', ''),
                        t("difficulty_level"): error.get('difficulty_level', 'medium'),
                        t("error_code"): error.get('error_code', '')
                    }
                    selected_errors.append(error_data)
                    problem_descriptions.append(
                        f"{error['category_name']}: {error['error_name']} - {error['description']}"
                    )
                logger.debug(f"Selected {len(selected_errors)} errors for LLM (final)")
                return selected_errors, problem_descriptions
            except Exception as e:
                logger.error(f"Error getting errors for LLM: {str(e)}")
                return [], []
        logger.warning("No selection method provided, returning empty error list")
        return [], []
    
    def _get_implementation_guide(self, error_name: str, category: str) -> Optional[str]:
        """
        Get implementation guide for a specific error.
        
        Args:
            error_name: Name of the error
            category: Category of the error
            
        Returns:
            Implementation guide string or None if not found
        """
        try:
            self.current_language = get_current_language()
            
            name_field = self._get_language_fields('error_name')
            guide_field = self._get_language_fields('implementation_guide')
            cat_name_field = self._get_language_fields('name')
            
            query = f"""
            SELECT je.{guide_field} as implementation_guide
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id
            WHERE je.{name_field} = %s AND ec.{cat_name_field} = %s           
            """
            
            result = self.db.execute_query(query, (error_name, category), fetch_one=True)
            
            if result:
                return result.get('implementation_guide')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting implementation guide: {str(e)}")
            return None
    
    def get_error_by_name(self, error_type: str, error_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific error by name.
        
        Args:
            error_type: Type of error ('java_error')
            error_name: Name of the error
            
        Returns:
            Error dictionary with added type and category, or None if not found
        """
        if error_type != "java_error":
            return None
        
        try:
            self.current_language = get_current_language()
            
            name_field = self._get_language_fields('error_name')
            desc_field = self._get_language_fields('description')
            cat_name_field = self._get_language_fields('name')
            
            query = f"""
            SELECT 
                je.{name_field} as error_name,
                je.{desc_field} as description,
                ec.{cat_name_field} as category_name
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id
            WHERE je.{name_field} = %s             
            """
            
            result = self.db.execute_query(query, (error_name,), fetch_one=True)
            
            if result:
                return {
                    t("category"): result['category_name'],
                    t("error_name"): result['error_name'],
                    t("description"): result['description']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting error by name {error_name}: {str(e)}")
            return None
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about the error database."""
        try:
            stats = {}
            
            # Total categories
            cat_query = "SELECT COUNT(*) as count FROM error_categories"
            cat_result = self.db.execute_query(cat_query, fetch_one=True)
            stats['total_categories'] = cat_result['count'] if cat_result else 0
            
            # Total errors
            err_query = "SELECT COUNT(*) as count FROM java_errors"
            err_result = self.db.execute_query(err_query, fetch_one=True)
            stats['total_errors'] = err_result['count'] if err_result else 0
            
            # Errors by category
            breakdown_query = """
            SELECT ec.name_en, COUNT(je.id) as error_count
            FROM error_categories ec
            LEFT JOIN java_errors je ON ec.id = je.category_id           
            GROUP BY ec.id
            ORDER BY ec.sort_order
            """
            breakdown = self.db.execute_query(breakdown_query)
            stats['errors_by_category'] = {row['name_en']: row['error_count'] for row in breakdown or []}
            
            # Most used errors
            popular_query = """
            SELECT error_name_en, usage_count
            FROM java_errors 
            ORDER BY usage_count DESC 
            LIMIT 5
            """
            popular = self.db.execute_query(popular_query)
            stats['most_used_errors'] = [
                {t('name'): row['error_name_en'], 'usage_count': row['usage_count']} 
                for row in popular or []
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}

    def get_error_examples(self, error_name: str) -> Dict[str, Any]:
        """
        Get example codes for a specific error from database.
        
        Args:
            error_name: Name of the error
            
        Returns:
            Dictionary containing example codes and solutions
        """
        try:
            self.current_language = get_current_language()
            name_field = self._get_language_fields('error_name')
            
            query = f"""
            SELECT examples, tags
            FROM java_errors 
            WHERE {name_field} = %s
            """
            
            result = self.db.execute_query(query, (error_name,), fetch_one=True)
            
            if result and result.get('examples'):
                try:
                    examples_data = json.loads(result['examples']) if isinstance(result['examples'], str) else result['examples']
                    
                    # Extract wrong and correct examples
                    examples = {
                        "wrong_examples": [],
                        "correct_examples": [],
                        "explanation": ""
                    }
                    
                    if isinstance(examples_data, list):
                        for example in examples_data:
                            if 'wrong' in example:
                                examples["wrong_examples"].append(example['wrong'])
                            if 'correct' in example:
                                examples["correct_examples"].append(example['correct'])
                            if 'advice' in example:
                                examples["explanation"] = example['advice']
                    
                    return examples
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in examples for error: {error_name}")
                    
            return self._get_default_examples(error_name)
            
        except Exception as e:
            logger.error(f"Error getting examples for {error_name}: {str(e)}")
            return self._get_default_examples(error_name)
    
    def _get_default_examples(self, error_name: str) -> Dict[str, Any]:
        """Generate default examples when database examples are not available."""
        return {
            "wrong_examples": [f"// Example showing {error_name}\n// This code demonstrates the error"],
            "correct_examples": [f"// Corrected version\n// This code shows the proper implementation"],
            "explanation": f"This demonstrates how to identify and fix {error_name}"
        }
    
    def get_all_errors_with_examples(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all errors with their examples for pattern recognition game.
        
        Returns:
            Dictionary of errors with their pattern data
        """
        try:
            self.current_language = get_current_language()
            name_field = self._get_language_fields('error_name')
            desc_field = self._get_language_fields('description')
            
            query = f"""
            SELECT 
                ec.name_en,
                je.{name_field} as error_name,
                je.{desc_field} as description,
                je.examples,
                je.tags
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id           
            ORDER BY ec.sort_order, je.{name_field}
            """
            
            errors = self.db.execute_query(query)
            pattern_database = {}
            
            for error in errors or []:
                error_key = error['error_name'].lower().replace(" ", "_")
                
                # Parse examples from JSON
                examples_data = {}
                if error.get('examples'):
                    try:
                        examples_json = json.loads(error['examples']) if isinstance(error['examples'], str) else error['examples']
                        
                        correct_patterns = []
                        incorrect_patterns = []
                        
                        if isinstance(examples_json, list):
                            for example in examples_json:
                                if 'wrong' in example:
                                    correct_patterns.append(example['wrong'])  # Wrong examples become "correct" patterns to identify
                                if 'correct' in example:
                                    incorrect_patterns.append(example['correct'])  # Correct examples become "incorrect" patterns
                        
                        examples_data = {
                            "correct_patterns": correct_patterns,
                            "incorrect_patterns": incorrect_patterns
                        }
                        
                    except json.JSONDecodeError:
                        examples_data = self._get_default_pattern_examples(error['error_name'])
                else:
                    examples_data = self._get_default_pattern_examples(error['error_name'])
                
                pattern_database[error_key] = {
                    t("error_name"): error['error_name'],
                    t("description"): error['description'],
                    t("correct_patterns"): examples_data.get("correct_patterns", []),
                    t("incorrect_patterns"): examples_data.get("incorrect_patterns", []),
                    t("explanation"): f"Learn to identify {error['error_name']} patterns",
                    t("warning_signs"): self._extract_warning_signs(error.get('tags'))
                }
            
            return pattern_database
            
        except Exception as e:
            logger.error(f"Error getting pattern database: {str(e)}")
            return {}
    
    def _get_default_pattern_examples(self, error_name: str) -> Dict[str, List[str]]:
        """Generate default pattern examples."""
        return {
            "correct_patterns": [f"// Pattern showing {error_name}"],
            "incorrect_patterns": [f"// Correct implementation"]
        }
    
    def _extract_warning_signs(self, tags_json: str) -> List[str]:
        """Extract warning signs from tags JSON."""
        try:
            if tags_json:
                tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
                if isinstance(tags, list):
                    return [f"Look for {tag}" for tag in tags[:3]]  # First 3 tags as warning signs
        except:
            pass
        return ["Review code carefully", "Check logic flow", "Verify syntax"]
        
# Compatibility function to maintain backward compatibility
def create_database_repository() -> DatabaseErrorRepository:
    """Create and return a DatabaseErrorRepository instance."""
    return DatabaseErrorRepository()