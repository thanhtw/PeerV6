"""
Updated Main Application with Simplified 2-Tab Structure
This replaces the existing main application logic for tab management.
"""

import streamlit as st
import logging
from typing import Dict, Any
from ui.components.unified_practice import UnifiedPracticeUI
from ui.components.tutorial import TutorialUI
from ui.components.auth_ui import AuthUI
from utils.language_utils import t, get_current_language
from utils.session_state_manager import session_state_manager
from static.css_utils import load_css_safe

logger = logging.getLogger(__name__)

class SimplifiedMainApp:
    """
    Simplified main application with only 2 tabs: Tutorial and Practice.
    Combines the old Generate, Review, and Feedback tabs into a single Practice tab.
    """
    
    def __init__(self, workflow, llm_manager):
        """Initialize the simplified main application."""
        self.workflow = workflow
        self.llm_manager = llm_manager
        
        # Initialize UI components
        self.auth_ui = AuthUI()
        self.tutorial_ui = TutorialUI(workflow)
        self.unified_practice_ui = UnifiedPracticeUI(workflow, self.auth_ui)
        
        # Initialize session state
        self._initialize_session_state()
        
        # Load CSS
        self._load_css()
    
    def _initialize_session_state(self):
        """Initialize session state for the simplified application."""
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = 0  # Start with Tutorial
        if "app_initialized" not in st.session_state:
            st.session_state.app_initialized = True
            # Ensure scroll to top on app initialization
            st.session_state.scroll_to_top = True
    
    def _load_css(self):
        """Load CSS styles for the application."""
        try:
            import os
            css_dir = os.path.join(os.path.dirname(__file__), "..", "static", "css")
            result = load_css_safe(css_directory=css_dir)
            
            if result['success']:
                logger.debug(f"Loaded CSS files: {result['loaded_files']}")
            else:
                logger.warning(f"CSS loading issues: {result['errors']}")
                
        except Exception as e:
            logger.error(f"Error loading CSS: {str(e)}")
    
    def run(self):
        """Run the simplified main application."""
        # Handle authentication
        if not self._handle_authentication():
            return
        
        # Handle page configuration
        self._configure_page()
        
        # Handle scroll to top
        self._handle_scroll_to_top()
        
        # Render main interface
        self._render_main_interface()
        
        # Handle cleanup
        self._handle_cleanup()
    
    def _handle_authentication(self) -> bool:
        """Handle user authentication."""
        if not self.auth_ui.is_authenticated():
            # Show authentication page
            authenticated = self.auth_ui.render_auth_page()
            if not authenticated:
                return False
        
        # Render sidebar for authenticated users
        self.auth_ui.render_combined_profile_leaderboard()
        return True
    
    def _configure_page(self):
        """Configure page settings."""
        current_language = get_current_language()
        
        # Set page title based on language
        page_title = t("app_title")
        st.set_page_config(
            page_title=page_title,
            page_icon="☕",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def _handle_scroll_to_top(self):
        """Handle scrolling to top after page loads/reruns."""
        # Always scroll to top after rerun to ensure consistent user experience
        st.markdown("""
        <script>
        // Scroll to top immediately
        setTimeout(function() {
            window.scrollTo(0, 0);
            if (document.querySelector('.main')) {
                document.querySelector('.main').scrollTop = 0;
            }
            if (document.querySelector('[data-testid="stAppViewContainer"]')) {
                document.querySelector('[data-testid="stAppViewContainer"]').scrollTop = 0;
            }
        }, 100);
        </script>
        """, unsafe_allow_html=True)
        
        # Clear scroll flag if set
        if st.session_state.get("scroll_to_top", False):
            st.session_state.scroll_to_top = False
    
    def _render_main_interface(self):
        """Render the main interface with simplified tab structure."""
        # Application header
        self._render_app_header()
        
        # Create simplified tab structure
        tab_labels = [
            f"🔍 {t('tutorial')}",
            f"🎯 {t('practice')}"
        ]
        
        # Create tabs
        tabs = st.tabs(tab_labels)
        
        # Handle tab content
        with tabs[0]:  # Tutorial Tab
            self._render_tutorial_tab()
        
        with tabs[1]:  # Practice Tab
            self._render_practice_tab()
        
        # Update active tab tracking
        self._update_active_tab_tracking()
    
    def _render_app_header(self):
        """Render application header."""
        current_language = get_current_language()
        user_info = st.session_state.auth.get("user_info", {})
        user_level = user_info.get(f"level_name_{current_language}", user_info.get("level", "medium"))
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        ">
            <h1 style="margin: 0 0 0.5rem 0; font-size: 2.5rem; color: white;">
                ☕ {t('app_title')}
            </h1>
            <p style="margin: 0; font-size: 1.2rem; opacity: 0.9; color: white;">
                {t('app_subtitle')} | {t('level')}: {user_level}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_tutorial_tab(self):
        """Render the tutorial/error explorer tab."""
        try:
            # Add tab-specific styling
            st.markdown(f"""
            <div class="tab-content tutorial-tab">
                <div style="margin-bottom: 1rem;">
                    <h2 style="color: #495057; margin-bottom: 0.5rem;">
                        🔍 {t('error_explorer')}
                    </h2>
                    <p style="color: #6c757d; margin: 0;">
                        {t('explore_and_practice_specific_errors')}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Render tutorial UI
            self.tutorial_ui.render(self.workflow)
            
        except Exception as e:
            logger.error(f"Error rendering tutorial tab: {str(e)}")
            st.error(f"❌ {t('error_loading_tutorial')}: {str(e)}")
    
    def _render_practice_tab(self):
        """Render the unified practice tab."""
        try:
            # Add tab-specific styling
            st.markdown(f"""
            <div class="tab-content practice-tab">
                <div style="margin-bottom: 1rem;">
                    <h2 style="color: #495057; margin-bottom: 0.5rem;">
                        🎯 {t('practice_workflow')}
                    </h2>
                    <p style="color: #6c757d; margin: 0;">
                        {t('complete_full_practice_workflow')}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Get user level for practice
            user_info = st.session_state.auth.get("user_info", {})
            current_language = get_current_language()
            user_level = user_info.get(f"level_name_{current_language}", user_info.get("level", "medium"))
            
            # Render unified practice UI
            self.unified_practice_ui.render(user_level)
            
        except Exception as e:
            logger.error(f"Error rendering practice tab: {str(e)}")
            st.error(f"❌ {t('error_loading_practice')}: {str(e)}")
            
            # Show fallback interface
            st.info(f"🔧 {t('practice_interface_loading')}")
            if st.button(f"🔄 {t('refresh_page')}", key="refresh_practice"):
                st.rerun()
    
    def _update_active_tab_tracking(self):
        """Update active tab tracking for session management."""
        # This is handled automatically by Streamlit's tab selection
        # We can add custom tracking here if needed for analytics
        pass
    
    def _handle_cleanup(self):
        """Handle session cleanup and maintenance."""
        try:
            # Clean up expired session state locks
            session_state_manager.cleanup_expired_locks()
            
            # Handle full reset if requested
            if st.session_state.get("full_reset", False):
                self._handle_full_reset()
            
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
    
    def _handle_full_reset(self):
        """Handle full application reset."""
        try:
            # Preserve authentication and core settings
            preserved_keys = [
                "auth", "app_initialized", "language", "active_tab"
            ]
            
            preserved_values = {}
            for key in preserved_keys:
                if key in st.session_state:
                    preserved_values[key] = st.session_state[key]
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                if key not in preserved_keys:
                    del st.session_state[key]
            
            # Restore preserved values
            for key, value in preserved_values.items():
                st.session_state[key] = value
            
            # Reset flags
            st.session_state.full_reset = False
            st.session_state.scroll_to_top = True
            
            logger.info("Full application reset completed")
            st.success(f"✅ {t('application_reset_complete')}")
            
        except Exception as e:
            logger.error(f"Error during full reset: {str(e)}")
            st.error(f"❌ {t('reset_error')}: {str(e)}")

def create_simplified_main_app(workflow, llm_manager):
    """
    Factory function to create and configure the simplified main application.
    
    Args:
        workflow: The workflow manager instance
        llm_manager: The LLM manager instance
        
    Returns:
        SimplifiedMainApp instance
    """
    return SimplifiedMainApp(workflow, llm_manager)