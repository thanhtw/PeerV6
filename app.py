import streamlit as st
import os
import logging
from state_schema import WorkflowState

# Import CSS utilities
from static.css_utils import load_css

# Import language utilities with i18n support
from utils.language_utils import init_language, render_language_selector, t

# Import FIXED workflow controller
from utils.workflow_controller import workflow_controller

# Import enhanced session state manager
from utils.session_state_manager import session_state_manager

# Configure logging
logging.getLogger('streamlit').setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import LLM Manager
from llm_manager import LLMManager

# Import LangGraph components
from langgraph_workflow import JavaCodeReviewGraph

# Import UI components
from ui.components.code_generator import CodeGeneratorUI
from ui.components.code_display import CodeDisplayUI  
from ui.components.feedback_system import render_feedback_tab
from ui.components.auth_ui import AuthUI
from ui.components.tutorial import TutorialUI

# Set page config
st.set_page_config(
    page_title="Java Code Review Trainer",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

css_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "css")

try:
    load_css(css_directory=css_dir)    
except Exception as e:
    logger.warning(f"CSS loading failed: {str(e)}")

def scroll_to_current_phase():
    """Enhanced auto-scroll to current workflow phase with smooth animation."""
    workflow_phase = st.session_state.get('workflow_phase', 'generate')
    
    # Map workflow phases to their HTML element IDs
    phase_mappings = {
        'generate': 'generation-phase',
        'review': 'review-phase', 
        'feedback': 'feedback-phase'
    }
    
    target_id = phase_mappings.get(workflow_phase, 'generation-phase')
    
    st.markdown(f"""
    <script>
    // Enhanced smooth scroll with better timing
    function scrollToPhase() {{
        const targetElement = document.getElementById('{target_id}');
        if (targetElement) {{
            // Add highlight effect
            targetElement.style.boxShadow = '0 0 20px rgba(76, 104, 215, 0.3)';
            targetElement.style.transform = 'scale(1.02)';
            
            // Smooth scroll with offset for better visibility
            const yOffset = -20;
            const elementPosition = targetElement.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset + yOffset;
            
            window.scrollTo({{
                top: offsetPosition,
                behavior: 'smooth'
            }});
            
            // Remove highlight after animation
            setTimeout(() => {{
                targetElement.style.boxShadow = '';
                targetElement.style.transform = '';
            }}, 2000);
        }}
    }}
    
    // Wait for page to fully render then scroll
    setTimeout(scrollToPhase, 300);
    </script>
    """, unsafe_allow_html=True)

def scroll_to_top():
    """Add JavaScript to scroll to top of page."""
    st.markdown("""
    <script>
    window.scrollTo(0, 0);
    </script>
    """, unsafe_allow_html=True)

def _handle_workflow_progression():
    """Handle workflow progression flags with enhanced auto-scroll."""
    if st.session_state.get("should_switch_to_feedback", False):
        st.session_state.workflow_phase = "feedback"
        del st.session_state["should_switch_to_feedback"]
        scroll_to_current_phase()  # Enhanced scroll
        st.rerun()
        return True
    
    if st.session_state.get("should_start_new_cycle", False):
        workflow_controller.reset_workflow_for_new_cycle()
        st.session_state.workflow_phase = "generate"
        del st.session_state["should_start_new_cycle"]
        scroll_to_current_phase()  # Enhanced scroll
        st.rerun()
        return True
    
    if st.session_state.get("should_switch_to_review", False):
        st.session_state.workflow_phase = "review"
        del st.session_state["should_switch_to_review"]
        scroll_to_current_phase()  # Enhanced scroll
        st.rerun()
        return True
    
    return False

