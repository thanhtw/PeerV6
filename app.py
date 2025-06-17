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

# Import modularized UI functions
from ui.utils.main_ui import create_tabs_with_workflow_control  

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

def _handle_all_switching_flags():
    """Handle all tab switching flags in one place to prevent conflicts."""
    if st.session_state.get("should_switch_to_feedback", False):
        st.session_state.active_tab = 3
        del st.session_state["should_switch_to_feedback"]
        st.rerun()
        return True
    
    if st.session_state.get("should_start_new_cycle", False):
        workflow_controller.reset_workflow_for_new_cycle()
        st.session_state.active_tab = 1
        del st.session_state["should_start_new_cycle"]
        st.rerun()
        return True
    
    if st.session_state.get("should_switch_to_review", False):
        st.session_state.active_tab = 2
        del st.session_state["should_switch_to_review"]
        st.rerun()
        return True
    
    # Auto-switch to feedback (ONE TIME ONLY)
    if not st.session_state.get("auto_switched_to_feedback", False):
        workflow_info = workflow_controller.get_workflow_state_info()
        if workflow_info["review_complete"] and st.session_state.get('active_tab', 0) != 3:
            st.session_state.active_tab = 3
            st.session_state.auto_switched_to_feedback = True
            st.rerun()
            return True
    
    return False

def main():
    """FIXED: Main application function with improved workflow control."""

    # Clean up expired locks at start of each run
    session_state_manager.cleanup_expired_locks()

    if _handle_all_switching_flags():
        return

    # Initialize language selection and i18n system
    init_language()

    # Initialize the authentication UI
    auth_ui = AuthUI()
    
    # Check if the user is authenticated
    if not auth_ui.is_authenticated():
        render_language_selector()
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
        
        st.rerun()

    # Initialize session state with enhanced management
    init_session_state()
    
    # FIXED: Handle tab transitions and ensure consistency
    session_state_manager.handle_tab_transition_after_generation()
    session_state_manager.ensure_tab_consistency()

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

    # Add language selector to sidebar
    render_language_selector()
    
    # Render user profile with total points instead of score
    auth_ui.render_combined_profile_leaderboard()

    # Initialize workflow after provider is setup
    workflow = JavaCodeReviewGraph(llm_manager)

    # Initialize UI components with enhanced state management
    code_display_ui = CodeDisplayUI()
    code_generator_ui = CodeGeneratorUI(workflow, code_display_ui)       
    error_explorer_ui = TutorialUI(workflow)
    
    # Check if we're in practice mode
    if st.session_state.get("practice_mode_active", False):
        render_practice_mode_interface(error_explorer_ui, workflow)
    else:
        render_normal_interface_with_workflow_control(
            code_generator_ui, 
            workflow, 
            code_display_ui, 
            auth_ui,          
            error_explorer_ui,
            user_level
        )

def init_session_state():
    """Enhanced session state initialization with improved workflow management."""
    
    # Use the session state manager for safe initialization
    if 'workflow_state' not in st.session_state:
        st.session_state.workflow_state = WorkflowState()
    
    # FIXED: Better active tab initialization based on workflow state
    if 'active_tab' not in st.session_state:
        # Check if we should start with a specific tab based on workflow state
        if hasattr(st.session_state, 'workflow_state') and st.session_state.workflow_state:
            workflow_info = workflow_controller.get_workflow_state_info()
            if workflow_info["has_code"] and not workflow_info["review_complete"]:
                st.session_state.active_tab = 2  # Start with review tab if code exists
            elif workflow_info["review_complete"]:
                st.session_state.active_tab = 3  # Start with feedback if review complete
            else:
                st.session_state.active_tab = 0  # Default to tutorial
        else:
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

