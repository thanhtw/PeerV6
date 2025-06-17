"""
Utility functions for code generation and processing in the Java Code Review System.

This module provides shared functionality for generating prompts, 
extracting code from responses, and handling error comments with improved
organization, error handling, and type safety.
"""
import streamlit as st
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from utils.language_utils import t, get_current_language
from analytics.behavior_tracker import behavior_tracker
import time

# Configure logging
logger = logging.getLogger(__name__)

# Constants
LINE_NUMBER_PADDING = 2

# Code complexity mapping
CODE_COMPLEXITY_MAP = {
    "short": "1 simple class with 1-2 basic methods (15-30 lines total)",
    "medium": "1 class with 3-5 methods of moderate complexity (40-80 lines total)",
    "long": "1-2 classes with 4-8 methods and clear relationships (100-150 lines total)"
}

def get_prompt_template_instance():
    """Get the appropriate prompt template instance for current language."""
    current_language = get_current_language()
    if current_language == "zh":
        from prompts.zh import PromptTemplate
    else:
        from prompts.en import PromptTemplate
    return PromptTemplate()

# =============================================================================
# Code Processing Functions
# =============================================================================

def add_line_numbers(code: str) -> str:
    """
    Add line numbers to code snippet with consistent formatting.
    
    Args:
        code: The code snippet to add line numbers to
        
    Returns:
        Code with line numbers, empty string if input is invalid
    """
    if not code or not isinstance(code, str):
        logger.warning("Invalid code input for line numbering")
        return ""
    
    try:
        lines = code.splitlines()
        if not lines:
            return ""
        
        max_line_num = len(lines)
        padding = max(LINE_NUMBER_PADDING, len(str(max_line_num)))
        
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            line_num = str(i).rjust(padding)
            numbered_lines.append(f"{line_num} | {line}")
        
        return "\n".join(numbered_lines)
        
    except Exception as e:
        logger.error(f"Error adding line numbers: {str(e)}")
        return code  # Return original code if numbering fails