def main():
    """Main application function with simplified two-tab interface."""
    
    # Clean up expired locks at start of each run
    session_state_manager.cleanup_expired_locks()
    
    # Handle workflow progression flags
    if _handle_workflow_progression():
        return

    # Initialize language selection and i18n system
    init_language()

    # Initialize the authentication UI
    auth_ui = AuthUI()
    
    # Check if the user is authenticated
    if not auth_ui.is_authenticated():
        is_authenticated = auth_ui.render_auth_page()
        if not is_authenticated:
            return

    # Get user level and store in session state
    user_level = auth_ui.get_user_level()   
    st.session_state.user_level = user_level
    
    # Handle full reset with better state management
    if st.session_state.get("full_reset", False):
        del st.session_state["full_reset"]
        preserved = {
            key: st.session_state.get(key) 
            for key in ["auth", "provider_selection", "user_level", "language", "session_id"]
            if key in st.session_state
        }        
        
        # Clear workflow-related state but preserve practice mode if active
        workflow_keys = [k for k in st.session_state.keys() 
                        if k not in preserved.keys() and not k.startswith("practice_")]
        for key in workflow_keys:
            del st.session_state[key]
        
        # Restore preserved values
        st.session_state.update(preserved)
        
        # Only reset workflow state if not in practice mode
        if not st.session_state.get("practice_mode_active", False):
            st.session_state.workflow_state = WorkflowState()
            st.session_state.active_tab = 0
            st.session_state.workflow_phase = "generate"
        
        scroll_to_top()
        st.rerun()

    # Initialize session state with enhanced management
    init_session_state()

    # Initialize LLM manager
    llm_manager = LLMManager()
    
    if "provider_selection" not in st.session_state:
        st.session_state.provider_selection = "groq"    
    
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        st.error("⚠️ No Groq API key found in environment variables. Please set GROQ_API_KEY in your .env file.")
        st.info("To get a Groq API key:")
        st.info("1. Visit https://console.groq.com/")
        st.info("2. Sign up and get your API key")
        st.info("3. Add GROQ_API_KEY=your_key_here to your .env file")
        st.stop()

    # Configure provider
    try:
        success = llm_manager.set_provider("groq", api_key)
        if not success:
            st.error("❌ Failed to configure Groq provider. Please check your configuration.")
            st.stop()
        else:
            logger.debug("✅ Groq provider configured successfully")
    except Exception as e:
        st.error(f"❌ Error configuring LLM provider: {str(e)}")
        st.stop()

    # Render user profile with total points instead of score
    auth_ui.render_combined_profile_leaderboard()

    # Initialize workflow after provider is setup
    workflow = JavaCodeReviewGraph(llm_manager)

    # Initialize UI components with enhanced state management - FIXED: Initialize code_display_ui first
    code_display_ui = CodeDisplayUI()
    code_generator_ui = CodeGeneratorUI(workflow, code_display_ui)       
    error_explorer_ui = TutorialUI(workflow)
    
    # Check if we're in practice mode
    if st.session_state.get("practice_mode_active", False):
        render_practice_mode_interface(error_explorer_ui, workflow)
    else:
        render_normal_interface_with_two_tabs(
            code_generator_ui, 
            workflow, 
            code_display_ui, 
            auth_ui,          
            error_explorer_ui,
            user_level
        )

def init_session_state():
    """Enhanced session state initialization with workflow phase management."""
    
    # Use the session state manager for safe initialization
    if 'workflow_state' not in st.session_state:
        st.session_state.workflow_state = WorkflowState()
    
    # Initialize workflow phase for unified practice tab
    if 'workflow_phase' not in st.session_state:
        st.session_state.workflow_phase = "generate"
    
    # Initialize active tab (0 = Tutorial, 1 = Practice)
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    
    # Initialize UI state with enhanced management
    ui_defaults = {
        'error': None,
        'workflow_steps': [],
        'sidebar_tab': "Status",
        'user_level': None,
        # State management flags
        'generation_in_progress': False,
        'review_submission_in_progress': False,
        'last_rerun_timestamp': 0
    }
    
    for key, default_value in ui_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Update last rerun timestamp
    import time
    st.session_state.last_rerun_timestamp = time.time()
    
    # Initialize LLM logger
    if 'llm_logger' not in st.session_state:
        from utils.llm_logger import LLMInteractionLogger
        st.session_state.llm_logger = LLMInteractionLogger()

def render_practice_mode_interface(error_explorer_ui, workflow):
    """Render the streamlined practice mode interface."""    
    # Render the error explorer in practice mode with workflow
    error_explorer_ui.render(workflow)

