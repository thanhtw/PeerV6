"""
Enhanced UI package for Java Peer Review Training System.

This package contains professional UI components for the Streamlit interface
with improved styling, better i18n support, and enhanced user experience.
"""

# Core UI components
from ui.components.code_generator import CodeGeneratorUI
from ui.components.code_display import CodeDisplayUI
from ui.components.feedback_system import FeedbackSystem
from ui.components.auth_ui import AuthUI
from ui.components.profile_leaderboard import ProfileLeaderboardSidebar


__all__ = [
    # Core components
    'CodeGeneratorUI',
    'CodeDisplayUI', 
    'FeedbackSystem',
    'AuthUI'
        
    # UI utilities - compact and professional  
    'render_sidebar',
    'ProfileLeaderboardSidebar'
]