def render_normal_interface_with_workflow_control(code_generator_ui, workflow, code_display_ui, auth_ui, 
                                                 error_explorer_ui, user_level):
    """FIXED: Enhanced normal interface with better tab management and NO infinite reruns."""
    
    # Header with improved styling
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: rgb(178 185 213); margin-bottom: 5px;">{t('app_title')}</h1>
        <p style="font-size: 1.1rem; color: #666;">{t('app_subtitle')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render workflow progress indicator
    workflow_controller.render_workflow_progress_indicator()
    
    # Display error message if there's an error
    if st.session_state.error:
        st.error(f"Error: {st.session_state.error}")
        if st.button("Clear Error"):
            st.session_state.error = None
            st.rerun()
    
    # Create enhanced tabs with workflow control
    tab_labels = [
        t("tab_tutorial"),
        t("tab_generate"),
        t("tab_review"),
        t("tab_feedback")      
    ]
    
    # Get workflow state for tab control
    workflow_info = workflow_controller.get_workflow_state_info()
    
    # FIXED: Better tab validation without auto-redirects that cause loops
    current_tab = st.session_state.get('active_tab', 0)
    can_access, reason = workflow_controller.validate_tab_access(current_tab)
    
    if not can_access and reason:
        # Show warning but DON'T auto-redirect (this was causing loops)
        st.warning(f"⚠️ {reason}")
        
        # Provide manual navigation options instead of auto-redirect
        if workflow_info["has_code"] and not workflow_info["review_complete"]:
            if st.button(f"📋 {t('go_to_review_tab')}"):
                st.session_state.active_tab = 2
                st.rerun()
        elif not workflow_info["has_code"]:
            if st.button(f"🔧 {t('go_to_generate_tab')}"):
                st.session_state.active_tab = 1
                st.rerun()
        elif workflow_info["review_complete"]:
            if st.button(f"📊 {t('go_to_feedback_tab')}"):
                st.session_state.active_tab = 3
                st.rerun()
    
    # Create tabs with visual indicators
    tabs = create_tabs_with_workflow_control(tab_labels, workflow_info)

    # FIXED: Tab content with improved state management
    with tabs[0]: # Tutorial Tab
        try:
            error_explorer_ui.render(workflow) 
        except Exception as e:
            logger.error(f"Error in tutorial tab: {str(e)}")
            st.error("Error loading tutorial. Please refresh the page.")

    with tabs[1]: # Generate Tab
        try:
            # FIXED: Better generation blocking logic
            if workflow_info["in_review"] and not workflow_info["can_generate"]:
                st.warning("🔒 " + t("generation_blocked_complete_review"))
                # Show option to view current review
                if st.button(f"📋 {t('go_to_review_tab')}"):
                    st.session_state.active_tab = 2
                    st.rerun()
            else:
                # Check for special practice session completion flow
                if st.session_state.get("practice_session_active", False):
                    error_name = st.session_state.get("practice_error_name", "")
                    st.info(f"🎯 **Practice Session Active** - Practicing with error: **{error_name}**")
                    st.info("💡 A code snippet has been generated for this error. Go to the **Review** tab to start analyzing!")
                
                code_generator_ui.render(user_level)
        except Exception as e:
            logger.error(f"Error in generate tab: {str(e)}")
            st.error("Error in code generation. Please refresh the page.")
    
    with tabs[2]: # Review Tab - FIXED: Improved rendering with better state detection
        try:
            render_improved_review_tab(workflow, code_display_ui, auth_ui, workflow_info)
        except Exception as e:
            logger.error(f"Error in review tab: {str(e)}")
            st.error("Error in review section. Please refresh the page.")
    
    with tabs[3]: # Feedback Tab
        try:
            # Show workflow status if review not complete
            if not workflow_info["review_complete"]:
                st.warning("📋 " + t("complete_review_before_feedback"))
                # Show progress info
                progress_text = f"{t('current')}: {workflow_info['current_iteration']}/{workflow_info['max_iterations']} {t('iterations')}"
                st.info(f"📊 {progress_text}")
                return
                
            render_feedback_tab(workflow, auth_ui)
        except Exception as e:
            logger.error(f"Error in feedback tab: {str(e)}")
            st.error("Error loading feedback. Please refresh the page.")

def render_improved_review_tab(workflow, code_display_ui, auth_ui, workflow_info):
    """
    FIXED: Improved review tab rendering without causing infinite reruns.
    """
    logger.debug(f"Rendering improved review tab with workflow_info: {workflow_info}")
    
    # Check if this is a practice session
    practice_session = st.session_state.get("practice_session_active", False)
    practice_error_name = st.session_state.get("practice_error_name", "")
    
    if practice_session:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #4CAF50, #45a049); color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <h3 style="margin: 0; color: white;">🎯 Practice Session: {practice_error_name}</h3>
            <p style="margin: 0.5rem 0 0 0; color: white;">Review the generated code below and identify the specific error you're practicing with.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # FIXED: Enhanced state checking with multiple validation methods
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.warning("⚙️ " + t("no_workflow_state_available"))
        st.info("💡 " + t("please_generate_code_first"))
        if st.button("🔧 " + t("go_to_generate_tab")):
            st.session_state.active_tab = 1
            st.rerun()
        return
    
    state = st.session_state.workflow_state
    
    # FIXED: Comprehensive code detection with multiple fallback methods
    has_code = False
    code_snippet = None
    
    # Method 1: Check generation_completed flag
    if st.session_state.get("generation_completed", False):
        logger.debug("Code presence confirmed via generation_completed flag")
        has_code = True
        code_snippet = getattr(state, 'code_snippet', None)
    
    # Method 2: Direct code_snippet check
    elif hasattr(state, 'code_snippet') and state.code_snippet:
        code_snippet = state.code_snippet
        # Comprehensive code validation
        if hasattr(code_snippet, 'code') and code_snippet.code:
            if isinstance(code_snippet.code, str) and len(code_snippet.code.strip()) > 0:
                has_code = True
                logger.debug("Code found in code_snippet.code")
        elif hasattr(code_snippet, 'clean_code') and code_snippet.clean_code:
            if isinstance(code_snippet.clean_code, str) and len(code_snippet.clean_code.strip()) > 0:
                has_code = True
                logger.debug("Code found in code_snippet.clean_code")
        elif isinstance(code_snippet, str) and len(code_snippet.strip()) > 0:
            has_code = True
            logger.debug("Code found as direct string")
    
    # Method 3: Check workflow info
    elif workflow_info["has_code"]:
        logger.debug("Code presence confirmed via workflow_info")
        has_code = True
        code_snippet = getattr(state, 'code_snippet', None)
    
    # Debug information for troubleshooting
    logger.debug(f"Review tab state check - has_code: {has_code}, workflow_has_code: {workflow_info['has_code']}, generation_completed: {st.session_state.get('generation_completed', False)}")
    
    # FIXED: Better error handling and user guidance
    if not has_code:
        st.markdown(f"""
        <div class="unavailable-state">
            <div class="state-icon">⚙️</div>
            <h3>{t('no_code_available')}</h3>
            <p>{t('generate_code_snippet_first')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔧 " + t("go_to_generate_tab"), use_container_width=True):
                st.session_state.active_tab = 1
                st.rerun()
        with col2:
            if st.button("🔄 Refresh State", use_container_width=True):
                st.rerun()
        
        return
    
    # FIXED: Check for review completion WITHOUT causing reruns
    if workflow_info["review_complete"]:
        st.success("🎉 " + t("review_completed_successfully"))
        st.info("📊 " + t("check_feedback_tab_for_results"))
        
        # FIXED: Use flags instead of immediate reruns
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📊 " + t("view_feedback"), type="primary", key="view_feedback_btn"):
                st.session_state.should_switch_to_feedback = True
        with col2:
            if st.button("🔄 " + t("start_new_review_cycle"), key="new_cycle_btn"):
                st.session_state.should_start_new_cycle = True
        return  # Important: return here to prevent further processing
    
    # FIXED: Render the actual review interface
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h2 style="color: #495057; margin-bottom: 0.5rem; font-size: 2rem; font-weight: 700;">
            📋 {t('review_java_code')}
        </h2>
        <p style="color: #6c757d; margin: 0; font-size: 1.1rem;">
            {t('carefully_examine_code')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show workflow progress in review
    if workflow_info["in_review"]:
        progress_text = f"📍 {t('review_in_progress')} - {t('iteration')} {workflow_info['current_iteration']}/{workflow_info['max_iterations']}"
        st.info(progress_text)
    
    # FIXED: Display the code with better error handling
    try:
        code_display_ui.render_code_display(code_snippet)
        logger.debug("Code display rendered successfully")
    except Exception as display_error:
        logger.error(f"Error rendering code display: {str(display_error)}")
        st.error(f"Error displaying code: {str(display_error)}")
        
        # Show fallback code display
        if code_snippet:
            try:
                if hasattr(code_snippet, 'clean_code') and code_snippet.clean_code:
                    st.code(code_snippet.clean_code, language="java")
                elif hasattr(code_snippet, 'code') and code_snippet.code:
                    st.code(code_snippet.code, language="java")
                else:
                    st.code(str(code_snippet), language="java")
            except:
                st.error("Could not display code in any format")
        return
    
    # Handle review submission
    try:
        _handle_review_submission_with_workflow_control(workflow, code_display_ui, auth_ui, workflow_info)
    except Exception as submission_error:
        logger.error(f"Error in review submission handling: {str(submission_error)}")
        st.error(f"Error in review submission: {str(submission_error)}")

def render_fixed_review_tab(workflow, code_display_ui, auth_ui, workflow_info):
    """
    FIXED: Review tab rendering with proper logic and better error handling.
    """
    logger.debug(f"Rendering review tab with workflow_info: {workflow_info}")
    
    # Check if this is a practice session
    practice_session = st.session_state.get("practice_session_active", False)
    practice_error_name = st.session_state.get("practice_error_name", "")
    
    if practice_session:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #4CAF50, #45a049); color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <h3 style="margin: 0; color: white;">🎯 Practice Session: {practice_error_name}</h3>
            <p style="margin: 0.5rem 0 0 0; color: white;">Review the generated code below and identify the specific error you're practicing with.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # FIXED: Better state checking
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.warning("⚙️ " + t("no_workflow_state_available"))
        st.info("💡 " + t("please_generate_code_first"))
        return
    
    state = st.session_state.workflow_state
    
    # FIXED: Check for code existence with multiple methods
    has_code = False
    code_snippet = None
    
    if hasattr(state, 'code_snippet') and state.code_snippet:
        code_snippet = state.code_snippet
        # Check if code snippet has content
        if hasattr(code_snippet, 'code') and code_snippet.code:
            if isinstance(code_snippet.code, str) and len(code_snippet.code.strip()) > 0:
                has_code = True
                logger.debug("Code found in code_snippet.code")
        elif hasattr(code_snippet, 'clean_code') and code_snippet.clean_code:
            if isinstance(code_snippet.clean_code, str) and len(code_snippet.clean_code.strip()) > 0:
                has_code = True
                logger.debug("Code found in code_snippet.clean_code")
    
    # Debug information
    logger.debug(f"Review tab state check - has_code: {has_code}, workflow_has_code: {workflow_info['has_code']}")
    
    # FIXED: Show appropriate message based on state
    if not has_code and not workflow_info["has_code"]:
        st.markdown(f"""
        <div class="unavailable-state">
            <div class="state-icon">⚙️</div>
            <h3>{t('no_code_available')}</h3>
            <p>{t('generate_code_snippet_first')}</p>
            <div class="action-hint">
                <button onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', data: 1}}, '*')">
                    👈 {t('go_to_generate_tab')}
                </button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔧 " + t("go_to_generate_tab")):
            st.session_state.active_tab = 1
            st.rerun()
        return
    
    # FIXED: If workflow says we have code but we can't find it, try to recover
    if workflow_info["has_code"] and not has_code:
        st.warning("⚠️ Code state inconsistency detected. Attempting to recover...")
        
        # Try to show what we can find
        if hasattr(state, 'code_snippet'):
            st.info("Found code_snippet object, displaying available content:")
            if hasattr(state.code_snippet, '__dict__'):
                st.json(state.code_snippet.__dict__)
        
        # Show debug button
        if st.button("🔧 Show Full State Debug"):
            st.json({
                "has_workflow_state": hasattr(st.session_state, 'workflow_state'),
                "workflow_state_type": type(st.session_state.workflow_state).__name__ if hasattr(st.session_state, 'workflow_state') else None,
                "has_code_snippet": hasattr(state, 'code_snippet') if state else False,
                "code_snippet_type": type(state.code_snippet).__name__ if hasattr(state, 'code_snippet') and state.code_snippet else None,
                "workflow_info": workflow_info
            })
        return
    
    # FIXED: Check for review completion
    if workflow_info["review_complete"]:
        st.success("🎉 " + t("review_completed_successfully"))
        st.info("📊 " + t("check_feedback_tab_for_results"))
        
        # Option to start new cycle
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📊 " + t("view_feedback"), type="primary"):
                st.session_state.active_tab = 3
                st.rerun()
        with col2:
            if st.button("🔄 " + t("start_new_review_cycle")):
                workflow_controller.reset_workflow_for_new_cycle()
                st.session_state.active_tab = 1  # Go to generate tab
                st.rerun()
        return
    
    # FIXED: Render the actual review interface
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h2 style="color: #495057; margin-bottom: 0.5rem; font-size: 2rem; font-weight: 700;">
            📋 {t('review_java_code')}
        </h2>
        <p style="color: #6c757d; margin: 0; font-size: 1.1rem;">
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
        code_display_ui.render_code_display(code_snippet)
        logger.debug("Code display rendered successfully")
    except Exception as display_error:
        logger.error(f"Error rendering code display: {str(display_error)}")
        st.error(f"Error displaying code: {str(display_error)}")
        return
    
    # Handle review submission
    try:
        _handle_review_submission_with_workflow_control(workflow, code_display_ui, auth_ui, workflow_info)
    except Exception as submission_error:
        logger.error(f"Error in review submission handling: {str(submission_error)}")
        st.error(f"Error in review submission: {str(submission_error)}")

def _handle_review_submission_with_workflow_control(workflow, code_display_ui, auth_ui, workflow_info):
    """FIXED: Handle review submission with proper workflow control."""
    
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
            
            # FIXED: Check if review is complete and set flag instead of immediate redirect
            review_sufficient = getattr(updated_state, 'review_sufficient', False)
            new_iteration = getattr(updated_state, 'current_iteration', 1)
            
            if review_sufficient or new_iteration > max_iterations:
                logger.debug("Review completed, setting flag for feedback tab switch")
                st.session_state.should_switch_to_feedback = True
                
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