def render_normal_interface_with_two_tabs(code_generator_ui, workflow, code_display_ui, auth_ui, 
                                         error_explorer_ui, user_level):
    """Render the simplified two-tab interface."""
    
    # Header with improved styling and reduced size
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1rem;">
        <h1 style="color: rgb(178 185 213); margin-bottom: 0.3rem; font-size: 1.8rem;">{t('app_title')}</h1>
        <p style="font-size: 1rem; color: #666; margin-bottom: 0.5rem;">{t('app_subtitle')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display error message if there's an error
    if st.session_state.error:
        st.error(f"Error: {st.session_state.error}")
        if st.button("Clear Error"):
            st.session_state.error = None
            st.rerun()
    
    # Create simplified two-tab interface
    tab_labels = [
        t("tab_tutorial"),
        t("tab_practice")
    ]
    
    tabs = st.tabs(tab_labels)
    
    # Handle tab switching
    for i, tab in enumerate(tabs):
        if tab:
            st.session_state.active_tab = i

    # Tutorial Tab
    with tabs[0]:
        try:
            error_explorer_ui.render(workflow) 
        except Exception as e:
            logger.error(f"Error in tutorial tab: {str(e)}")
            st.error("Error loading tutorial. Please refresh the page.")

    # Practice Tab - Unified workflow
    with tabs[1]:
        try:
            render_unified_practice_workflow(
                code_generator_ui, 
                workflow, 
                code_display_ui, 
                auth_ui, 
                user_level
            )
        except Exception as e:
            logger.error(f"Error in practice tab: {str(e)}")
            st.error("Error in practice section. Please refresh the page.")

def render_unified_practice_workflow(code_generator_ui, workflow, code_display_ui, auth_ui, user_level):
    """Render the unified practice workflow with compact, user-friendly design."""
    
    # Get workflow state
    workflow_info = workflow_controller.get_workflow_state_info()
    current_phase = st.session_state.get('workflow_phase', 'generate')
    
    # Phase 1: Code Generation (Compact Design)
    render_compact_generation_phase(code_generator_ui, workflow_info, current_phase, user_level)
    
    # Phase 2: Code Review (Compact Design)
    render_compact_review_phase(workflow, code_display_ui, workflow_info, current_phase)
    
    # Phase 3: Feedback (Compact Design)
    render_compact_feedback_phase(workflow, auth_ui, workflow_info, current_phase)

def render_compact_generation_phase(code_generator_ui, workflow_info, current_phase, user_level):
    """Render compact code generation phase."""
    
    # Determine phase status
    if workflow_info["has_code"]:
        phase_class = "compact-phase-completed"
        status_class = "compact-status-completed"
        status_text = t("completed")
    elif current_phase == "generate":
        phase_class = "compact-phase-active"
        status_class = "compact-status-active" 
        status_text = t("active")
    else:
        phase_class = "compact-phase-upcoming"
        status_class = "compact-status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="compact-practice-phase {phase_class}" id="generation-phase">
        <div class="compact-phase-header">
            <span class="compact-phase-icon">🔧</span>
            <span class="compact-phase-title">{t('phase_1_generate_code')}</span>
            <span class="compact-phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if current_phase == "generate" or not workflow_info["has_code"]:
        # Show generation interface with compact design
        if workflow_info["review_complete"]:
            st.success("🎉 " + t("previous_review_completed"))
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("💡 " + t("start_new_review_cycle"))
            with col2:
                if st.button("🔄 " + t("start_new_cycle"), type="primary", use_container_width=True):
                    workflow_controller.reset_workflow_for_new_cycle()
                    st.session_state.workflow_phase = "generate"
                    scroll_to_current_phase()
                    st.rerun()
        
        # Compact content area
        with st.container():
            st.markdown('<div class="compact-content">', unsafe_allow_html=True)
            code_generator_ui.render(user_level)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-advance to review if code is generated
        if workflow_info["has_code"] and current_phase == "generate":
            st.session_state.workflow_phase = "review"
            scroll_to_current_phase()
            st.rerun()

def render_compact_review_phase(workflow, code_display_ui, workflow_info, current_phase):
    """Render compact code review phase."""
    
    # Determine phase status
    if workflow_info["review_complete"]:
        phase_class = "compact-phase-completed"
        status_class = "compact-status-completed"
        status_text = t("completed")
    elif workflow_info["has_code"] and not workflow_info["review_complete"]:
        phase_class = "compact-phase-active"
        status_class = "compact-status-active"
        status_text = t("active")
    else:
        phase_class = "compact-phase-upcoming"
        status_class = "compact-status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="compact-practice-phase {phase_class}" id="review-phase">
        <div class="compact-phase-header">
            <span class="compact-phase-icon">📋</span>
            <span class="compact-phase-title">{t('phase_2_review_code')}</span>
            <span class="compact-phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not workflow_info["has_code"]:
        logger.info("📝 " + t("complete_code_generation_first"))
        return
    
    if workflow_info["review_complete"]:
        logger.info("🎉 " + t("review_completed_successfully"))
    
    else:
        # Show active review interface (compact)
        with st.container():
            #st.markdown('<div class="compact-content">', unsafe_allow_html=True)
            render_compact_review_tab(workflow, code_display_ui, workflow_info)
            #st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-advance to feedback if review is complete
        if workflow_info["review_complete"]:
            st.session_state.workflow_phase = "feedback"
            scroll_to_current_phase()
            st.rerun()

def render_compact_feedback_phase(workflow, auth_ui, workflow_info, current_phase):
    """Render compact feedback phase."""
    
    # Determine phase status
    if workflow_info["review_complete"]:
        phase_class = "compact-phase-active"
        status_class = "compact-status-active"
        status_text = t("active")
    else:
        phase_class = "compact-phase-upcoming"
        status_class = "compact-status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="compact-practice-phase {phase_class}" id="feedback-phase">
        <div class="compact-phase-header">
            <span class="compact-phase-icon">📊</span>
            <span class="compact-phase-title">{t('phase_3_feedback')}</span>
            <span class="compact-phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not workflow_info["review_complete"]:
        st.info("📋 " + t("complete_review_before_feedback"))
        progress_text = f"{t('current')}: {workflow_info['current_iteration']}/{workflow_info['max_iterations']} {t('iterations')}"
        st.info(f"📊 {progress_text}")
        return
    
    # Show feedback interface (compact)
    with st.container():
        #st.markdown('<div class="compact-content">', unsafe_allow_html=True)
        render_feedback_tab(workflow, auth_ui)
        #st.markdown('</div>', unsafe_allow_html=True)

def render_compact_review_tab(workflow, code_display_ui, workflow_info):
    """Render compact review tab with better state handling."""
    
    logger.debug(f"Rendering compact review tab with workflow_info: {workflow_info}")
    
    # Check state
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.warning("⚙️ " + t("no_workflow_state_available"))
        st.info("💡 " + t("please_generate_code_first"))
        return
    
    state = st.session_state.workflow_state
    
    # Check for code
    if not hasattr(state, 'code_snippet') or not state.code_snippet:
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin: 1rem 0;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚙️</div>
            <h4 style="margin: 0; color: #495057;">{t('no_code_available')}</h4>
            <p style="margin: 0.5rem 0 0 0; color: #6c757d;">{t('generate_code_snippet_first')}</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Compact review interface
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <h4 style="color: #495057; margin: 0; font-size: 1.2rem; font-weight: 600;">
            📋 {t('review_java_code')}
        </h4>
        <p style="color: #6c757d; margin: 0.3rem 0 0 0; font-size: 0.9rem;">
            {t('carefully_examine_code')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show workflow progress in review (compact)
    if workflow_info["in_review"]:
        progress_text = f"📍 {t('review_in_progress')} - {t('iteration')} {workflow_info['current_iteration']}/{workflow_info['max_iterations']}"
        st.info(progress_text)
    
    # Display the code
    try:
        code_display_ui.render_code_display(state.code_snippet)
        logger.debug("Code display rendered successfully")
    except Exception as display_error:
        logger.error(f"Error rendering code display: {str(display_error)}")
        st.error(f"Error displaying code: {str(display_error)}")
        return
    
    # Handle review submission (compact)
    try:
        _handle_compact_review_submission(workflow, code_display_ui, workflow_info)
    except Exception as submission_error:
        logger.error(f"Error in review submission handling: {str(submission_error)}")
        st.error(f"Error in review submission: {str(submission_error)}")

def _handle_compact_review_submission(workflow, code_display_ui, workflow_info):
    """Handle review submission with compact design."""
    
    state = st.session_state.workflow_state
    
    # Get review data for display
    current_iteration = workflow_info["current_iteration"]
    max_iterations = workflow_info["max_iterations"]
    review_history = getattr(state, 'review_history', [])
    latest_review = review_history[-1] if review_history else None
    
    targeted_guidance = getattr(latest_review, "targeted_guidance", None) if latest_review else None
    review_analysis = getattr(latest_review, "analysis", None) if latest_review else None
    
    # Compact callback for workflow-controlled submission
    def on_submit_compact(review_text):
        try:
            logger.debug(f"Submitting review: {review_text[:100]}...")
            updated_state = workflow.submit_review(state, review_text)
            
            if hasattr(updated_state, 'error') and updated_state.error:
                st.error(f"❌ {updated_state.error}")
                return False
                
            st.session_state.workflow_state = updated_state
            logger.debug("Review submitted successfully")
            
            # Check if review is complete and set flag for feedback transition
            review_sufficient = getattr(updated_state, 'review_sufficient', False)
            new_iteration = getattr(updated_state, 'current_iteration', 1)
            
            if review_sufficient or new_iteration > max_iterations:
                logger.debug("Review completed, transitioning to feedback")
                st.session_state.workflow_phase = "feedback"
                scroll_to_current_phase()
                
            return True
            
        except Exception as e:
            logger.error(f"Error in review submission: {str(e)}")
            st.error(f"❌ Error submitting review: {str(e)}")
            return False
    
    # Render compact review input
    try:
        code_display_ui.render_review_input(
            on_submit_callback=on_submit_compact,
            iteration_count=current_iteration,
            max_iterations=max_iterations,
            targeted_guidance=targeted_guidance,
            review_analysis=review_analysis
        )
        logger.debug("Review input rendered successfully")
    except Exception as input_error:
        logger.error(f"Error rendering review input: {str(input_error)}")
        st.error(f"Error rendering review input: {str(input_error)}")

if __name__ == "__main__":
    main()