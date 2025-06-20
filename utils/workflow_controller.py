# utils/workflow_controller.py - UPDATED: Simplified for unified practice tab

import streamlit as st
import logging
from typing import Dict, List, Tuple, Optional
from state_schema import WorkflowState
from utils.language_utils import t

logger = logging.getLogger(__name__)

class WorkflowController:
    """
    UPDATED: Simplified workflow controller for unified practice tab.
    Manages workflow phases instead of separate tabs.
    """
    
    def __init__(self):
        self.workflow_phases = [
            "generate",      # Code generation phase
            "review",        # Code review phase
            "feedback"       # Results and feedback phase
        ]
    
    def get_workflow_state_info(self) -> Dict:
        """
        Get comprehensive workflow state information for unified practice flow.
        """
        # Default state for new users
        default_state = {
            "current_phase": "generate",
            "progress_percentage": 0,
            "can_generate": True,
            "in_review": False,
            "review_complete": False,
            "has_code": False,
            "review_count": 0,
            "current_iteration": 1,
            "max_iterations": 3,
            "review_sufficient": False,
            "phase_status": {
                "generate": "pending",
                "review": "locked",
                "feedback": "locked"
            }
        }
        
        # Check if we have workflow state
        if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
            logger.debug("No workflow state found, using default")
            return default_state
        
        state = st.session_state.workflow_state
        
        # Detect code presence
        has_code = self._detect_code_presence(state)
        logger.debug(f"Code detection result: {has_code}")
        
        # Enhanced review detection
        has_reviews = hasattr(state, 'review_history') and len(getattr(state, 'review_history', [])) > 0
        review_sufficient = getattr(state, 'review_sufficient', False)
        current_iteration = getattr(state, 'current_iteration', 1)
        max_iterations = getattr(state, 'max_iterations', 3)
        
        # Check if we just completed generation
        generation_completed = st.session_state.get("generation_completed", False)
        
        logger.debug(f"Review state: has_reviews={has_reviews}, sufficient={review_sufficient}, iter={current_iteration}/{max_iterations}, gen_completed={generation_completed}")
        
        # Determine workflow phases and progress
        phase_status = {}
        
        # Phase 1: Generate
        if has_code or generation_completed:
            phase_status["generate"] = "completed"
            can_generate = True  # Can regenerate
            progress = 33
        else:
            phase_status["generate"] = "active"
            can_generate = True
            progress = 10
        
        # Phase 2: Review
        if not has_code and not generation_completed:
            phase_status["review"] = "locked"
            in_review = False
        elif review_sufficient or current_iteration > max_iterations:
            phase_status["review"] = "completed"
            in_review = False
            progress = 66
        else:
            phase_status["review"] = "active"
            in_review = True
            progress = 33 + (current_iteration - 1) * 10
        
        # Phase 3: Feedback
        if review_sufficient or current_iteration > max_iterations:
            phase_status["feedback"] = "active"
            review_complete = True
            progress = 100
        else:
            phase_status["feedback"] = "locked"
            review_complete = False
        
        # Determine current phase based on workflow state and user selection
        current_workflow_phase = st.session_state.get('workflow_phase', 'generate')
        
        # Auto-advance phase based on completion
        if current_workflow_phase == "generate" and has_code:
            current_workflow_phase = "review"
            st.session_state.workflow_phase = "review"
        elif current_workflow_phase == "review" and review_complete:
            current_workflow_phase = "feedback"
            st.session_state.workflow_phase = "feedback"
        
        result = {
            "current_phase": current_workflow_phase,
            "progress_percentage": progress,
            "can_generate": can_generate,
            "in_review": in_review,
            "review_complete": review_complete,
            "has_code": has_code,
            "review_count": len(getattr(state, 'review_history', [])),
            "current_iteration": current_iteration,
            "max_iterations": max_iterations,
            "review_sufficient": review_sufficient,
            "phase_status": phase_status
        }
        
        logger.debug(f"Workflow state info: {result}")
        return result
    
    def _detect_code_presence(self, state) -> bool:
        """
        Robust code presence detection with better validation.
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
    
    def validate_phase_access(self, phase: str) -> Tuple[bool, str]:
        """
        Validate access to a specific workflow phase.
        """
        workflow_info = self.get_workflow_state_info()
        phase_status = workflow_info["phase_status"]
        
        if phase not in phase_status:
            return False, f"Unknown phase: {phase}"
        
        status = phase_status[phase]
        
        if status == "locked":
            if phase == "review":
                return False, t("generate_code_first")
            elif phase == "feedback":
                return False, t("complete_review_first")
        
        return True, ""
    
    def get_phase_progress(self) -> Dict:
        """Get progress information for all phases."""
        workflow_info = self.get_workflow_state_info()
        
        return {
            "overall_progress": workflow_info["progress_percentage"],
            "current_phase": workflow_info["current_phase"],
            "phase_status": workflow_info["phase_status"],
            "can_advance": self._can_advance_phase(workflow_info)
        }
    
    def _can_advance_phase(self, workflow_info: Dict) -> bool:
        """Check if the workflow can advance to the next phase."""
        current_phase = workflow_info["current_phase"]
        
        if current_phase == "generate":
            return workflow_info["has_code"]
        elif current_phase == "review":
            return workflow_info["review_complete"]
        elif current_phase == "feedback":
            return False  # Feedback is the final phase
        
        return False
    
    def advance_to_next_phase(self) -> bool:
        """
        Advance workflow to the next logical phase.
        Returns True if advanced, False if cannot advance.
        """
        workflow_info = self.get_workflow_state_info()
        current_phase = workflow_info["current_phase"]
        
        if not self._can_advance_phase(workflow_info):
            return False
        
        if current_phase == "generate" and workflow_info["has_code"]:
            st.session_state.workflow_phase = "review"
            return True
        elif current_phase == "review" and workflow_info["review_complete"]:
            st.session_state.workflow_phase = "feedback"
            return True
        
        return False
    
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
            
            # Clear generation flags
            if "generation_completed" in st.session_state:
                del st.session_state["generation_completed"]
            
            # Reset to generate phase
            st.session_state.workflow_phase = "generate"
            
            logger.info("Workflow reset for new generation cycle")
    
    def render_workflow_progress_indicator(self):
        """Render simplified workflow progress for unified practice tab."""
        workflow_info = self.get_workflow_state_info()
        
        # Create progress steps for unified view
        steps = [
            {"name": t("generate_code"), "icon": "🔧", "phase": "generate"},
            {"name": t("review_code"), "icon": "📋", "phase": "review"}, 
            {"name": t("view_feedback"), "icon": "📊", "phase": "feedback"}
        ]
        
        current_phase = workflow_info["current_phase"]
        phase_status = workflow_info["phase_status"]
        
        st.markdown("""
        <style>
        .unified-workflow-progress {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1.5rem 0;
            padding: 1.5rem;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            border: 1px solid #dee2e6;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .unified-progress-step {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0 2rem;
            padding: 1rem;
            border-radius: 12px;
            min-width: 120px;
            transition: all 0.3s ease;
            position: relative;
        }
        .unified-progress-step.completed {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border: 2px solid #28a745;
            color: #155724;
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.2);
        }
        .unified-progress-step.active {
            background: linear-gradient(135deg, #fff3cd 0%, #fef8e1 100%);
            border: 2px solid #ffc107;
            color: #856404;
            box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
            transform: scale(1.05);
        }
        .unified-progress-step.locked {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 2px solid #6c757d;
            color: #6c757d;
            opacity: 0.6;
        }
        .unified-step-icon {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .unified-step-name {
            font-size: 1rem;
            text-align: center;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .unified-step-status {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }
        .unified-step-connector {
            position: absolute;
            top: 50%;
            right: -2rem;
            width: 4rem;
            height: 3px;
            background: #dee2e6;
            transform: translateY(-50%);
        }
        .unified-step-connector.completed {
            background: linear-gradient(90deg, #28a745, #20c997);
        }
        .unified-step-connector.active {
            background: linear-gradient(90deg, #ffc107, #fd7e14);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Build progress HTML
        progress_html = '<div class="unified-workflow-progress">'
        
        for i, step in enumerate(steps):
            phase = step["phase"]
            status = phase_status.get(phase, "locked")
            
            # Determine CSS class
            if status == "completed":
                step_class = "completed"
            elif status == "active" or phase == current_phase:
                step_class = "active"
            else:
                step_class = "locked"
            
            progress_html += f'''
            <div class="unified-progress-step {step_class}">
                <div class="unified-step-icon">{step["icon"]}</div>
                <div class="unified-step-name">{step["name"]}</div>
                <div class="unified-step-status">{t(status)}</div>
            '''
            
            # Add connector except for last step
            if i < len(steps) - 1:
                connector_class = "completed" if status == "completed" else ("active" if status == "active" else "")
                progress_html += f'<div class="unified-step-connector {connector_class}"></div>'
            
            progress_html += '</div>'
        
        progress_html += '</div>'
        
        st.markdown(progress_html, unsafe_allow_html=True)
        
        # Add current phase description
        phase_descriptions = {
            "generate": t("configure_and_generate_java_code"),
            "review": t("analyze_code_and_identify_errors"),
            "feedback": t("review_feedback_and_results")
        }
        
        description = phase_descriptions.get(current_phase, "")
        if description:
            st.info(f"📍 **{t('current_phase')}:** {description}")
        
        # Show overall progress
        overall_progress = workflow_info["progress_percentage"]
        st.progress(overall_progress / 100, text=f"{t('overall_progress')}: {overall_progress}%")

    def force_phase_consistency_check(self):
        """
        Force a consistency check and correction of workflow phase.
        """
        try:
            workflow_info = self.get_workflow_state_info()
            current_phase = st.session_state.get('workflow_phase', 'generate')
            
            # Auto-correct phase based on workflow state
            if workflow_info["has_code"] and not workflow_info["review_complete"] and current_phase == "generate":
                st.session_state.workflow_phase = "review"
                logger.debug("Auto-corrected to review phase - code available")
            elif workflow_info["review_complete"] and current_phase in ["generate", "review"]:
                st.session_state.workflow_phase = "feedback"
                logger.debug("Auto-corrected to feedback phase - review complete")
            elif not workflow_info["has_code"] and current_phase in ["review", "feedback"]:
                st.session_state.workflow_phase = "generate"
                logger.debug("Auto-corrected to generate phase - no code available")
            
            return workflow_info
            
        except Exception as e:
            logger.error(f"Error in force consistency check: {str(e)}")
            return None

# Global instance
workflow_controller = WorkflowController()