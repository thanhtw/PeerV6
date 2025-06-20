"""
Unified Practice Component for Java Peer Review Training System.

This component combines code generation, review, and feedback into a single
scrollable interface for better user experience.
"""

import streamlit as st
import logging
import time
from typing import Dict, List, Any, Optional
from ui.components.code_generator import CodeGeneratorUI
from ui.components.code_display import CodeDisplayUI
from ui.components.feedback_system import FeedbackSystem
from utils.language_utils import t, get_current_language
from utils.workflow_controller import workflow_controller
from utils.session_state_manager import session_state_manager

logger = logging.getLogger(__name__)

class UnifiedPracticeUI:
    """
    Unified practice interface that combines code generation, review, and feedback
    in a single vertical scrollable layout.
    """
    
    def __init__(self, workflow, auth_ui=None):
        """Initialize the unified practice UI with necessary components."""
        self.workflow = workflow
        self.auth_ui = auth_ui
        
        # Initialize component UIs
        self.code_generator_ui = CodeGeneratorUI(workflow, None)  # We'll handle code display separately
        self.code_display_ui = CodeDisplayUI()
        self.feedback_system = FeedbackSystem(workflow, auth_ui)
        
        # Initialize session state for unified interface
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for unified practice interface."""
        if "practice_phase" not in st.session_state:
            st.session_state.practice_phase = "configure"  # configure, review, feedback
        if "scroll_to_top" not in st.session_state:
            st.session_state.scroll_to_top = False
    
    def render(self, user_level: str = "medium"):
        """
        Render the unified practice interface with all components in vertical layout.
        
        Args:
            user_level: User's experience level for code generation parameters
        """
        # Handle scroll to top after rerun
        self._handle_scroll_to_top()
        
        # Get current workflow state
        workflow_info = workflow_controller.get_workflow_state_info()
        current_phase = self._determine_current_phase(workflow_info)
        
        # Render header
        self._render_practice_header(workflow_info)
        
        # Render progress indicator
        self._render_practice_progress(current_phase, workflow_info)
        
        # Render main content sections vertically
        self._render_configuration_section(user_level, current_phase, workflow_info)
        self._render_code_display_section(current_phase, workflow_info)
        self._render_review_section(current_phase, workflow_info)
        self._render_feedback_section(current_phase, workflow_info)
        
        # Render action buttons
        self._render_action_buttons(current_phase, workflow_info)
    
    def _handle_scroll_to_top(self):
        """Handle scrolling to top after page rerun."""
        if st.session_state.get("scroll_to_top", False):
            # Inject JavaScript to scroll to top
            st.markdown("""
            <script>
                window.scrollTo(0, 0);
                document.querySelector('.main').scrollTop = 0;
            </script>
            """, unsafe_allow_html=True)
            st.session_state.scroll_to_top = False
    
    def _determine_current_phase(self, workflow_info: Dict) -> str:
        """
        Determine current practice phase based on workflow state.
        
        Returns:
            'configure', 'review', or 'feedback'
        """
        if workflow_info["review_complete"]:
            return "feedback"
        elif workflow_info["has_code"] or workflow_info["in_review"]:
            return "review"
        else:
            return "configure"
    
    def _render_practice_header(self, workflow_info: Dict):
        """Render the practice session header."""
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ">
            <h1 style="margin: 0 0 0.5rem 0; font-size: 2.2rem; color: white;">
                🎯 {t('practice_session')}
            </h1>
            <p style="margin: 0; font-size: 1.1rem; opacity: 0.9; color: white;">
                {t('complete_code_review_workflow')}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_practice_progress(self, current_phase: str, workflow_info: Dict):
        """Render practice progress indicator."""
        phases = [
            {"key": "configure", "name": t("configure"), "icon": "⚙️"},
            {"key": "review", "name": t("review"), "icon": "📋"},
            {"key": "feedback", "name": t("feedback"), "icon": "📊"}
        ]
        
        st.markdown("""
        <style>
        .practice-progress {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1.5rem 0;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 10px;
            border: 1px solid #e9ecef;
        }
        .progress-phase {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem;
            border-radius: 8px;
            min-width: 120px;
            transition: all 0.3s ease;
        }
        .progress-phase.active {
            background: #667eea;
            color: white;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .progress-phase.completed {
            background: #28a745;
            color: white;
        }
        .progress-phase.pending {
            background: #e9ecef;
            color: #6c757d;
        }
        .phase-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .phase-name {
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.9rem;
        }
        .progress-arrow {
            font-size: 1.5rem;
            color: #6c757d;
            margin: 0 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        progress_html = '<div class="practice-progress">'
        
        for i, phase in enumerate(phases):
            # Determine phase state
            if phase["key"] == current_phase:
                phase_class = "active"
            elif self._is_phase_completed(phase["key"], workflow_info):
                phase_class = "completed"
            else:
                phase_class = "pending"
            
            progress_html += f'''
            <div class="progress-phase {phase_class}">
                <div class="phase-icon">{phase["icon"]}</div>
                <div class="phase-name">{phase["name"]}</div>
            </div>
            '''
            
            # Add arrow except for last phase
            if i < len(phases) - 1:
                progress_html += '<div class="progress-arrow">→</div>'
        
        progress_html += '</div>'
        st.markdown(progress_html, unsafe_allow_html=True)
    
    def _is_phase_completed(self, phase_key: str, workflow_info: Dict) -> bool:
        """Check if a phase is completed."""
        if phase_key == "configure":
            return workflow_info["has_code"]
        elif phase_key == "review":
            return workflow_info["review_complete"]
        elif phase_key == "feedback":
            return False  # Feedback is the final phase
        return False
    
    def _render_configuration_section(self, user_level: str, current_phase: str, workflow_info: Dict):
        """Render the code generation configuration section."""
        # Section header
        section_expanded = current_phase == "configure"
        section_disabled = workflow_info["in_review"] and not workflow_info["review_complete"]
        
        if section_disabled:
            st.markdown(f"""
            <div style="
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                text-align: center;
            ">
                🔒 {t('complete_current_review_before_generating')}
            </div>
            """, unsafe_allow_html=True)
        
        with st.expander(
            f"⚙️ {t('step_1_configure_and_generate')}", 
            expanded=section_expanded and not section_disabled
        ):
            if section_disabled:
                st.info(f"📋 {t('finish_review_to_generate_new_code')}")
            else:
                # Use existing code generator UI
                self.code_generator_ui.render(user_level)
    
    def _render_code_display_section(self, current_phase: str, workflow_info: Dict):
        """Render the generated code display section."""
        if not workflow_info["has_code"]:
            return
        
        section_expanded = current_phase == "review"
        
        with st.expander(
            f"📄 {t('step_2_generated_code')}", 
            expanded=section_expanded
        ):
            # Display the generated code
            if hasattr(st.session_state, 'workflow_state') and st.session_state.workflow_state:
                state = st.session_state.workflow_state
                if hasattr(state, 'code_snippet') and state.code_snippet:
                    self.code_display_ui.render_code_display(state.code_snippet)
                else:
                    st.info(t("code_generation_in_progress"))
            else:
                st.warning(t("no_code_available"))
    
    def _render_review_section(self, current_phase: str, workflow_info: Dict):
        """Render the code review section."""
        if not workflow_info["has_code"]:
            return
        
        if workflow_info["review_complete"]:
            section_title = f"✅ {t('step_3_review_completed')}"
            section_expanded = False
        else:
            section_title = f"📋 {t('step_3_review_code')}"
            section_expanded = current_phase == "review"
        
        with st.expander(section_title, expanded=section_expanded):
            if workflow_info["review_complete"]:
                st.success(f"🎉 {t('review_completed_successfully')}")
                st.info(f"📊 {t('check_feedback_section_below')}")
            else:
                # Render review interface
                self._render_review_interface()
    
    def _render_review_interface(self):
        """Render the review interface within the section."""
        if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
            st.info("📝 Please generate code first.")
            return
        
        state = st.session_state.workflow_state
        current_iteration = getattr(state, 'current_iteration', 1)
        max_iterations = getattr(state, 'max_iterations', 3)
        review_sufficient = getattr(state, 'review_sufficient', False)
        
        if current_iteration <= max_iterations and not review_sufficient:
            # Get review data for display
            review_history = getattr(state, 'review_history', [])
            latest_review = review_history[-1] if review_history else None
            
            targeted_guidance = getattr(latest_review, "targeted_guidance", None) if latest_review else None
            review_analysis = getattr(latest_review, "analysis", None) if latest_review else None
            
            # Simple callback for unified workflow
            def on_submit_unified(review_text):
                # Trigger scroll to top after submission
                st.session_state.scroll_to_top = True
                
                updated_state = self.workflow.submit_review(state, review_text)
                if hasattr(updated_state, 'error') and updated_state.error:
                    st.error(f"❌ {updated_state.error}")
                    return False
                st.session_state.workflow_state = updated_state
                return True
            
            # Render review input
            self.code_display_ui.render_review_input(
                on_submit_callback=on_submit_unified,
                iteration_count=current_iteration,
                max_iterations=max_iterations,
                targeted_guidance=targeted_guidance,
                review_analysis=review_analysis
            )
        else:
            st.success("🎉 Review phase completed!")
    
    def _render_feedback_section(self, current_phase: str, workflow_info: Dict):
        """Render the feedback and results section."""
        if not workflow_info["review_complete"]:
            return
        
        section_expanded = current_phase == "feedback"
        
        with st.expander(
            f"📊 {t('step_4_feedback_and_results')}", 
            expanded=section_expanded
        ):
            # Render feedback using existing feedback system
            self.feedback_system.render_feedback_tab()
    
    def _render_action_buttons(self, current_phase: str, workflow_info: Dict):
        """Render action buttons for the current phase."""
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if workflow_info["review_complete"]:
                if st.button(
                    f"🔄 {t('start_new_practice_session')}", 
                    use_container_width=True,
                    type="primary"
                ):
                    self._start_new_session()
        
        with col2:
            if current_phase == "review" and workflow_info["has_code"]:
                if st.button(
                    f"📋 {t('scroll_to_review')}", 
                    use_container_width=True
                ):
                    self._scroll_to_section("review")
        
        with col3:
            if current_phase == "feedback":
                if st.button(
                    f"📊 {t('scroll_to_feedback')}", 
                    use_container_width=True
                ):
                    self._scroll_to_section("feedback")
    
    def _start_new_session(self):
        """Start a new practice session."""
        # Reset workflow state
        workflow_controller.reset_workflow_for_new_cycle()
        
        # Reset practice session state
        st.session_state.practice_phase = "configure"
        st.session_state.scroll_to_top = True
        
        # Clear any generation flags
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith("generation_")]
        for key in keys_to_clear:
            del st.session_state[key]
        
        st.success(f"🎯 {t('new_practice_session_started')}")
        st.rerun()
    
    def _scroll_to_section(self, section: str):
        """Scroll to a specific section (placeholder for future enhancement)."""
        st.session_state.scroll_to_top = True
        st.info(f"📍 {t('scrolling_to')} {section} {t('section')}")
        st.rerun()