def extract_both_code_versions(response) -> Tuple[str, str]:
    """
    Extract both annotated and clean code versions from LLM response.
    FIXED: Enhanced regex patterns and better handling of various response formats.
    
    Args:
        response: LLM response containing code blocks
        
    Returns:
        Tuple of (annotated_code, clean_code)
    """
    try:
        response_text = process_llm_response(response)
        
        if not response_text:
            logger.error("Empty response from LLM")
            return "", ""
        
        logger.debug(f"Processing LLM response (length: {len(response_text)})")
        logger.debug(f"Response preview: {response_text[:200]}...")
        
        # More comprehensive patterns for different code block formats
        # Order matters - more specific patterns first
        patterns = [
            # Specific annotated and clean patterns
            (r'```java-annotated\s*\n(.*?)```', r'```java-clean\s*\n(.*?)```'),
            (r'```java-annotated(.*?)```', r'```java-clean(.*?)```'),
            
            # Generic Java patterns
            (r'```java\s*\n(.*?)```', r'```java\s*\n(.*?)```'),
            (r'```java(.*?)```', r'```java(.*?)```'),
            
            # Generic code patterns
            (r'```\s*\n(.*?)```', r'```\s*\n(.*?)```'),
            (r'```(.*?)```', r'```(.*?)```'),
        ]
        
        # Try each pattern combination
        for annotated_pattern, clean_pattern in patterns:
            annotated_matches = re.findall(annotated_pattern, response_text, re.DOTALL | re.IGNORECASE)
            clean_matches = re.findall(clean_pattern, response_text, re.DOTALL | re.IGNORECASE)
            
            if annotated_matches and clean_matches:
                # Found both versions
                annotated_code = _clean_extracted_code(annotated_matches[0])
                clean_code = _clean_extracted_code(clean_matches[-1] if len(clean_matches) > 1 else clean_matches[0])
                
                if annotated_code.strip() and clean_code.strip():
                    logger.debug(f"Successfully extracted both versions (annotated: {len(annotated_code)} chars, clean: {len(clean_code)} chars)")
                    return annotated_code, clean_code
        
        # Fallback: try to find any code blocks
        all_code_blocks = []
        fallback_patterns = [
            r'```java-annotated\s*\n?(.*?)```',
            r'```java-clean\s*\n?(.*?)```', 
            r'```java\s*\n?(.*?)```',
            r'```\s*\n?(.*?)```'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                cleaned = _clean_extracted_code(match)
                if cleaned.strip() and len(cleaned.strip()) > 10:  # Must have some substantial content
                    all_code_blocks.append(cleaned)
        
        # Remove duplicates while preserving order
        unique_blocks = []
        for block in all_code_blocks:
            if block not in unique_blocks:
                unique_blocks.append(block)
        
        if len(unique_blocks) >= 2:
            logger.debug(f"Using fallback extraction: found {len(unique_blocks)} unique code blocks")
            return unique_blocks[0], unique_blocks[1]
        elif len(unique_blocks) == 1:
            logger.debug("Using single code block for both versions")
            return unique_blocks[0], unique_blocks[0]
        
        # Last resort: try to extract any Java-like content
        java_content = _extract_java_content_heuristic(response_text)
        if java_content:
            logger.debug("Using heuristic Java content extraction")
            return java_content, java_content
        
        # If all else fails, log the issue and return the raw response
        logger.error("No code blocks found in response using any pattern")
        logger.debug(f"Full response for debugging: {response_text}")
        
        # Return a minimal fallback
        fallback_content = response_text.strip()
        if len(fallback_content) > 100:  # If there's substantial content
            return fallback_content, fallback_content
        else:
            return "", ""
            
    except Exception as e:
        logger.error(f"Error extracting code versions: {str(e)}")
        return "", ""

def _clean_extracted_code(code_text: str) -> str:
    """
    Clean extracted code text by removing common artifacts.
    
    Args:
        code_text: Raw extracted code text
        
    Returns:
        Cleaned code text
    """
    if not code_text:
        return ""
    
    # Remove leading/trailing whitespace
    code = code_text.strip()
    
    # Remove common prefixes/suffixes that might be captured
    prefixes_to_remove = ['java', 'java-annotated', 'java-clean', '\n', '\r\n']
    for prefix in prefixes_to_remove:
        if code.startswith(prefix):
            code = code[len(prefix):].strip()
    
    # Fix line endings
    code = code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive blank lines
    code = re.sub(r'\n{3,}', '\n\n', code)
    
    return code

def _extract_java_content_heuristic(text: str) -> str:
    """
    Heuristic approach to extract Java-like content from text.
    
    Args:
        text: Text to extract Java content from
        
    Returns:
        Extracted Java content or empty string
    """
    try:
        # Look for Java class definition patterns
        java_patterns = [
            r'(public\s+class\s+\w+.*?(?=public\s+class|\Z))',
            r'(class\s+\w+.*?(?=class|\Z))',
            r'(import\s+.*?(?:\n.*?)*?public\s+class.*?(?=import|public\s+class|\Z))'
        ]
        
        for pattern in java_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                content = matches[0].strip()
                if len(content) > 50 and ('class' in content.lower() or 'public' in content.lower()):
                    logger.debug(f"Extracted Java content using heuristic (length: {len(content)})")
                    return content
        
        return ""
        
    except Exception as e:
        logger.error(f"Error in heuristic Java extraction: {str(e)}")
        return ""

def process_llm_response(response) -> str:
    """
    Process and clean LLM response with improved error handling.
    FIXED: Enhanced response processing to handle various response types.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Processed response string
    """
    try:
        if response is None:
            logger.warning("Received None response from LLM")
            return ""
        
        # Handle different response types
        content = ""
        
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict):
            if 'content' in response:
                content = response['content']
            elif 'text' in response:
                content = response['text']
            elif 'output' in response:
                content = response['output']
        elif isinstance(response, (str, bytes)):
            content = response
        else:
            # Try to convert to string as last resort
            content = str(response)
        
        # Ensure we have a string
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        result = str(content).strip() if content else ""
        
        if not result:
            logger.warning("Empty content after processing LLM response")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing LLM response: {str(e)}")
        return ""

