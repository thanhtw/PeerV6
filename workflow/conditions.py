"""
FIXED: Schema-compliant Workflow Conditions for Java Peer Review Training System.

This module contains the conditional logic with clear separation between
code generation and review phases, and proper use of review_sufficient.
FIXED: Clear definition and usage of review_sufficient variable.
"""

import logging
from typing import Dict, Any, List, Optional
from state_schema import WorkflowState
from utils.language_utils import t

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowConditions:
    """
    FIXED: Conditional logic for the Java Code Review workflow with clear phase separation.
    
    This class contains all the conditional functions with enhanced review_sufficient logic
    and proper separation between code generation and review processing phases.
    """
    
    @staticmethod
    def should_regenerate_or_complete(state: WorkflowState) -> str:
        """
        PHASE 1: Code Generation Decision - Complete when code is ready for review.
        FIXED: This should only handle code generation, not review logic.
        """
        try:
            evaluation_result = getattr(state, "evaluation_result", None)
            evaluation_attempts = getattr(state, "evaluation_attempts", 0)
            max_evaluation_attempts = getattr(state, "max_evaluation_attempts", 3)
            
            logger.debug(f"CODE GENERATION DECISION: "
                        f"valid={evaluation_result.get(t('valid'), False) if evaluation_result else False}, "
                        f"attempts={evaluation_attempts}/{max_evaluation_attempts}")
            
            # Check max attempts FIRST
            if evaluation_attempts >= max_evaluation_attempts:
                logger.debug(f"CODE GENERATION: Max attempts ({max_evaluation_attempts}) reached. "
                           f"Code generation complete.")
                return "complete"
            
            # Check evaluation result
            if evaluation_result:
                is_valid = evaluation_result.get(t("valid"), False)
                missing_errors = evaluation_result.get(t("missing_errors"), [])
                
                if is_valid or len(missing_errors) == 0:
                    logger.debug("CODE GENERATION: Evaluation passed. Code ready for review.")
                    return "complete"
                
                # Need regeneration if missing errors and under max attempts
                if len(missing_errors) > 0 and evaluation_attempts < max_evaluation_attempts:
                    logger.debug(f"CODE GENERATION: Missing {len(missing_errors)} errors. Regenerating.")
                    return "regenerate_code"
            
            # Default to complete (safety fallback)
            logger.debug("CODE GENERATION: No clear evaluation result, completing generation")
            return "complete"
            
        except Exception as e:
            logger.error(f"Error in should_regenerate_or_complete: {str(e)}")
            return "complete"
    
    @staticmethod
    def should_continue_review_or_complete(state: WorkflowState) -> str:
        """
        PHASE 2: Review Decision - FIXED with clear review_sufficient logic.
        
        review_sufficient is set to True when:
        1. Student has identified ALL errors in the code, OR
        2. Student has identified a sufficient percentage (e.g., 80%+) of errors
        
        This method determines whether to continue waiting for more reviews
        or to generate the final comparison report.
        """
        try:
            current_iteration = getattr(state, "current_iteration", 1)
            max_iterations = getattr(state, "max_iterations", 3)
            review_sufficient = getattr(state, "review_sufficient", False)
            review_history = getattr(state, "review_history", [])
            original_error_count = getattr(state, "original_error_count", 0)
            
            logger.debug(f"REVIEW DECISION: "
                         f"iteration={current_iteration}/{max_iterations}, "
                         f"sufficient={review_sufficient}, "
                         f"review_count={len(review_history)}, "
                         f"original_errors={original_error_count}")
            
            # PRIORITY 1: Check if review is marked as sufficient
            if review_sufficient:
                logger.debug("REVIEW: Review marked as sufficient. Generating final report.")
                return "generate_comparison_report"
            
            # PRIORITY 2: Check max iterations reached
            if current_iteration > max_iterations:
                logger.debug(f"REVIEW: Max iterations ({max_iterations}) reached. Generating final report.")
                return "generate_comparison_report"
            
            # PRIORITY 3: Check if all errors found in latest review
            if review_history and len(review_history) > 0:
                latest_review = review_history[-1]
                if hasattr(latest_review, "analysis") and latest_review.analysis:
                    analysis = latest_review.analysis
                    identified_count = analysis.get(t("identified_count"), 0)
                    total_problems = analysis.get(t("total_problems"), original_error_count)
                    
                    # FIXED: Clear definition of when review is sufficient
                    if identified_count >= total_problems and total_problems > 0:
                        logger.debug(f"REVIEW: All {total_problems} errors found. Review sufficient!")
                        # Mark as sufficient for future checks
                        state.review_sufficient = True
                        return "generate_comparison_report"
                    
                    # Optional: Consider review sufficient if high percentage found
                    if total_problems > 0:
                        accuracy_percentage = (identified_count / total_problems) * 100
                        if accuracy_percentage >= 90.0:  # 90% threshold for sufficient review
                            logger.debug(f"REVIEW: High accuracy ({accuracy_percentage:.1f}%). Review sufficient!")
                            state.review_sufficient = True
                            return "generate_comparison_report"
                        else:
                            logger.debug(f"REVIEW: Progress - {identified_count}/{total_problems} "
                                       f"({accuracy_percentage:.1f}%) identified")
            
            # Continue waiting for more reviews
            if current_iteration <= max_iterations and not review_sufficient:
                logger.debug(f"REVIEW: Continuing review phase (iteration {current_iteration}/{max_iterations})")
                return "continue_review"
            else:
                logger.debug("REVIEW: Conditions met for completion. Generating report.")
                return "generate_comparison_report"
                
        except Exception as e:
            logger.error(f"Error in should_continue_review_or_complete: {str(e)}")
            # Safe fallback
            return "generate_comparison_report"
    
    @staticmethod
    def evaluate_review_sufficiency(state: WorkflowState, analysis: Dict[str, Any]) -> bool:
        """
        HELPER: Evaluate if a review is sufficient based on analysis results.
        
        FIXED: Clear definition of review_sufficient criteria:
        - Student found ALL errors (100% accuracy), OR
        - Student found 90%+ of errors (high accuracy threshold)
        
        Args:
            state: Current workflow state
            analysis: Review analysis results
            
        Returns:
            bool: True if review is sufficient, False otherwise
        """
        try:
            
            identified_count = analysis.get(t("identified_count"), 0)
            total_problems = analysis.get(t("total_problems"), 0)
            original_error_count = getattr(state, "original_error_count", 0)            
            # Use original_error_count as the authoritative source
            if original_error_count > 0:
                total_problems = original_error_count
            
            if total_problems <= 0:
                logger.warning("No total problems to evaluate against")
                return False
            
            # Calculate accuracy
            accuracy_percentage = (identified_count / total_problems) * 100
            
            # FIXED: Clear sufficiency criteria
            is_sufficient = False
            
            # Criterion 1: All errors found (100% accuracy)
            if identified_count >= total_problems:
                is_sufficient = True
                logger.info(f"Review sufficient: All {total_problems} errors found (100%)")
            
            # Criterion 2: High accuracy threshold (90%+)
            elif accuracy_percentage >= 90.0:
                is_sufficient = True
                logger.info(f"Review sufficient: High accuracy ({accuracy_percentage:.1f}% >= 90%)")
            
            else:
                logger.info(f"Review not sufficient: {identified_count}/{total_problems} "
                           f"({accuracy_percentage:.1f}%) - needs 90%+ or all errors")
            
            return is_sufficient
            
        except Exception as e:
            logger.error(f"Error evaluating review sufficiency: {str(e)}")
            return False
    
    @staticmethod
    def validate_state_for_review(state: WorkflowState) -> bool:
        """
        ENHANCED: Validate state for review processing.
        """
        try:
            validation_errors = []
            
            # Check for required code snippet
            if not hasattr(state, 'code_snippet') or not state.code_snippet:
                validation_errors.append("No code snippet")
            elif not hasattr(state.code_snippet, 'code') or not state.code_snippet.code:
                validation_errors.append("Code snippet has no code content")
            
            # Check for required error information
            original_error_count = getattr(state, 'original_error_count', 0)
            if original_error_count <= 0:
                validation_errors.append("No valid original error count")
            
            # Check iteration settings with auto-correction
            max_iterations = getattr(state, 'max_iterations', 0)
            if max_iterations <= 0:
                logger.warning("Invalid max_iterations, setting to default (3)")
                state.max_iterations = 3
            
            current_iteration = getattr(state, 'current_iteration', 0)
            if current_iteration <= 0:
                logger.warning("Invalid current_iteration, setting to default (1)")
                state.current_iteration = 1
            
            # FIXED: Initialize review_sufficient if not set
            if not hasattr(state, 'review_sufficient'):
                state.review_sufficient = False
                logger.debug("Initialized review_sufficient to False")
            
            # Validate review history consistency
            review_history = getattr(state, 'review_history', [])
            if review_history:
                for i, review in enumerate(review_history):
                    if not hasattr(review, 'student_review') or not review.student_review:
                        validation_errors.append(f"Review {i+1} has no content")
                    if not hasattr(review, 'iteration_number') or review.iteration_number <= 0:
                        validation_errors.append(f"Review {i+1} has invalid iteration number")
            
            # Log validation results
            if validation_errors:
                logger.error(f"State validation failed: {'; '.join(validation_errors)}")
                return False
            else:
                logger.debug("State validation passed for review processing")
                return True
            
        except Exception as e:
            logger.error(f"Error validating state for review: {str(e)}")
            return False
    
    @staticmethod
    def get_review_progress_info(state: WorkflowState) -> Dict[str, Any]:
        """
        HELPER: Get current review progress information with review_sufficient status.
        """
        try:
            current_iteration = getattr(state, "current_iteration", 1)
            max_iterations = getattr(state, "max_iterations", 3)
            review_history = getattr(state, "review_history", [])
            review_sufficient = getattr(state, "review_sufficient", False)
            pending_review = getattr(state, "pending_review", None)
            original_error_count = getattr(state, "original_error_count", 0)
            
            # Calculate progress
            progress_percentage = ((current_iteration - 1) / max_iterations) * 100
            
            # Get latest analysis if available
            latest_analysis = None
            accuracy_percentage = 0
            identified_count = 0
            
            if review_history and len(review_history) > 0:
                latest_review = review_history[-1]
                if hasattr(latest_review, 'analysis'):
                    latest_analysis = latest_review.analysis
                    identified_count = latest_analysis.get(t("identified_count"), 0)
                    total_problems = latest_analysis.get(t("total_problems"), original_error_count)
                    if total_problems > 0:
                        accuracy_percentage = (identified_count / total_problems) * 100
            
            progress_info = {
                "current_iteration": current_iteration,
                "max_iterations": max_iterations,
                "review_count": len(review_history),
                "review_sufficient": review_sufficient,
                "has_pending_review": bool(pending_review and pending_review.strip()),
                "progress_percentage": progress_percentage,
                "latest_analysis": latest_analysis,
                "can_continue": current_iteration <= max_iterations and not review_sufficient,
                "original_error_count": original_error_count,
                "identified_count": identified_count,
                "accuracy_percentage": accuracy_percentage
            }
            
            return progress_info
            
        except Exception as e:
            logger.error(f"Error getting review progress info: {str(e)}")
            return {
                "current_iteration": 1,
                "max_iterations": 3,
                "review_count": 0,
                "review_sufficient": False,
                "has_pending_review": False,
                "progress_percentage": 0,
                "latest_analysis": None,
                "can_continue": True,
                "error": str(e)
            }