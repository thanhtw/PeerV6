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

def scroll_to_top():
    """Add JavaScript to scroll to top of page."""
    st.markdown("""
    <script>
    window.scrollTo(0, 0);
    </script>
    """, unsafe_allow_html=True)

def _handle_workflow_progression():
    """Handle workflow progression flags in one place."""
    if st.session_state.get("should_switch_to_feedback", False):
        st.session_state.workflow_phase = "feedback"
        del st.session_state["should_switch_to_feedback"]
        scroll_to_top()
        st.rerun()
        return True
    
    if st.session_state.get("should_start_new_cycle", False):
        workflow_controller.reset_workflow_for_new_cycle()
        st.session_state.workflow_phase = "generate"
        del st.session_state["should_start_new_cycle"]
        scroll_to_top()
        st.rerun()
        return True
    
    if st.session_state.get("should_switch_to_review", False):
        st.session_state.workflow_phase = "review"
        del st.session_state["should_switch_to_review"]
        scroll_to_top()
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
    
    # Header with improved styling
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: rgb(178 185 213); margin-bottom: 5px;">{t('app_title')}</h1>
        <p style="font-size: 1.1rem; color: #666;">{t('app_subtitle')}</p>
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
    """Render the unified practice workflow in a single scrollable tab."""
    
    # Get workflow state
    workflow_info = workflow_controller.get_workflow_state_info()
    current_phase = st.session_state.get('workflow_phase', 'generate')
    
    # Add scroll to top CSS
    st.markdown("""
    <style>
    .practice-phase {
        margin-bottom: 3rem;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border: 1px solid #e9ecef;
    }
    .phase-completed {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-color: #28a745;
    }
    .phase-active {
        background: linear-gradient(135deg, #fff3cd 0%, #fef8e1 100%);
        border-color: #ffc107;
    }
    .phase-upcoming {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-color: #6c757d;
        opacity: 0.7;
    }
    .phase-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        font-size: 1.5rem;
        font-weight: 700;
    }
    .phase-icon {
        margin-right: 1rem;
        font-size: 2rem;
    }
    .phase-title {
        flex: 1;
    }
    .phase-status {
        font-size: 0.9rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
    }
    .status-completed { background: #28a745; color: white; }
    .status-active { background: #ffc107; color: #212529; }
    .status-upcoming { background: #6c757d; color: white; }
    </style>
    """, unsafe_allow_html=True)

    # Phase 1: Code Generation
    render_generation_phase(code_generator_ui, workflow_info, current_phase, user_level, code_generator_ui)
    
    # Phase 2: Code Review  
    render_review_phase(workflow, code_display_ui, workflow_info, current_phase)
    
    # Phase 3: Feedback
    render_feedback_phase(workflow, auth_ui, workflow_info, current_phase)

def render_generation_phase(code_generator_ui, workflow_info, current_phase, user_level, code_display_ui):
    """Render the code generation phase."""
    
    # Determine phase status
    if workflow_info["has_code"]:
        phase_class = "phase-completed"
        status_class = "status-completed"
        status_text = t("completed")
    elif current_phase == "generate":
        phase_class = "phase-active"
        status_class = "status-active" 
        status_text = t("active")
    else:
        phase_class = "phase-upcoming"
        status_class = "status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="practice-phase {phase_class}" id="generation-phase">
        <div class="phase-header">
            <span class="phase-icon">🔧</span>
            <span class="phase-title">{t('phase_1_generate_code')}</span>
            <span class="phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if current_phase == "generate" or not workflow_info["has_code"]:
        # Show generation interface
        if workflow_info["review_complete"]:
            st.success("🎉 " + t("previous_review_completed"))
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info("💡 " + t("start_new_review_cycle"))
            with col2:
                if st.button("🔄 " + t("start_new_cycle"), type="primary"):
                    workflow_controller.reset_workflow_for_new_cycle()
                    st.session_state.workflow_phase = "generate"
                    scroll_to_top()
                    st.rerun()
        
        code_generator_ui.render(user_level)
        
        # Auto-advance to review if code is generated
        if workflow_info["has_code"] and current_phase == "generate":
            st.session_state.workflow_phase = "review"
            scroll_to_top()
            st.rerun()