# =============================================================================
# Error Formatting Functions
# =============================================================================

def format_errors_for_prompt(errors: List[Dict[str, Any]], language: str = None) -> str:
    """
    Format errors for inclusion in prompts with language support.
    
    Args:
        errors: List of error dictionaries
        language: Target language (uses current if None)
        
    Returns:
        Formatted error string
    """
    if not errors:
        return t("no_errors_available")
    
    error_list = []
    
    for i, error in enumerate(errors, 1):
        try:
            error_name = error.get(t('error_name_variable'), "Unknown Error")
            error_description = error.get(t('description'), "Description not available")
            error_implementation_guide = error.get(t('implementation_guide'), "")
            error_category = error.get(t('category'), "General").upper()
            error_list.append(f"{i}. {t('error_category')}: {error_category} | {t('error_name_variable')}: {error_name} | {t('description')}: {error_description} | {t('implementation_guide')}: {error_implementation_guide}")

        except Exception as e:
            logger.warning(f"Error formatting error {i}: {str(e)}")
            continue
    
    return "\n\n".join(error_list)

def format_problems_for_prompt(problems: List[str]) -> str:
    """
    Format problem list for prompt inclusion.
    
    Args:
        problems: List of problem descriptions
        
    Returns:
        Formatted problems string
    """
    if not problems:
        return t("no_problems_found")
    
    return "\n".join(f"- {problem}" for problem in problems if problem)

# =============================================================================
# Prompt Creation Functions
# =============================================================================

def create_code_generation_prompt(code_length: str, difficulty_level: str, 
                                 selected_errors: List[Dict], domain: str = None, 
                                 include_error_annotations: bool = True) -> str:
    """
    Create a prompt for generating Java code with intentional errors.
    
    Args:
        code_length: Length of code (short, medium, long)
        difficulty_level: Difficulty level (easy, medium, hard)
        selected_errors: List of errors to include
        domain: Domain context for the code
        include_error_annotations: Whether to include error annotations
        
    Returns:
        Generated prompt string
    """
    try:
        complexity = CODE_COMPLEXITY_MAP.get(code_length.lower(), CODE_COMPLEXITY_MAP["medium"])
        
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_code_generation_prompt_template(
            code_length=code_length,
            difficulty_level=difficulty_level,
            domain=domain or "general",
            complexity=complexity,
            error_count=len(selected_errors),
            error_instructions=format_errors_for_prompt(selected_errors, get_current_language())  
        )  
        return prompt        
    except Exception as e:
        logger.error(f"Error creating code generation prompt: {str(e)}")
        return ""

def create_evaluation_prompt(code: str, requested_errors: List[Dict]) -> str:
    """
    Create a prompt for evaluating whether code contains required errors.
    
    Args:
        code: The code to evaluate
        requested_errors: List of errors that should be in the code
        
    Returns:
        Evaluation prompt string
    """
    try:
        if not code or not requested_errors:
            logger.error("Invalid inputs for evaluation prompt")
            return ""
        
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_evaluation_prompt_template(
            error_count=len(requested_errors),
            code=code,
            error_instructions=format_errors_for_prompt(requested_errors, get_current_language())
        )
        return prompt
    except Exception as e:
        logger.error(f"Error creating evaluation prompt: {str(e)}")
        return ""

def create_regeneration_prompt(code: str, domain: str, missing_errors: List,
                              found_errors: List, requested_errors: List) -> str:
    """
    Create a prompt for regenerating code with missing errors.
    
    Args:
        code: The original code
        domain: Domain context
        missing_errors: Errors that need to be added
        found_errors: Errors that were found and should be preserved
        requested_errors: All requested errors
        
    Returns:
        Regeneration prompt string
    """
    try:
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_regeneration_prompt_template(
            total_requested=len(requested_errors),
            domain=domain,
            missing_text=_format_missing_errors(missing_errors),
            found_text=_format_found_errors(found_errors),
            code=code
        )
        return prompt        
    except Exception as e:
        logger.error(f"Error creating regeneration prompt: {str(e)}")
        return ""

