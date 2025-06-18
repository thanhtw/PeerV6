"""
FIXED: Simplified Workflow Nodes for Java Peer Review Training System.

This module contains the node implementations with proper separation between
code generation and review phases, and clear review_sufficient logic.
FIXED: No code regeneration during review phase, only review analysis.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional

from state_schema import WorkflowState, CodeSnippet, ReviewAttempt
from utils.code_utils import extract_both_code_versions, create_regeneration_prompt
from utils.language_utils import t
import random

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowNodes:
    """
    FIXED: Node implementations for the Java Code Review workflow with clear phase separation.
    
    This class contains all node handlers with NO code regeneration during review phase
    and proper review_sufficient evaluation logic.
    """
    
    def __init__(self, code_generator, code_evaluation, error_repository, llm_logger):
        """
        Initialize workflow nodes with required components.
        
        Args:
            code_generator: Component for generating Java code with errors
            code_evaluation: Component for evaluating generated code quality
            error_repository: Repository for accessing Java error data
            llm_logger: Logger for tracking LLM interactions
        """
        self.code_generator = code_generator
        self.code_evaluation = code_evaluation
        self.error_repository = error_repository
        self.llm_logger = llm_logger
        # Initialize evaluator - this was missing
        self.evaluator = None

    def set_evaluator(self, evaluator):
        """Set the student evaluator component."""
        self.evaluator = evaluator

    # =================================================================
    # PHASE 1: CODE GENERATION AND EVALUATION NODES (UNCHANGED)
    # =================================================================
    
    def generate_code_node(self, state: WorkflowState) -> WorkflowState:
        """Generate Java code with errors based on selected parameters."""
        try:
            logger.debug("PHASE 1: Starting code generation")
            
            # Get parameters from state
            code_length = getattr(state, "code_length", "medium")
            difficulty_level = getattr(state, "difficulty_level", "medium")
            selected_error_categories = getattr(state, "selected_error_categories", {})
            selected_specific_errors = getattr(state, "selected_specific_errors", [])
            
            # Reset generation state for fresh start
            state.evaluation_attempts = 0
            state.evaluation_result = None
            state.code_generation_feedback = None

            # Set domain if not already set
            if not hasattr(state, "domain") or not state.domain:
                domains = [
                    "user_management", "file_processing", "data_validation", 
                    "calculation", "inventory_system", "notification_service",
                    "logging", "banking", "e-commerce", "student_management"
                ]
                state.domain = random.choice(domains)
                logger.debug(f"Selected domain: {state.domain}")
            
            # Determine error selection mode and get errors
            if selected_specific_errors:
                logger.debug(f"Using specific errors mode with {len(selected_specific_errors)} errors")
                selected_errors = selected_specific_errors
                original_error_count = len(selected_errors)
            else:
                if not selected_error_categories or not selected_error_categories.get("java_errors", []):
                    state.error = t("no_categories_selected")
                    return state
                
                # Get errors based on difficulty and count range
                error_count_start = int(getattr(state, "error_count_start", 1))
                error_count_end = int(getattr(state, "error_count_end", 2))
                required_error_count = random.randint(error_count_start, error_count_end)
            
                selected_errors, _ = self.error_repository.get_errors_for_llm(
                    selected_categories=selected_error_categories,
                    count=required_error_count,
                    difficulty=difficulty_level
                )

                original_error_count = len(selected_errors)
           
            logger.debug(f"Final error count for generation: {len(selected_errors)}")
            
            # Generate code with selected errors
            response = self.code_generator._generate_with_llm(
                code_length=code_length,
                difficulty_level=difficulty_level,
                selected_errors=selected_errors,
                domain=getattr(state, "domain", "")
            )

            # Extract both annotated and clean versions
            annotated_code, clean_code = extract_both_code_versions(response)
           
            # Validate code extraction
            if not annotated_code.strip() or not clean_code.strip():
                logger.error("Code generation failed: No code extracted from LLM response")
                state.error = "Failed to generate code. Please try again."
                return state

            # Create code snippet object
            code_snippet = CodeSnippet(
                code=annotated_code,
                clean_code=clean_code,
                raw_errors={"java_errors": selected_errors},
                expected_error_count=original_error_count
            )                  
            
            # Update state and proceed to evaluation
            state.original_error_count = original_error_count
            state.code_snippet = code_snippet
            state.current_step = "evaluate"
            
            logger.debug("PHASE 1: Code generation completed successfully")
            return state
                    
        except Exception as e:           
            logger.error(f"Error generating code: {str(e)}", exc_info=True)
            state.error = f"Error generating Java code: {str(e)}"
            return state

    def evaluate_code_node(self, state: WorkflowState) -> WorkflowState:
        """
        Evaluate generated code to check if it contains the required errors.
        """
        try:
            logger.debug("PHASE 1: Starting code evaluation")
            
            # Validate code snippet exists
            if not hasattr(state, 'code_snippet') or state.code_snippet is None:
                state.error = "No code snippet available for evaluation"
                return state
                    
            # Get the code with annotations
            code = state.code_snippet.code
            
            # Get requested errors from state
            requested_errors = self._extract_requested_errors(state)
            
            # Ensure we have errors to evaluate against
            if not requested_errors:
                logger.warning("No requested errors found, marking evaluation as valid")
                state.evaluation_result = {
                    t("found_errors"): [],
                    t("missing_errors"): [],
                    t("valid"): True,
                    t("feedback"): "No errors to evaluate against"
                }
                return state
            
            # Set up evaluation tracking
            original_error_count = getattr(state, "original_error_count", len(requested_errors))
            if original_error_count == 0:
                original_error_count = len(requested_errors)
                state.original_error_count = original_error_count
            
            # Ensure max_evaluation_attempts is set
            if not hasattr(state, 'max_evaluation_attempts'):
                state.max_evaluation_attempts = 3
                
            logger.debug(f"Evaluating code for {original_error_count} expected errors")
            
            # Initialize and increment attempts
            if not hasattr(state, 'evaluation_attempts'):
                state.evaluation_attempts = 0
            state.evaluation_attempts += 1
            
            logger.debug(f"Evaluation attempt {state.evaluation_attempts}/{state.max_evaluation_attempts}")
            
            # Perform the evaluation
            try:
                raw_evaluation_result = self.code_evaluation.evaluate_code(code, requested_errors)
            except Exception as eval_error:
                logger.error(f"Code evaluation failed: {str(eval_error)}")
                raw_evaluation_result = {
                    t("found_errors"): [],
                    t("missing_errors"): [f"EVALUATION_ERROR - {str(eval_error)}"],
                    t("valid"): False,
                    t("feedback"): f"Evaluation failed: {str(eval_error)}"
                }
            
            # Process and validate evaluation result
            evaluation_result = self._process_evaluation_result(
                raw_evaluation_result, requested_errors, original_error_count
            )
            
            # Update state with evaluation results
            state.evaluation_result = evaluation_result
            
            # Generate feedback for potential regeneration if needed
            missing_count = len(evaluation_result.get(t('missing_errors'), []))
            
            if missing_count > 0 and state.evaluation_attempts < state.max_evaluation_attempts:
                logger.debug(f"Missing {missing_count} out of {original_error_count} requested errors")
                
                try:
                    if hasattr(self.code_evaluation, 'generate_improved_prompt'):
                        feedback = self.code_evaluation.generate_improved_prompt(
                            code, requested_errors, evaluation_result
                        )
                    else:
                        feedback = create_regeneration_prompt(
                            code=code,
                            domain=getattr(state, "domain", ""),
                            missing_errors=evaluation_result.get(t('missing_errors'), []),
                            found_errors=evaluation_result.get(t('found_errors'), []), 
                            requested_errors=requested_errors
                        )
                    state.code_generation_feedback = feedback
                except Exception as feedback_error:
                    logger.error(f"Failed to generate feedback: {str(feedback_error)}")
                    state.code_generation_feedback = None
            else:
                if missing_count > 0:
                    logger.warning(f"Still missing {missing_count} errors but reached max attempts")
                else:
                    logger.debug(f"All {original_error_count} requested errors implemented correctly")
                state.code_generation_feedback = None

            logger.debug(f"PHASE 1: Evaluation complete. Valid: {evaluation_result.get(t('valid'), False)}")
            return state
            
        except Exception as e:
            logger.error(f"Error in evaluation: {str(e)}", exc_info=True)
            state.error = f"Error evaluating code: {str(e)}"
            return state

    def regenerate_code_node(self, state: WorkflowState) -> WorkflowState:
        """Regenerate code based on evaluation feedback."""
        try:
            current_attempt = getattr(state, 'evaluation_attempts', 0)
            max_attempts = getattr(state, "max_evaluation_attempts", 3)
            
            logger.debug(f"PHASE 1: Starting code regeneration (attempt {current_attempt}/{max_attempts})")
            
            # Check max attempts (should not happen due to conditions, but safety check)
            if current_attempt >= max_attempts:
                logger.warning(f"Max attempts ({max_attempts}) reached. Skipping regeneration.")
                return state
            
            # Use the code generation feedback to generate improved code
            feedback_prompt = getattr(state, "code_generation_feedback", None)
            
            if not feedback_prompt:
                logger.warning("No feedback prompt available for regeneration.")
                return state
            
            if hasattr(self.code_generator, 'llm') and self.code_generator.llm:
                try:
                    # Generate improved code
                    response = self.code_generator.llm.invoke(feedback_prompt)
                    
                    # Log the regeneration
                    metadata = {
                        "attempt_after_evaluation": current_attempt,
                        "max_attempts": max_attempts
                    }
                    self.llm_logger.log_code_regeneration(feedback_prompt, response, metadata)
                    
                    # Process the response
                    annotated_code, clean_code = extract_both_code_versions(response)                
                    
                    # Get requested errors from state
                    requested_errors = self._extract_requested_errors(state)
                    
                    # Create updated code snippet
                    state.code_snippet = CodeSnippet(
                        code=annotated_code,
                        clean_code=clean_code,
                        raw_errors={"java_errors": requested_errors}
                    )
                    
                    logger.debug(f"PHASE 1: Code regenerated successfully for attempt {current_attempt + 1}")
                    
                except Exception as regen_error:
                    logger.error(f"Failed to regenerate code: {str(regen_error)}")
                    
                return state
            else:
                logger.warning("No LLM available for regeneration.")
                return state
            
        except Exception as e:                 
            logger.error(f"Error regenerating code: {str(e)}", exc_info=True)
            logger.warning("Regeneration failed, continuing with existing code")
            return state

    # =================================================================
    # PHASE 2: REVIEW PROCESSING NODES (FIXED - NO CODE REGENERATION)
    # =================================================================
    
    def process_review_node(self, state: WorkflowState) -> WorkflowState:
        """
        FIXED: Process submitted review - ONLY handles review, NO code regeneration.
        """
        try:
            pending_review = getattr(state, "pending_review", None)
            current_iteration = getattr(state, "current_iteration", 1)
            
            logger.debug(f"PHASE 2: Processing review submission for iteration {current_iteration}")
            
            # Validate we have a pending review
            if not pending_review or not pending_review.strip():
                state.error = "No pending review to process"
                logger.error("process_review_node: No pending review found")
                return state
            
            review_text = pending_review.strip()
            
            # Ensure review_history exists
            if not hasattr(state, 'review_history'):
                state.review_history = []
            
            # Check if this review already exists for current iteration
            needs_new_entry = True
            for review in state.review_history:
                if review.iteration_number == current_iteration:
                    # Update existing entry instead of creating new one
                    review.student_review = review_text
                    needs_new_entry = False
                    logger.debug(f"Updated existing review for iteration {current_iteration}")
                    break
            
            if needs_new_entry:
                # Create new review entry
                review_attempt = ReviewAttempt(
                    student_review=review_text,
                    iteration_number=current_iteration,
                    analysis={},
                    targeted_guidance=None
                )
                state.review_history.append(review_attempt)
                logger.debug(f"Created new review entry for iteration {current_iteration}")
            
            # Clear pending review
            state.pending_review = None
            
            # Set current step for analysis
            state.current_step = "analyze"
            
            logger.debug("PHASE 2: Review processing completed, proceeding to analysis")
            return state
                
        except Exception as e:
            logger.error(f"Error in process_review_node: {str(e)}")
            state.error = f"Error processing review: {str(e)}"
            return state
    
    def analyze_review_node(self, state: WorkflowState) -> WorkflowState:
        """
        FIXED: Analyze student review with proper review_sufficient evaluation.
        """
        try:
            logger.debug("PHASE 2: Starting review analysis")
            
            # Validate we have review history
            if not hasattr(state, 'review_history') or not state.review_history:
                state.error = "No review history for analysis"
                logger.error("analyze_review_node: No review history found")
                return state
            
            # Get the latest review
            latest_review = state.review_history[-1]
            student_review = latest_review.student_review
            current_iteration = getattr(state, 'current_iteration', 1)
            
            logger.debug(f"analyze_review_node: Analyzing review for iteration {current_iteration}")
            
            # Validate code snippet exists
            if not hasattr(state, 'code_snippet') or not state.code_snippet:
                state.error = "No code snippet for analysis"
                return state
            
            # Extract known problems for analysis
            known_problems = self._extract_known_problems_for_analysis(state)
            
            # Check evaluator is available
            if not self.evaluator:
                logger.error("Student evaluator not initialized")
                state.error = "Student evaluator not initialized"
                return state
            
            # Perform the analysis
            try:
                analysis = self.evaluator.evaluate_review(
                    code_snippet=state.code_snippet.code,
                    known_problems=known_problems,
                    student_review=student_review
                )
                
                if not analysis:
                    raise ValueError("Evaluator returned empty analysis")
                
                logger.debug(f"analyze_review_node: Analysis completed successfully")
                
            except Exception as eval_error:
                logger.error(f"Review evaluation failed: {str(eval_error)}")
                # Create fallback analysis
                original_error_count = getattr(state, 'original_error_count', 1)
                analysis = {
                    t("identified_count"): 0,
                    t("total_problems"): original_error_count,
                    t("identified_percentage"): 0,
                    t("review_sufficient"): False,
                    t("error"): f"Evaluation failed: {str(eval_error)}"
                }
            
            # FIXED: Update analysis with proper metrics and review_sufficient evaluation
            original_error_count = getattr(state, 'original_error_count', 1)
            identified_count = analysis.get(t('identified_count'), 0)
            
            # Ensure counts are reasonable
            if identified_count > original_error_count:
                identified_count = original_error_count
                analysis[t('identified_count')] = identified_count
            
            analysis[t('total_problems')] = original_error_count
            analysis[t('identified_percentage')] = (identified_count / original_error_count) * 100 if original_error_count > 0 else 0
            analysis[t('accuracy_percentage')] = analysis[t('identified_percentage')]
            
            # FIXED: Evaluate review sufficiency using clear criteria
            from workflow.conditions import WorkflowConditions
            is_sufficient = WorkflowConditions.evaluate_review_sufficiency(state, analysis)
            print(f"\nReview sufficiency evaluated as: {is_sufficient}")
            analysis[t('review_sufficient')] = is_sufficient
            state.review_sufficient = is_sufficient
            
            if is_sufficient:
                logger.debug(f"REVIEW: Marked as sufficient - {identified_count}/{original_error_count} errors found")
            else:
                logger.debug(f"REVIEW: Not sufficient - {identified_count}/{original_error_count} errors found")
            
            # Update the review with analysis
            latest_review.analysis = analysis
            
            # Increment iteration for next review (if needed)
            max_iterations = getattr(state, 'max_iterations', 3)
            if not state.review_sufficient and current_iteration < max_iterations:
                state.current_iteration = current_iteration + 1
                logger.debug(f"analyze_review_node: Incremented to iteration {state.current_iteration}")
            
            # Generate guidance if needed (only if review not sufficient and more iterations allowed)
            if not state.review_sufficient and state.current_iteration <= max_iterations:
                try:
                    if self.evaluator and hasattr(self.evaluator, 'generate_targeted_guidance'):
                        guidance = self.evaluator.generate_targeted_guidance(
                            code_snippet=state.code_snippet.code,
                            known_problems=known_problems,
                            student_review=student_review,
                            review_analysis=analysis,
                            iteration_count=current_iteration,
                            max_iterations=max_iterations
                        )
                        latest_review.targeted_guidance = guidance
                        logger.debug("analyze_review_node: Generated targeted guidance")
                    else:
                        logger.warning("Evaluator does not have generate_targeted_guidance method")
                        latest_review.targeted_guidance = None
                except Exception as guidance_error:
                    logger.error(f"Failed to generate guidance: {str(guidance_error)}")
                    latest_review.targeted_guidance = None
            
            logger.debug(f"PHASE 2: Analysis completed successfully. Sufficient: {state.review_sufficient}")
            return state
            
        except Exception as e:
            logger.error(f"Error in analyze_review_node: {str(e)}")
            state.error = f"Error analyzing review: {str(e)}"
            return state

    # =================================================================
    # PHASE 3: FINAL REPORT GENERATION (UNCHANGED)
    # =================================================================

    def generate_comparison_report_node(self, state: WorkflowState) -> WorkflowState:
        """Enhanced comparison report node with badge processing."""
        try:
            logger.debug("PHASE 3: Generating comparison report with badge processing")
            
            # Check if we have review history
            if not hasattr(state, 'review_history') or not state.review_history:
                logger.warning("No review history found")
                state.comparison_report = None
                state.current_step = "complete"
                return state
                    
            # Get latest review
            latest_review = state.review_history[-1]
            
            # Generate comparison report if not already generated
            if not hasattr(state, 'comparison_report') or not state.comparison_report:
                if hasattr(state, 'evaluation_result') and state.evaluation_result:
                    found_errors = state.evaluation_result.get(t('found_errors'), [])
                    
                    converted_history = []
                    for review in state.review_history:
                        converted_history.append({
                            "iteration_number": review.iteration_number,
                            "student_comment": review.student_review,
                            "review_analysis": review.analysis,
                            "targeted_guidance": getattr(review, 'targeted_guidance', None)
                        })
                            
                    if hasattr(self, "evaluator") and self.evaluator:
                        try:
                            state.comparison_report = self.evaluator.generate_comparison_report(
                                found_errors,
                                latest_review.analysis,
                                converted_history
                            )
                            logger.debug("PHASE 3: Generated comparison report successfully")
                        except Exception as report_error:
                            logger.error(f"Failed to generate comparison report: {str(report_error)}")
                            state.comparison_report = None
            
            # === NEW: BADGE PROCESSING ===
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and 'auth' in st.session_state:
                    user_id = st.session_state.auth.get('user_id')
                    
                    if user_id and user_id != 'demo_user':
                        from workflow.badge_integration import WorkflowBadgeIntegrator
                        
                        badge_integrator = WorkflowBadgeIntegrator()
                        badge_result = badge_integrator.process_review_completion_with_badges(
                            state, user_id
                        )
                        
                        if badge_result.get('success'):
                            state.badge_awards = {
                                'awarded_badges': badge_result.get('awarded_badges', []),
                                'points_awarded': badge_result.get('points_awarded', 0),
                                'total_badges_awarded': badge_result.get('total_badges_awarded', 0)
                            }
                            logger.info(f"Badge processing completed: {badge_result.get('total_badges_awarded', 0)} badges awarded")
            except Exception as badge_error:
                logger.error(f"Error in badge processing: {str(badge_error)}")
            # === END BADGE PROCESSING ===
            
            # Update state to complete
            state.current_step = "complete"
            
            logger.debug("PHASE 3: Comparison report generation completed")
            return state
            
        except Exception as e:
            logger.error(f"Error generating comparison report: {str(e)}", exc_info=True)
            state.error = f"Error generating comparison report: {str(e)}"
            return state

    # =================================================================
    # HELPER METHODS (UNCHANGED)
    # =================================================================

    def _extract_known_problems_for_analysis(self, state: WorkflowState) -> List[str]:
        """Helper to extract known problems from state."""
        known_problems = []
        
        try:
            if hasattr(state, 'code_snippet') and state.code_snippet:
                raw_errors = state.code_snippet.raw_errors
                
                if isinstance(raw_errors, dict) and "java_errors" in raw_errors:
                    for error in raw_errors["java_errors"]:
                        if isinstance(error, dict):
                            error_name = error.get(t('error_name'), error.get('name', ''))
                            category = error.get(t('category'), error.get('type', ''))
                            description = error.get(t('description'), '')
                            known_problems.append(f"{category} - {error_name}: {description}")
            
            logger.debug(f"Extracted {len(known_problems)} known problems for analysis")
            
        except Exception as e:
            logger.error(f"Error extracting known problems: {str(e)}")
        
        return known_problems

    def _process_evaluation_result(self, raw_result, requested_errors, original_error_count):
        """
        Process and validate evaluation result to ensure it's in the correct format.
        """
        try:
            if not isinstance(raw_result, dict):
                logger.error(f"Expected dict for evaluation_result, got {type(raw_result)}")
                evaluation_result = {
                    t("found_errors"): [],
                    t("missing_errors"): [f"{error.get('type', '').upper()} - {error.get('name', '')}" 
                                    for error in requested_errors],
                    t("valid"): False,
                    t("feedback"): f"Invalid evaluation result type: {type(raw_result)}",
                    t("original_error_count"): original_error_count
                }
            else:
                evaluation_result = raw_result.copy()
                evaluation_result[t("original_error_count")] = original_error_count

                # Ensure required fields exist
                if t("found_errors") not in evaluation_result:
                    evaluation_result[t("found_errors")] = []
                if t("missing_errors") not in evaluation_result:
                    evaluation_result[t("missing_errors")] = []
                
                # Ensure fields are lists
                if not isinstance(evaluation_result.get(t("found_errors")), list):
                    evaluation_result[t("found_errors")] = []
                if not isinstance(evaluation_result.get(t("missing_errors")), list):
                    evaluation_result[t("missing_errors")] = []
                
                # Set validity based on missing errors
                missing_errors = evaluation_result.get(t('missing_errors'), [])
                evaluation_result[t('valid')] = len(missing_errors) == 0
                
                logger.debug(f"Processed evaluation: found={len(evaluation_result.get(t('found_errors'), []))}, "
                            f"missing={len(missing_errors)}, valid={evaluation_result[t('valid')]}")
                
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error processing evaluation result: {str(e)}")
            # Return a safe fallback
            return {
                t("found_errors"): [],
                t("missing_errors"): [f"PROCESSING_ERROR - {str(e)}"],
                t("valid"): False,
                t("feedback"): f"Error processing evaluation: {str(e)}",
                t("original_error_count"): original_error_count
            }

    def _extract_requested_errors(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """Extract requested errors from the state."""
        requested_errors = []
        
        if not hasattr(state, 'code_snippet') or state.code_snippet is None:
            logger.warning("No code snippet in state for extracting requested errors")
            return requested_errors
        
        if hasattr(state, 'code_snippet') and hasattr(state.code_snippet, "raw_errors"):
            raw_errors = state.code_snippet.raw_errors           
            
            if not isinstance(raw_errors, dict):
                logger.warning(f"Expected dict for raw_errors, got {type(raw_errors)}")
                return requested_errors
            
            if "java_errors" in raw_errors:
                errors = raw_errors.get("java_errors", [])
                if not isinstance(errors, list):
                    logger.warning(f"Expected list for java_errors, got {type(errors)}")
                    return requested_errors
                
                for error in errors:
                    if not isinstance(error, dict):
                        logger.warning(f"Expected dict for error, got {type(error)}")
                        continue
                    requested_errors.append(error)
        
        elif hasattr(state, 'selected_specific_errors') and state.selected_specific_errors:
            if isinstance(state.selected_specific_errors, list):
                for error in state.selected_specific_errors:
                    if isinstance(error, dict):
                        requested_errors.append(error)
        
        logger.debug(f"Extracted {len(requested_errors)} requested errors")
        return requested_errors