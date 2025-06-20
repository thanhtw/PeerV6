# utils/session_state_manager.py - UPDATED: Enhanced for unified practice tab

import streamlit as st
import logging
import time
import uuid
from typing import Any, Dict, Optional, Callable
from state_schema import WorkflowState
from utils.language_utils import t

logger = logging.getLogger(__name__)

class SessionStateManager:
    """
    Enhanced session state manager for unified practice workflow.
    Handles workflow phase consistency and prevents data loss during transitions.
    """
    
    def __init__(self):
        self.state_lock_timeout = 5.0  # 5 seconds timeout for state locks
        self.session_id = self._get_or_create_session_id()
    
    def _get_or_create_session_id(self) -> str:
        """Get or create a unique session ID."""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())[:8]
        return st.session_state.session_id
    
    def acquire_state_lock(self, operation_name: str) -> bool:
        """
        Acquire a state lock to prevent concurrent operations.
        
        Args:
            operation_name: Name of the operation requiring the lock
            
        Returns:
            True if lock acquired, False otherwise
        """
        lock_key = f"state_lock_{operation_name}"
        current_time = time.time()
        
        # Check if lock exists and is still valid
        if lock_key in st.session_state:
            lock_time = st.session_state[lock_key]
            if current_time - lock_time < self.state_lock_timeout:
                logger.debug(f"State lock '{operation_name}' is still active")
                return False
            else:
                # Lock expired, remove it
                del st.session_state[lock_key]
        
        # Acquire lock
        st.session_state[lock_key] = current_time
        logger.debug(f"Acquired state lock '{operation_name}'")
        return True
    
    def release_state_lock(self, operation_name: str) -> None:
        """Release a state lock."""
        lock_key = f"state_lock_{operation_name}"
        if lock_key in st.session_state:
            del st.session_state[lock_key]
            logger.debug(f"Released state lock '{operation_name}'")
    
    def is_operation_in_progress(self, operation_name: str) -> bool:
        """Check if an operation is currently in progress."""
        lock_key = f"state_lock_{operation_name}"
        if lock_key in st.session_state:
            lock_time = st.session_state[lock_key]
            current_time = time.time()
            return current_time - lock_time < self.state_lock_timeout
        return False
    
    def safe_workflow_state_update(self, update_func: Callable[[WorkflowState], WorkflowState]) -> bool:
        """
        Safely update workflow state with conflict prevention.
        
        Args:
            update_func: Function that takes current state and returns updated state
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.acquire_state_lock("workflow_update"):
            logger.warning("Could not acquire workflow update lock")
            return False
        
        try:
            current_state = st.session_state.get('workflow_state')
            if current_state is None:
                current_state = WorkflowState()
            
            # Apply update
            updated_state = update_func(current_state)
            
            # Validate update
            if self._validate_workflow_state_update(current_state, updated_state):
                st.session_state.workflow_state = updated_state
                logger.debug("Workflow state updated successfully")
                return True
            else:
                logger.error("Workflow state update validation failed")
                return False
                
        except Exception as e:
            logger.error(f"Error updating workflow state: {str(e)}")
            return False
        finally:
            self.release_state_lock("workflow_update")
    
    def _validate_workflow_state_update(self, old_state: WorkflowState, new_state: WorkflowState) -> bool:
        """Validate that workflow state update is consistent."""
        try:
            # Check that iteration doesn't go backwards
            old_iteration = getattr(old_state, 'current_iteration', 1)
            new_iteration = getattr(new_state, 'current_iteration', 1)
            
            if new_iteration < old_iteration:
                logger.warning(f"Iteration going backwards: {old_iteration} -> {new_iteration}")
                return False
            
            # Check that review history doesn't shrink
            old_history_len = len(getattr(old_state, 'review_history', []))
            new_history_len = len(getattr(new_state, 'review_history', []))
            
            if new_history_len < old_history_len:
                logger.warning(f"Review history shrinking: {old_history_len} -> {new_history_len}")
                return False
            
            # Check that code doesn't disappear unexpectedly
            old_has_code = hasattr(old_state, 'code_snippet') and old_state.code_snippet is not None
            new_has_code = hasattr(new_state, 'code_snippet') and new_state.code_snippet is not None
            
            if old_has_code and not new_has_code:
                logger.warning("Code snippet disappeared during update")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating workflow state update: {str(e)}")
            return False
    
    def safe_review_submission(self, review_text: str, iteration: int, 
                             callback: Callable[[str], Any]) -> tuple[bool, Any]:
        """
        Safely handle review submission with duplicate prevention.
        
        Args:
            review_text: The review text to submit
            iteration: Current iteration number
            callback: Callback function to handle the submission
            
        Returns:
            Tuple of (success, result)
        """
        submission_key = f"review_submission_{iteration}"
        
        if not self.acquire_state_lock(submission_key):
            logger.warning(f"Review submission already in progress for iteration {iteration}")
            return False, "Submission already in progress"
        
        try:
            # Check for duplicate submission
            last_submission_key = f"last_review_submission_{iteration}"
            last_submission = st.session_state.get(last_submission_key)
            
            if last_submission and last_submission.get('text') == review_text:
                submission_time = last_submission.get('timestamp', 0)
                current_time = time.time()
                
                # If same review was submitted within last 10 seconds, consider it duplicate
                if current_time - submission_time < 10:
                    logger.warning(f"Duplicate review submission detected for iteration {iteration}")
                    return False, "Duplicate submission detected"
            
            # Record this submission
            st.session_state[last_submission_key] = {
                'text': review_text,
                'timestamp': time.time(),
                'iteration': iteration
            }
            
            # Execute callback
            logger.debug(f"Executing review submission callback for iteration {iteration}")
            result = callback(review_text)
            
            # Mark submission as completed
            completion_key = f"review_completed_{iteration}"
            st.session_state[completion_key] = {
                'timestamp': time.time(),
                'success': result is not False
            }
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error in safe review submission: {str(e)}")
            return False, str(e)
        finally:
            self.release_state_lock(submission_key)
    
    def prevent_code_regeneration_on_rerun(self) -> bool:
        """
        Prevent unnecessary code regeneration during reruns.
        
        Returns:
            True if code regeneration should be prevented, False otherwise
        """
        # Check if code was recently generated
        last_generation_key = "last_code_generation"
        last_generation = st.session_state.get(last_generation_key)
        
        if last_generation:
            generation_time = last_generation.get('timestamp', 0)
            current_time = time.time()
            
            # If code was generated within last 30 seconds, prevent regeneration
            if current_time - generation_time < 30:
                logger.debug("Preventing code regeneration - recent generation detected")
                return True
        
        # Check if we're in review phase
        workflow_phase = st.session_state.get('workflow_phase', 'generate')
        if workflow_phase == 'review':
            workflow_state = st.session_state.get('workflow_state')
            if workflow_state and hasattr(workflow_state, 'code_snippet') and workflow_state.code_snippet:
                logger.debug("Preventing code regeneration - already in review phase with code")
                return True
            
            # Check if we have review history
            if workflow_state and hasattr(workflow_state, 'review_history'):
                review_history = getattr(workflow_state, 'review_history', [])
                if review_history:
                    logger.debug("Preventing code regeneration - review history exists")
                    return True
        
        return False
    
    def mark_code_generation(self, code_snippet: Any) -> None:
        """Mark that code generation occurred."""
        last_generation_key = "last_code_generation"
        st.session_state[last_generation_key] = {
            'timestamp': time.time(),
            'has_code': code_snippet is not None,
            'session_id': self.session_id
        }
        logger.debug("Marked code generation timestamp")
    
    def cleanup_expired_locks(self) -> None:
        """Clean up expired state locks."""
        current_time = time.time()
        expired_keys = []
        
        for key in st.session_state.keys():
            if key.startswith('state_lock_'):
                lock_time = st.session_state.get(key, 0)
                if current_time - lock_time > self.state_lock_timeout:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del st.session_state[key]
            logger.debug(f"Cleaned up expired lock: {key}")
    
    def get_workflow_state_safely(self) -> Optional[WorkflowState]:
        """Get workflow state with safety checks."""
        try:
            workflow_state = st.session_state.get('workflow_state')
            if workflow_state is None:
                logger.debug("No workflow state found, creating new one")
                workflow_state = WorkflowState()
                st.session_state.workflow_state = workflow_state
            
            return workflow_state
        except Exception as e:
            logger.error(f"Error getting workflow state: {str(e)}")
            # Return a new state as fallback
            return WorkflowState()
    
    def handle_phase_transition(self, from_phase: str, to_phase: str) -> bool:
        """
        Handle transition between workflow phases in unified practice tab.
        
        Args:
            from_phase: Current phase
            to_phase: Target phase
            
        Returns:
            True if transition was handled, False otherwise
        """
        try:
            logger.debug(f"Handling phase transition: {from_phase} -> {to_phase}")
            
            # Validate transition
            if not self._validate_phase_transition(from_phase, to_phase):
                logger.warning(f"Invalid phase transition: {from_phase} -> {to_phase}")
                return False
            
            # Update workflow phase
            st.session_state.workflow_phase = to_phase
            
            # Mark transition timestamp
            transition_key = f"phase_transition_{to_phase}"
            st.session_state[transition_key] = {
                'timestamp': time.time(),
                'from_phase': from_phase,
                'session_id': self.session_id
            }
            
            logger.debug(f"Successfully transitioned to phase: {to_phase}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling phase transition: {str(e)}")
            return False
    
    def _validate_phase_transition(self, from_phase: str, to_phase: str) -> bool:
        """Validate that a phase transition is allowed."""
        try:
            workflow_state = st.session_state.get('workflow_state')
            
            # Allow backward transitions (user can always go back)
            valid_phases = ["generate", "review", "feedback"]
            if to_phase not in valid_phases:
                return False
            
            # Allow transition to generate from any phase (restart)
            if to_phase == "generate":
                return True
            
            # Transition to review requires code
            if to_phase == "review":
                if workflow_state and hasattr(workflow_state, 'code_snippet'):
                    return workflow_state.code_snippet is not None
                return st.session_state.get("generation_completed", False)
            
            # Transition to feedback requires completed review
            if to_phase == "feedback":
                if workflow_state:
                    review_sufficient = getattr(workflow_state, 'review_sufficient', False)
                    current_iteration = getattr(workflow_state, 'current_iteration', 1)
                    max_iterations = getattr(workflow_state, 'max_iterations', 3)
                    return review_sufficient or current_iteration > max_iterations
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating phase transition: {str(e)}")
            return False
    
    def ensure_phase_consistency(self) -> None:
        """
        Ensure workflow phase is consistent with workflow state.
        """
        try:
            workflow_state = st.session_state.get('workflow_state')
            current_phase = st.session_state.get('workflow_phase', 'generate')
            
            if workflow_state:
                # Check if current phase makes sense given workflow state
                has_code = hasattr(workflow_state, 'code_snippet') and workflow_state.code_snippet is not None
                has_reviews = hasattr(workflow_state, 'review_history') and len(getattr(workflow_state, 'review_history', [])) > 0
                review_complete = getattr(workflow_state, 'review_sufficient', False)
                current_iteration = getattr(workflow_state, 'current_iteration', 1)
                max_iterations = getattr(workflow_state, 'max_iterations', 3)
                
                # Auto-correct phase if needed
                if has_code and not has_reviews and current_phase == "generate":
                    # Have code but no reviews, should advance to review
                    logger.debug("Auto-advancing to review phase - have code but no reviews")
                    st.session_state.workflow_phase = "review"
                    
                elif (review_complete or current_iteration > max_iterations) and current_phase != "feedback":
                    # Review complete, should advance to feedback
                    logger.debug("Auto-advancing to feedback phase - review complete")
                    st.session_state.workflow_phase = "feedback"
                    
                elif not has_code and current_phase in ["review", "feedback"]:
                    # No code but in advanced phase, go back to generate
                    logger.debug("Auto-correcting to generate phase - no code available")
                    st.session_state.workflow_phase = "generate"
            
        except Exception as e:
            logger.error(f"Error ensuring phase consistency: {str(e)}")
    
    def add_scroll_to_top_script(self) -> None:
        """Add JavaScript to scroll to top of page."""
        st.markdown("""
        <script>
        // Smooth scroll to top
        function scrollToTop() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }
        
        // Auto scroll to top on page load/rerun
        window.addEventListener('load', function() {
            setTimeout(scrollToTop, 100);
        });
        
        // Also trigger immediately
        scrollToTop();
        </script>
        """, unsafe_allow_html=True)
    
    def debug_session_state(self) -> Dict[str, Any]:
        """Get debug information about current session state."""
        try:
            debug_info = {
                'session_id': self.session_id,
                'total_keys': len(st.session_state.keys()),
                'workflow_state_exists': 'workflow_state' in st.session_state,
                'workflow_phase': st.session_state.get('workflow_phase', 'unknown'),
                'active_locks': [k for k in st.session_state.keys() if k.startswith('state_lock_')],
                'review_submissions': [k for k in st.session_state.keys() if 'review_submission' in k],
                'code_generations': [k for k in st.session_state.keys() if 'code_generation' in k],
                'phase_transitions': [k for k in st.session_state.keys() if 'phase_transition' in k]
            }
            
            if 'workflow_state' in st.session_state:
                workflow_state = st.session_state.workflow_state
                debug_info.update({
                    'workflow_step': getattr(workflow_state, 'current_step', 'unknown'),
                    'current_iteration': getattr(workflow_state, 'current_iteration', 0),
                    'has_code_snippet': hasattr(workflow_state, 'code_snippet') and workflow_state.code_snippet is not None,
                    'review_history_count': len(getattr(workflow_state, 'review_history', []))
                })
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Error getting debug info: {str(e)}")
            return {'error': str(e)}

# Global instance
session_state_manager = SessionStateManager()