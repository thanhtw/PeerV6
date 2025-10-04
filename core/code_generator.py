"""
Code Generator module for Java Peer Review Training System.

This module provides the CodeGenerator class which dynamically generates
Java code snippets based on the selected difficulty level and code length,
eliminating the reliance on predefined templates.
"""

import random
import logging
from langchain_core.language_models import BaseLanguageModel
from utils.code_utils import create_code_generation_prompt
from utils.llm_logger import LLMInteractionLogger
from utils.language_utils import t
from data.database_error_repository import DatabaseErrorRepository
import streamlit as st

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodeGenerator:
    """
    Generates Java code snippets dynamically without relying on predefined templates.
    This class creates realistic Java code based on specified complexity and length.
    Enhanced with database integration to show all error categories and their errors.
    """
    def __init__(self, llm: BaseLanguageModel = None, llm_logger: LLMInteractionLogger = None):
        """
        Initialize the CodeGenerator with an optional language model.
        
        Args:
            llm: Language model to use for code generation
            llm_logger: Logger for tracking LLM interactions
        """
        self.llm = llm
        self.llm_logger = llm_logger or LLMInteractionLogger()
        
        # Initialize database repository for error management
        self.error_repository = DatabaseErrorRepository()
        
        # Define complexity profiles for different code lengths
        self.complexity_profiles = {
            "short": {
                "class_count": 1,
                "method_count_range": (1, 2),  # Reduced to 1-2 methods for beginners
                "field_count_range": (1, 3),   # Fewer fields
                "imports_count_range": (0, 1), # Minimal imports
                "nested_class_prob": 0.0,      # No nested classes for beginners
                "interface_prob": 0.0          # No interfaces for beginners
            },
            "medium": {
                "class_count": 1,
                "method_count_range": (3, 5),  # Reduced from 3-6 to 3-5
                "field_count_range": (2, 5),   # Reduced field count
                "imports_count_range": (0, 3), # Fewer imports
                "nested_class_prob": 0.1,      # Reduced probability of nested classes
                "interface_prob": 0.1          # Reduced probability of interfaces
            },
            "long": {
                "class_count": 1,              # Changed from 2 to 1 (with possibility of 2)
                "method_count_range": (4, 8),  # Reduced from 5-10 to 4-8
                "field_count_range": (3, 6),   # Reduced from 4-8 to 3-6
                "imports_count_range": (1, 4), # Reduced from 2-6 to 1-4
                "nested_class_prob": 0.3,      # Reduced from 0.5 to 0.3
                "interface_prob": 0.2          # Reduced from 0.4 to 0.2
            }
        }
        
        # Common Java domains to make code more realistic
        self.domains = [
            "user_management", "file_processing", "data_validation", 
            "calculation", "inventory_system", "notification_service",
            "logging", "banking", "e-commerce", "student_management"
        ]
    
    def get_all_categories_and_errors(self) -> dict:
        """
        Get all error categories and their errors, ordered by difficulty level.
        
        Returns:
            Dictionary containing all categories with their errors ordered by difficulty
        """
        try:
            # Get all categories from the database
            categories_data = self.error_repository.get_all_categories()
            java_error_categories = categories_data.get("java_errors", [])
            
            if not java_error_categories:
                logger.warning("No error categories found in database")
                return {}
            
            # Dictionary to store all categories and their errors
            all_categories_errors = {}
            
            # Difficulty order for sorting
            difficulty_order = {"easy": 1, "medium": 2, "hard": 3}
            
            for category in java_error_categories:
                logger.debug(f"Processing category: {category}")
                
                # Get errors for this category
                category_errors = self.error_repository.get_category_errors(category)
                
                if category_errors:
                    # Sort errors by difficulty level
                    sorted_errors = sorted(
                        category_errors,
                        key=lambda x: (
                            difficulty_order.get(x.get('difficulty_level', 'medium'), 2),
                            x.get(t("error_name"), "")
                        )
                    )
                    
                    all_categories_errors[category] = sorted_errors
                    logger.debug(f"Found {len(sorted_errors)} errors in {category}")
                else:
                    logger.warning(f"No errors found for category: {category}")
                    all_categories_errors[category] = []
            
            return all_categories_errors
            
        except Exception as e:
            logger.error(f"Error getting all categories and errors: {str(e)}")
            return {}
    
    def display_all_categories_and_errors(self) -> str:
        """
        Display all categories and their errors in a formatted string.
        
        Returns:
            Formatted string showing all categories and errors ordered by difficulty
        """
        try:
            all_data = self.get_all_categories_and_errors()
            
            if not all_data:
                return "No error data available"
            
            output_lines = []
            output_lines.append("=" * 80)
            output_lines.append("JAVA ERROR CATEGORIES AND ERRORS (Ordered by Difficulty)")
            output_lines.append("=" * 80)
            output_lines.append("")
            
            total_categories = len(all_data)
            total_errors = sum(len(errors) for errors in all_data.values())
            
            output_lines.append(f"Total Categories: {total_categories}")
            output_lines.append(f"Total Errors: {total_errors}")
            output_lines.append("")
            
            for category_idx, (category, errors) in enumerate(all_data.items(), 1):
                output_lines.append(f"{category_idx}. {category.upper()}")
                output_lines.append("-" * (len(category) + 10))
                
                if not errors:
                    output_lines.append("   No errors available")
                    output_lines.append("")
                    continue
                
                # Group errors by difficulty
                difficulty_groups = {"easy": [], "medium": [], "hard": []}
                
                for error in errors:
                    difficulty = error.get('difficulty_level', 'medium')
                    difficulty_groups[difficulty].append(error)
                
                # Display errors by difficulty level
                for difficulty in ["easy", "medium", "hard"]:
                    if difficulty_groups[difficulty]:
                        output_lines.append(f"   {difficulty.upper()} LEVEL ({len(difficulty_groups[difficulty])} errors):")
                        
                        for error_idx, error in enumerate(difficulty_groups[difficulty], 1):
                            error_name = error.get(t("error_name"), "Unknown Error")
                            error_desc = error.get(t("description"), "No description")
                            
                            # Truncate description if too long
                            if len(error_desc) > 100:
                                error_desc = error_desc[:100] + "..."
                            
                            output_lines.append(f"      {error_idx}. {error_name}")
                            output_lines.append(f"         → {error_desc}")
                            output_lines.append("")
                
                output_lines.append("")
            
            output_lines.append("=" * 80)
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"Error displaying categories and errors: {str(e)}")
            return f"Error displaying data: {str(e)}"
    
    def get_errors_by_difficulty(self, difficulty: str) -> dict:
        """
        Get all errors filtered by difficulty level across all categories.
        
        Args:
            difficulty: Difficulty level ("easy", "medium", "hard")
            
        Returns:
            Dictionary containing errors grouped by category for the specified difficulty
        """
        try:
            all_data = self.get_all_categories_and_errors()
            filtered_data = {}
            
            for category, errors in all_data.items():
                filtered_errors = [
                    error for error in errors 
                    if error.get('difficulty_level', 'medium').lower() == difficulty.lower()
                ]
                
                if filtered_errors:
                    filtered_data[category] = filtered_errors
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering errors by difficulty {difficulty}: {str(e)}")
            return {}

    def _generate_with_llm(self, code_length: str, difficulty_level: str, domain: str = None, 
                       selected_errors=None) -> str:
        """
        Generate Java code using the language model.        
        
        Args:
            code_length: Desired code length (short, medium, long)
            difficulty_level: Difficulty level (easy, medium, hard)
            domain: Optional domain for the code context
            selected_errors: Optional list of errors to include
            
        Returns:
            Generated Java code as a string or AIMessage object
        """

        if not self.llm:
            logger.error("No LLM available for code generation")
            return "// Error: No LLM available for code generation"
    
        # Select a domain if not provided
        if not domain:
            domain = random.choice(self.domains)
        
        # Create a detailed prompt for the LLM using shared utility
        prompt = create_code_generation_prompt(
            code_length=code_length,
            difficulty_level=difficulty_level,
            selected_errors=selected_errors,  # No errors for clean code
            domain=domain,
            include_error_annotations=False if selected_errors is None else True
        )

        try:
            # Metadata for logging
            user_idd = st.session_state.auth.get("user_id")
            metadata = {
                "user_id": user_idd,
                f"{t('code_length')}": code_length,
                f"{t('difficulty_level')}": difficulty_level,
                f"{t('domain')}": domain,
                f"{t('selected_errors')}": []
            }
            
            # Add provider info to metadata if available
            if hasattr(self.llm, 'provider'):
                metadata[t("provider")] = self.llm.provider
                logger.debug(t("generating_java_code_with_provider").format(provider=self.llm.provider))
            elif hasattr(self.llm, 'model_name') and 'groq' in type(self.llm).__name__.lower():
                metadata[t("provider")] = "groq"
                logger.debug(t("generating_java_code_with_groq").format(model=self.llm.model_name))
            else:
                logger.debug(t("generating_java_code_with_llm").format(
                    length=code_length, 
                    difficulty=difficulty_level, 
                    domain=domain
                ))
            
            # Generate the code using the LLM
            response = self.llm.invoke(prompt)
            
            # Log the response type
            logger.debug(t("llm_response_type").format(type=type(response).__name__))
            
            # Log to the LLM logger
            self.llm_logger.log_code_generation(prompt, response, metadata)
            
            # Return the response (can be string or AIMessage depending on provider)
            return response
            
        except Exception as e:
            logger.error(t("error_generating_code_with_llm").format(error=str(e)))          
            return """
    """