def create_review_analysis_prompt(code: str, known_problems: List[str], 
                                 student_review: str, accuracy_threshold: float = 0.7,
                                 meaningful_threshold: float = 0.6) -> str:
    """
    Create a prompt for analyzing a student's review.
    
    Args:
        code: The code being reviewed
        known_problems: List of known problems
        student_review: Student's review text
        accuracy_threshold: Threshold for accuracy scoring
        meaningful_threshold: Threshold for meaningfulness scoring
        
    Returns:
        Review analysis prompt string
    """
    try:
        if not all([code, known_problems, student_review]):
            logger.error("Invalid inputs for review analysis prompt")
            return ""
        
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_review_analysis_prompt_template(
            code=code,
            problem_count=len(known_problems),
            problems_text=format_problems_for_prompt(known_problems),            
            student_review=student_review,
            accuracy_score_threshold=accuracy_threshold,
            meaningful_score_threshold=meaningful_threshold
        )
        
        return prompt
        
    except Exception as e:
        logger.error(f"Error creating review analysis prompt: {str(e)}")
        return ""

def create_feedback_prompt(review_analysis: Dict[str, Any], iteration: int = 1, 
                          max_iterations: int = 3) -> str:
    """
    Create a prompt for generating targeted feedback.
    
    Args:
        review_analysis: Analysis results from review
        iteration: Current iteration number
        max_iterations: Maximum allowed iterations
        
    Returns:
        Feedback prompt string
    """
    try:
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_feedback_prompt_template(
            iteration=iteration,
            max_iterations=max_iterations,
            identified=review_analysis.get(t("identified_count"), 0),
            total=review_analysis.get(t("total_problems"), 0),
            accuracy=review_analysis.get(t("identified_percentage"), 0),
            remaining=max_iterations - iteration,
            identified_text=review_analysis.get(t("identified_problems"), 0),
            missed_text=review_analysis.get(t("missed_problems"),0) 
        )
        return prompt        
    except Exception as e:
        logger.error(f"Error creating feedback prompt: {str(e)}")
        return ""

def create_comparison_report_prompt(review_analysis: Dict[str, Any],
                                   review_history: List = None) -> str:
    """
    Create a prompt for generating a comparison report.
    
    Args:
        review_analysis: Analysis of the latest review
        review_history: History of all review attempts
        
    Returns:
        Comparison report prompt string
    """
    try:
        prompt_template = get_prompt_template_instance()
        prompt = prompt_template.create_comparison_report_prompt_template(
            total_problems=review_analysis.get(t("total_problems"), 0),
            identified=review_analysis.get(t("identified_count"), 0),
            accuracy=review_analysis.get(t("identified_percentage"), 0),
            missed_count=len(review_analysis.get(t("missed_problems"),0)),
            identified_text=review_analysis.get(t("identified_problems"), 0),
            missed_text=review_analysis.get(t("missed_problems"),0)
        )
        return prompt
    except Exception as e:
        logger.error(f"Error creating comparison report prompt: {str(e)}")
        return ""

# =============================================================================
# Helper Functions
# =============================================================================

def _format_missing_errors(missing_errors: List) -> str:
    """Format missing errors for prompt inclusion."""
    if not missing_errors:
        return t("no_missing_errors")
    
    formatted = []
    for i, error in enumerate(missing_errors, 1):
        try:
            if isinstance(error, dict):
                error_type = error.get(t("category"), "").upper()
                name = error.get(t("error_name_variable"), "")
                description = error.get(t("description"), "")
                implementation_guide = error.get(t("implementation_guide"), "")
                
                formatted.append(f"{i}. {error_type} - {name}: {description}")
                if implementation_guide:
                    formatted.append(f" {t('implementation_guide')}: {implementation_guide}")
                formatted.append("")
            else:
                formatted.append(f"{i}. {str(error)}")
        except Exception as e:
            logger.warning(f"Error formatting missing error {i}: {str(e)}")
            continue
    
    return "\n".join(formatted)