def render_review_phase(workflow, code_display_ui, workflow_info, current_phase):
    """Render the code review phase."""
    
    # Determine phase status
    if workflow_info["review_complete"]:
        phase_class = "phase-completed"
        status_class = "status-completed"
        status_text = t("completed")
    elif workflow_info["has_code"] and not workflow_info["review_complete"]:
        phase_class = "phase-active"
        status_class = "status-active"
        status_text = t("active")
    else:
        phase_class = "phase-upcoming"
        status_class = "status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="practice-phase {phase_class}" id="review-phase">
        <div class="phase-header">
            <span class="phase-icon">📋</span>
            <span class="phase-title">{t('phase_2_review_code')}</span>
            <span class="phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not workflow_info["has_code"]:
        st.info("📝 " + t("complete_code_generation_first"))
        return
    
    if workflow_info["review_complete"]:
        # Show completed review summary
        st.success("🎉 " + t("review_completed_successfully"))
        
      
        # Option to restart review
        if st.button("🔄 " + t("restart_review"), key="restart_review_from_summary"):
            # Reset review state
            if hasattr(st.session_state, 'workflow_state'):
                state = st.session_state.workflow_state
                state.review_history = []
                state.current_iteration = 1
                state.review_sufficient = False
                state.comparison_report = None
            
            st.session_state.workflow_phase = "review"
            scroll_to_top()
            st.rerun()
    
    else:
        # Show active review interface
        render_improved_review_tab(workflow, code_display_ui, workflow_info)
        
        # Auto-advance to feedback if review is complete
        if workflow_info["review_complete"]:
            st.session_state.workflow_phase = "feedback"
            scroll_to_top()
            st.rerun()

def render_feedback_phase(workflow, auth_ui, workflow_info, current_phase):
    """Render the feedback phase."""
    
    # Determine phase status
    if workflow_info["review_complete"]:
        phase_class = "phase-active"
        status_class = "status-active"
        status_text = t("active")
    else:
        phase_class = "phase-upcoming"
        status_class = "status-upcoming"
        status_text = t("pending")
    
    st.markdown(f"""
    <div class="practice-phase {phase_class}" id="feedback-phase">
        <div class="phase-header">
            <span class="phase-icon">📊</span>
            <span class="phase-title">{t('phase_3_feedback')}</span>
            <span class="phase-status {status_class}">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not workflow_info["review_complete"]:
        st.info("📋 " + t("complete_review_before_feedback"))
        progress_text = f"{t('current')}: {workflow_info['current_iteration']}/{workflow_info['max_iterations']} {t('iterations')}"
        st.info(f"📊 {progress_text}")
        return
    
    # Show feedback interface
    render_feedback_tab(workflow, auth_ui)

def render_improved_review_tab(workflow, code_display_ui, workflow_info):
    """Render the improved review tab with better state handling."""
    
    logger.debug(f"Rendering review tab with workflow_info: {workflow_info}")
    
    # Check state
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.warning("⚙️ " + t("no_workflow_state_available"))
        st.info("💡 " + t("please_generate_code_first"))
        return
    
    state = st.session_state.workflow_state
    
    # Check for code
    if not hasattr(state, 'code_snippet') or not state.code_snippet:
        st.markdown(f"""
        <div class="unavailable-state">
            <div class="state-icon">⚙️</div>
            <h3>{t('no_code_available')}</h3>
            <p>{t('generate_code_snippet_first')}</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Render review interface
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h3 style="color: #495057; margin-bottom: 0.5rem; font-size: 1.5rem; font-weight: 700;">
            📋 {t('review_java_code')}
        </h3>
        <p style="color: #6c757d; margin: 0; font-size: 1rem;">
            {t('carefully_examine_code')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show workflow progress in review
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
    
    # Handle review submission
    try:
        _handle_review_submission_with_workflow_control(workflow, code_display_ui, workflow_info)
    except Exception as submission_error:
        logger.error(f"Error in review submission handling: {str(submission_error)}")
        st.error(f"Error in review submission: {str(submission_error)}")

def _handle_review_submission_with_workflow_control(workflow, code_display_ui, workflow_info):
    """Handle review submission with workflow control."""
    
    state = st.session_state.workflow_state
    
    # Get review data for display
    current_iteration = workflow_info["current_iteration"]
    max_iterations = workflow_info["max_iterations"]
    review_history = getattr(state, 'review_history', [])
    latest_review = review_history[-1] if review_history else None
    
    targeted_guidance = getattr(latest_review, "targeted_guidance", None) if latest_review else None
    review_analysis = getattr(latest_review, "analysis", None) if latest_review else None
    
    # Simple callback for workflow-controlled submission
    def on_submit_with_workflow_control(review_text):
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
                scroll_to_top()
                
            return True
            
        except Exception as e:
            logger.error(f"Error in review submission: {str(e)}")
            st.error(f"❌ Error submitting review: {str(e)}")
            return False
    
    # Render review input
    try:
        code_display_ui.render_review_input(
            on_submit_callback=on_submit_with_workflow_control,
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