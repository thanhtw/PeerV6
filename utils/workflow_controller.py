# utils/workflow_controller.py - FIXED: Review UI not showing issue

import streamlit as st
import logging
from typing import Dict, List, Tuple, Optional
from state_schema import WorkflowState
from utils.language_utils import t

logger = logging.getLogger(__name__)

class WorkflowController:
    """
    FIXED: Controls workflow progression and tab accessibility.
    Fixed issue where review UI wasn't showing in analyze_code_and_identify_errors step.
    """
    
    def __init__(self):
        self.workflow_steps = [
            "tutorial",      # 0 - Always accessible
            "generate",      # 1 - Code generation
            "review",        # 2 - Code review
            "feedback"       # 3 - Results and feedback
        ]
    
    
    def get_workflow_state_info(self) -> Dict:
        """
        FIXED: Get comprehensive workflow state information with improved code detection.
        """
        # Default state for new users
        default_state = {
            "current_phase": "initial",
            "accessible_tabs": [0, 1],  # Tutorial, Generate
            "blocked_tabs": [2, 3],     # Review, Feedback blocked
            "current_step": "generate",
            "progress_percentage": 0,
            "can_generate": True,
            "in_review": False,
            "review_complete": False,
            "has_code": False,
            "review_count": 0,
            "current_iteration": 1,
            "max_iterations": 3,
            "review_sufficient": False
        }
        
        # Check if we have workflow state
        if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
            logger.debug("No workflow state found, using default")
            return default_state
        
        state = st.session_state.workflow_state
        
        # FIXED: Improved code detection with multiple validation methods
        has_code = self._detect_code_presence(state)
        logger.debug(f"Code detection result: {has_code}")
        
        # FIXED: Enhanced review detection
        has_reviews = hasattr(state, 'review_history') and len(getattr(state, 'review_history', [])) > 0
        review_sufficient = getattr(state, 'review_sufficient', False)
        current_iteration = getattr(state, 'current_iteration', 1)
        max_iterations = getattr(state, 'max_iterations', 3)
        
        # FIXED: Check if we just completed generation (special state)
        generation_completed = st.session_state.get("generation_completed", False)
        
        logger.debug(f"Review state: has_reviews={has_reviews}, sufficient={review_sufficient}, iter={current_iteration}/{max_iterations}, gen_completed={generation_completed}")
        
        # FIXED: Improved phase determination
        if not has_code and not generation_completed:
            # Phase 1: Need to generate code
            current_phase = "generate"
            accessible_tabs = [0, 1]  # Tutorial, Generate
            blocked_tabs = [2, 3]     # Review, Feedback blocked
            can_generate = True
            in_review = False
            review_complete = False
            progress_percentage = 0
            
        elif (has_code or generation_completed) and (not review_sufficient and current_iteration <= max_iterations):
            # Phase 2: Code exists or just generated, in review process
            current_phase = "review"
            accessible_tabs = [0, 2]  # Tutorial, Review - Allow review when code exists
            blocked_tabs = [1, 3]     # Generate, Feedback blocked during review
            can_generate = False
            in_review = True
            review_complete = False
            progress_percentage = 25 + (current_iteration - 1) * 20
            
        elif review_sufficient or current_iteration > max_iterations:
            # Phase 3: Review complete
            current_phase = "complete"
            accessible_tabs = [0, 1, 3]  # Tutorial, Generate (new cycle), Feedback
            blocked_tabs = [2]           # Review blocked unless new cycle
            can_generate = True
            in_review = False
            review_complete = True
            progress_percentage = 100
            
        else:
            # Fallback: allow generation
            current_phase = "generate"
            accessible_tabs = [0, 1]
            blocked_tabs = [2, 3]
            can_generate = True
            in_review = False
            review_complete = False
            progress_percentage = 0
        
        result = {
            "current_phase": current_phase,
            "accessible_tabs": accessible_tabs,
            "blocked_tabs": blocked_tabs,
            "current_step": current_phase,
            "progress_percentage": progress_percentage,
            "can_generate": can_generate,
            "in_review": in_review,
            "review_complete": review_complete,
            "has_code": has_code,
            "review_count": len(getattr(state, 'review_history', [])),
            "current_iteration": current_iteration,
            "max_iterations": max_iterations,
            "review_sufficient": review_sufficient
        }
        
        logger.debug(f"Workflow state info: {result}")
        return result
    
    def _detect_code_presence(self, state) -> bool:
        """
        FIXED: More robust code presence detection with better validation.
        """
        try:
            # Method 1: Check generation_completed flag (most immediate)
            if st.session_state.get("generation_completed", False):
                logger.debug("Code detected via generation_completed flag")
                return True
            
            # Method 2: Check code_snippet attribute with thorough validation
            if hasattr(state, 'code_snippet') and state.code_snippet is not None:
                code_snippet = state.code_snippet
                
                # Check if code_snippet has actual code content
                if hasattr(code_snippet, 'code') and code_snippet.code:
                    if isinstance(code_snippet.code, str) and len(code_snippet.code.strip()) > 10:
                        logger.debug("Code detected via code_snippet.code")
                        return True
                
                # Check clean_code as backup
                if hasattr(code_snippet, 'clean_code') and code_snippet.clean_code:
                    if isinstance(code_snippet.clean_code, str) and len(code_snippet.clean_code.strip()) > 10:
                        logger.debug("Code detected via code_snippet.clean_code")
                        return True
                
                # Check if code_snippet is a string itself
                if isinstance(code_snippet, str) and len(code_snippet.strip()) > 10:
                    logger.debug("Code detected via code_snippet as string")
                    return True
                
                logger.debug("code_snippet exists but no valid code content found")
            
            # Method 3: Check if we're past generation step
            current_step = getattr(state, 'current_step', 'generate')
            if current_step in ['review', 'analyze', 'complete']:
                logger.debug(f"Code assumed present due to current_step: {current_step}")
                return True
            
            # Method 4: Check evaluation result exists (indicates code was generated)
            if hasattr(state, 'evaluation_result') and state.evaluation_result:
                logger.debug("Code detected via evaluation_result presence")
                return True
            
            # Method 5: Check if there's any review history (implies code existed)
            if hasattr(state, 'review_history') and len(getattr(state, 'review_history', [])) > 0:
                logger.debug("Code detected via review_history presence")
                return True
            
            logger.debug("No code detected via any method")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting code presence: {str(e)}")
            return False
    
    def validate_tab_access(self, tab_index: int) -> Tuple[bool, str]:
        """
        FIXED: Validate tab access with improved logic for code-ready state.
        """
        workflow_info = self.get_workflow_state_info()
        
        # Tutorial tab (0) is always accessible
        if tab_index == 0:
            return True, ""
        
        # Generate tab (1)
        if tab_index == 1:
            if workflow_info["in_review"] and not workflow_info["review_complete"]:
                return False, t("complete_current_review_first")
            else:
                return True, ""  # Allow generate when not in active review
                
        # Review tab (2) - FIXED: More permissive access
        elif tab_index == 2:
            if not workflow_info["has_code"] and not st.session_state.get("generation_completed", False):
                return False, t("generate_code_first")
            elif workflow_info["review_complete"]:
                return False, t("review_already_complete")
            else:
                return True, ""  # Allow review when code exists or just generated
                
        # Feedback tab (3)
        elif tab_index == 3:
            if not workflow_info["review_complete"]:
                return False, t("complete_review_first")
            else:
                return True, ""
        
        return True, ""
    
    def get_tab_state(self, tab_index: int) -> Dict:
        """Get the state information for a specific tab."""
        can_access, reason = self.validate_tab_access(tab_index)
        workflow_info = self.get_workflow_state_info()
        
        return {
            "can_access": can_access,
            "blocked_reason": reason,
            "is_current_step": workflow_info["current_step"] == self.workflow_steps[tab_index],
            "is_completed": self._is_tab_completed(tab_index, workflow_info)
        }
    
    def _is_tab_completed(self, tab_index: int, workflow_info: Dict) -> bool:
        """Check if a tab step is completed."""
        if tab_index == 1:  # Generate tab
            return workflow_info["has_code"]
        elif tab_index == 2:  # Review tab
            return workflow_info["review_complete"]
        elif tab_index == 3:  # Feedback tab
            return False  # Feedback is final step
        return False
    
    def handle_invalid_tab_access(self, attempted_tab: int, current_tab: int) -> int:
        """
        FIXED: Handle invalid tab access with better logic.
        """
        workflow_info = self.get_workflow_state_info()
        
        # FIXED: More permissive redirects
        if attempted_tab == 2 and workflow_info["has_code"]:
            # Allow review tab if code exists
            return 2
        elif attempted_tab == 1:
            # Allow generate tab unless in active review
            if not workflow_info["in_review"]:
                return 1
            else:
                st.warning(t("complete_current_review_first"))
                return 2  # Redirect to review
        elif attempted_tab == 3 and workflow_info["review_complete"]:
            # Allow feedback if review complete
            return 3
        
        # Redirect based on current phase
        if workflow_info["current_phase"] == "generate":
            return 1
        elif workflow_info["current_phase"] == "review":
            return 2
        elif workflow_info["current_phase"] == "complete":
            return 3
        else:
            return 0  # Tutorial
    
    def reset_workflow_for_new_cycle(self):
        """Reset workflow state to start a new code generation cycle."""
        if hasattr(st.session_state, 'workflow_state'):
            state = st.session_state.workflow_state
            # Reset for new cycle while preserving user settings
            state.code_snippet = None
            state.review_history = []
            state.current_iteration = 1
            state.review_sufficient = False
            state.evaluation_result = None
            state.comparison_report = None
            state.error = None
            state.current_step = "generate"
            
            # FIXED: Also clear generation flags
            if "generation_completed" in st.session_state:
                del st.session_state["generation_completed"]
            
            logger.info("Workflow reset for new generation cycle")
    
    def ensure_correct_tab_after_generation(self):
        """
        FIXED: Ensure the correct tab is active after code generation.
        """
        workflow_info = self.get_workflow_state_info()
        
        # If we just completed generation and we're not on review tab, switch to it
        if (workflow_info["has_code"] or st.session_state.get("generation_completed", False)) and not workflow_info["in_review"]:
            if st.session_state.get("active_tab", 0) != 2:
                logger.debug("Switching to review tab after code generation")
                st.session_state.active_tab = 2
                return True
        
        return False

    def render_workflow_progress_indicator(self):
        """FIXED: Render workflow progress with debug info."""
        workflow_info = self.get_workflow_state_info()
        
        # Add debug info in development
        if st.session_state.get("show_debug_workflow", False):
            with st.expander("🔧 Workflow Debug Info", expanded=False):
                st.json(workflow_info)
                if st.button("Hide Debug"):
                    st.session_state.show_debug_workflow = False
                    st.rerun()
        
        # Create progress steps
        steps = [
            {"name": t("generate_code"), "icon": "🔧", "step": "generate"},
            {"name": t("review_code"), "icon": "📋", "step": "review"}, 
            {"name": t("view_feedback"), "icon": "📊", "step": "complete"}
        ]
        
        # Determine step states
        current_phase = workflow_info["current_phase"]
        
        st.markdown("""
        <style>
        .workflow-progress {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1rem 0;
            padding: 1rem;
            background: linear-gradient(90deg, #f8f9fa, #e9ecef);
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        .progress-step {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0 1rem;
            padding: 0.5rem;
            border-radius: 8px;
            min-width: 80px;
            transition: all 0.3s ease;
        }
        .progress-step.active {
            background: #6f61c1;
            color: white !important;
            box-shadow: 0 2px 4px rgba(0,123,255,0.3);
        }
        .progress-step.completed {
            background: #28a745;
            color: white;
        }
        .progress-step.disabled {
            background: rgb(215 215 214 / 46%);
            color: #adb5bd;
        }
        .step-icon {
            font-size: 1.5rem;
            margin-bottom: 0.25rem;
        }
        .step-name {
            font-size: 0.8rem;
            text-align: center;
            font-weight: 500;
        }
        .step-connector {
            flex: 1;
            height: 2px;
            background: #dee2e6;
            margin: 0 0.5rem;
            align-self: center;
        }
        .step-connector.completed {
            background: #28a745;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Build progress HTML
        progress_html = '<div class="workflow-progress">'
        
        for i, step in enumerate(steps):
            # Determine step state
            if step["step"] == "generate":
                if workflow_info["has_code"]:
                    step_class = "completed"
                elif current_phase == "generate" or current_phase == "initial":
                    step_class = "active"
                else:
                    step_class = "disabled"
            elif step["step"] == "review":
                if workflow_info["review_complete"]:
                    step_class = "completed"
                elif current_phase == "review" or (workflow_info["has_code"] and not workflow_info["review_complete"]):
                    step_class = "active"
                else:
                    step_class = "disabled"
            elif step["step"] == "complete":
                if workflow_info["review_complete"]:
                    step_class = "active"
                else:
                    step_class = "disabled"
            else:
                step_class = "disabled"
            
            progress_html += f'''
            <div class="progress-step {step_class} progress-step-heigh">
                <div class="step-icon">{step["icon"]}</div>
                <div class="step-name">{step["name"]}</div>
            </div>
            '''
            
            # Add connector except for last step
            if i < len(steps) - 1:
                connector_class = "completed" if step_class == "completed" else ""
                progress_html += f'<div class="step-connector {connector_class}"></div>'
        
        progress_html += '</div>'
        
        st.markdown(progress_html, unsafe_allow_html=True)
        
        # Add phase description
        phase_descriptions = {
            "initial": t("start_by_generating_code"),
            "generate": t("configure_and_generate_java_code"),
            "review": t("analyze_code_and_identify_errors"),
            "complete": t("review_feedback_and_start_new_cycle")
        }
        
        description = phase_descriptions.get(current_phase, "")
        if description:
            st.info(f"📍 {description}")

    def force_tab_consistency_check(self):
        """
        Force a consistency check and correction of tab state.
        Call this when you suspect tab state might be incorrect.
        """
        try:
            from utils.session_state_manager import session_state_manager
            session_state_manager.ensure_tab_consistency()
            
            # Also trigger workflow state info refresh
            workflow_info = self.get_workflow_state_info()
            logger.debug(f"Forced consistency check - workflow info: {workflow_info}")
            
            return workflow_info
            
        except Exception as e:
            logger.error(f"Error in force consistency check: {str(e)}")
            return None
        
# Global instance
workflow_controller = WorkflowController()