def _format_found_errors(found_errors: List) -> str:
    """Format found errors for prompt inclusion."""
    if not found_errors:
        return t("no_found_errors")
    
    formatted = []
    for i, error in enumerate(found_errors, 1):
        try:
            if isinstance(error, dict):
                error_type = error.get(t("category"), "").upper()
                name = error.get(t("error_name_variable"), "")
                description = error.get(t("description"), "")
                formatted.append(f"{i}. {error_type} - {name}: {description}")
            else:
                formatted.append(f"{i}. {str(error)}")
        except Exception as e:
            logger.warning(f"Error formatting found error {i}: {str(e)}")
            continue
    
    return "\n".join(formatted)

def _get_category_icon(category_name: str) -> str:
        
    """Get icon for category based on name (language-aware)."""
    # Map both English and Chinese category names to icons
    icon_mapping = {
            # English category names (from database)
            "logical errors": "🧠",
            "syntax errors": "🔤", 
            "code quality": "⭐",
            "standard violation": "📋",
            "java specific": "☕",
            
            # Chinese category names (from database)
            "邏輯錯誤": "🧠",
            "語法錯誤": "🔤",
            "程式碼品質": "⭐", 
            "標準違規": "📋",
            "java 特定錯誤": "☕",
            
            # Category codes (fallback)
            "logical": "🧠",
            "syntax": "🔤",
            "code_quality": "⭐",
            "standard_violation": "📋", 
            "java_specific": "☕"
        }
        
    # Try exact match first (case-sensitive)
    if category_name in icon_mapping:
        return icon_mapping[category_name]
        
    # Try case-insensitive match
    category_lower = category_name.lower()
    for key, icon in icon_mapping.items():
        if key.lower() == category_lower:
            return icon
        
        # Default fallback icon
    return "🐛"

def _get_difficulty_icon(difficulty_name: str) -> str:
        
    """Get icon for category based on name (language-aware)."""
    # Map both English and Chinese category names to icons
    icon_mapping = {
            # English category names (from database)
            "easy": "⭐",
            "medium": "⭐⭐", 
            "hard": "⭐⭐⭐",           
            
            # Chinese category names (from database)
            "简单": "⭐",
            "中等": "⭐⭐",
            "困難": "⭐⭐⭐"  
        }
        
    # Try exact match first (case-sensitive)
    if difficulty_name in icon_mapping:
        return icon_mapping[difficulty_name]
        
    # Try case-insensitive match
    difficulty_name_lower = difficulty_name.lower()
    for key, icon in icon_mapping.items():
        if key.lower() == difficulty_name_lower:
            return icon
        
        # Default fallback icon
    return "🐛"

def _log_user_interaction_code_display( 
                         user_id: str,
                         interaction_category: str,
                         interaction_type: str,                        
                         success: bool = True,                        
                         details: Dict[str, Any] = None,
                         time_spent_seconds: int = None) -> None:
    """
    Centralized method to log all user interactions to the database.
    
    Args:
        user_id: The user's ID
        interaction_type: 'main_workflow' for main workflow interactions
        action: Specific action taken       
        success: Whether the action was successful       
        details: Additional details about the interaction
        time_spent_seconds: Time spent on this interaction
    """
    try:
        if not user_id:
            return
        
        
        # Prepare context data
        context_data = {            
            "current_step": getattr(st.session_state.get("workflow_state"), 'current_step', 'unknown') if hasattr(st.session_state, 'workflow_state') else 'unknown',
            "current_iteration": getattr(st.session_state.get("workflow_state"), 'current_iteration', 0) if hasattr(st.session_state, 'workflow_state') else 0,
            "has_code_snippet": hasattr(st.session_state.get("workflow_state"), 'code_snippet') if hasattr(st.session_state, 'workflow_state') else False,
            "language": get_current_language(),
            "timestamp": time.time()
        }
        
        # Log through behavior tracker
        behavior_tracker.log_interaction(
            user_id=user_id,
            interaction_category=interaction_category,
            interaction_type=interaction_type,           
            details=context_data,
            time_spent_seconds=time_spent_seconds,
            success=success
                        
        )
        
        logger.debug(f"Logged {interaction_type} interaction: {interaction_category} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging user interaction: {str(e)}")

def _log_user_interaction_code_generator( 
                         user_id: str,
                         interaction_category: str,
                         interaction_type: str,                         
                         success: bool = True,                        
                         details: Dict[str, Any] = None,
                         time_spent_seconds: int = None) -> None:
    """
    Centralized method to log all user interactions to the database.
    """
    try:
        if not user_id:
            return
        
        context_data = {            
            "selected_categories": st.session_state.get("selected_categories", []),
            "user_level": st.session_state.get("user_level", "medium"),
            "workflow_step": "generate",
            "language": get_current_language(),
            "timestamp": time.time()
        }
        
       
        behavior_tracker.log_interaction(
            user_id=user_id,
            interaction_category=interaction_category,
            interaction_type=interaction_type,           
            details=context_data,
            time_spent_seconds=time_spent_seconds,
            success=success
                    
        )
        
        logger.debug(f"Logged {interaction_type} interaction: {interaction_category} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging user interaction: {str(e)}")

def _log_user_interaction_feedback_system( 
                         user_id: str,
                         interaction_category: str,
                         interaction_type: str,                        
                         success: bool = True,                        
                         details: Dict[str, Any] = None,
                         time_spent_seconds: int = None) -> None:
    """
    Centralized method to log all user interactions to the database.
    """
    try:
        if not user_id:
            return
        
        
        context_data = {          
            "has_review_history": bool(getattr(st.session_state.get("workflow_state"), 'review_history', [])) if hasattr(st.session_state, 'workflow_state') else False,
            "language": get_current_language(),
            "timestamp": time.time()
        }
      
        
        behavior_tracker.log_interaction(
            user_id=user_id,
            interaction_category=interaction_category,
            interaction_type=interaction_type,     
            details=context_data,
            time_spent_seconds=time_spent_seconds,
            success=success
            
        )
        
        logger.debug(f"Logged {interaction_type} interaction: {interaction_category} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging user interaction: {str(e)}")

def _log_user_interaction_tutorial(user_id: str,
                         interaction_category: str,
                         interaction_type: str,                        
                         success: bool = True,                        
                         details: Dict[str, Any] = None,
                         time_spent_seconds: int = None) -> None:
    """
    Centralized method to log all user interactions to the database.
    
    Args:
        user_id: The user's ID
        interaction_type: Type of interaction (e.g., 'tutorial', 'practice')
        action: Specific action taken        
        success: Whether the action was successful
        details: Additional details about the interaction
        time_spent_seconds: Time spent on this interaction
    """
    try:
        if not user_id:
            return
        
               
        context_data = {
            "language": get_current_language(),
            "timestamp": time.time()
        }
               
        if hasattr(st.session_state, 'workflow_state') and st.session_state.workflow_state:
            context_data.update({
                "current_step": getattr(st.session_state.workflow_state, 'current_step', 'unknown'),
                "current_iteration": getattr(st.session_state.workflow_state, 'current_iteration', 0),
                "has_code_snippet": hasattr(st.session_state.workflow_state, 'code_snippet')
            })
             
        
        # Log through behavior tracker
        behavior_tracker.log_interaction(
            user_id=user_id,
            interaction_category=interaction_category,
            interaction_type=interaction_type,      
            details=context_data,
            time_spent_seconds=time_spent_seconds,
            success=success,                    
        )
        
        logger.debug(f"Logged {interaction_type} interaction: {interaction_category} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging user interaction: {str(e)}")

