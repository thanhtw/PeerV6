"""
Integration module for connecting the enhanced badge system 
with the review workflow completion.

This module should be added to the workflow/node.py file.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from analytics.badge_manager import BadgeManager
from utils.language_utils import t

logger = logging.getLogger(__name__)

class WorkflowBadgeIntegrator:
    """Integrates badge system with workflow completion."""
    
    def __init__(self):
        self.badge_manager = BadgeManager()
    
    def process_review_completion_with_badges(self, state, user_id: str) -> Dict[str, Any]:
        """
        Process review completion and handle badge awards.
        This should be called after a review is analyzed and marked as complete.
        
        Args:
            state: WorkflowState containing review completion data
            user_id: The user's ID
            
        Returns:
            Dictionary containing badge results and statistics
        """
        try:
            if not user_id:
                logger.warning("No user_id provided for badge processing")
                return {"success": False, "error": "No user ID"}
            
            # Extract review completion data from state
            review_data = self._extract_review_data_from_state(state)
            
            if not review_data:
                logger.warning("Could not extract review data from workflow state")
                return {"success": False, "error": "No review data"}
            
            # Process through enhanced badge manager
            logger.info(f"Processing badge awards for user {user_id}")
            result = self.badge_manager.process_review_completion(user_id, review_data)
            
            # Log awarded badges for debugging
            if result.get('success') and result.get('awarded_badges'):
                badge_names = [badge.get('name', 'Unknown') for badge in result['awarded_badges']]
                logger.info(f"Awarded badges to {user_id}: {', '.join(badge_names)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in workflow badge integration: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_review_data_from_state(self, state) -> Optional[Dict[str, Any]]:
        """Extract review completion data from workflow state."""
        try:
            if not hasattr(state, 'review_history') or not state.review_history:
                logger.warning("No review history in state")
                return None
            
            # Get the latest completed review
            latest_review = state.review_history[-1]
            
            if not hasattr(latest_review, 'analysis') or not latest_review.analysis:
                logger.warning("No analysis in latest review")
                return None
            
            analysis = latest_review.analysis
            
            # Extract key metrics
            accuracy_percentage = analysis.get(t('accuracy_percentage'), 
                                             analysis.get(t('identified_percentage'), 0.0))
            identified_count = analysis.get(t('identified_count'), 0)
            total_problems = analysis.get(t('total_problems'), 
                                        getattr(state, 'original_error_count', 1))
            
            # Get timing information (if available)
            time_spent_seconds = self._calculate_session_time(state)
            
            # Get difficulty and other metadata
            code_difficulty = getattr(state, 'difficulty_level', 'medium')
            review_iterations = getattr(state, 'current_iteration', 1)
            
            # Determine session type
            session_type = 'regular'
            practice_error_code = None
            
            # Check if this is a practice session
            if hasattr(state, 'selected_specific_errors') and state.selected_specific_errors:
                if len(state.selected_specific_errors) == 1:
                    session_type = 'practice'
                    error = state.selected_specific_errors[0]
                    practice_error_code = error.get('error_code', error.get('name', ''))
            
            # Extract categories encountered
            categories_encountered = self._extract_categories_from_state(state)
            
            review_data = {
                'accuracy_percentage': float(accuracy_percentage),
                'identified_count': int(identified_count),
                'total_problems': int(total_problems),
                'time_spent_seconds': int(time_spent_seconds),
                'session_type': session_type,
                'practice_error_code': practice_error_code,
                'code_difficulty': code_difficulty,
                'review_iterations': int(review_iterations),
                'categories_encountered': categories_encountered,
                'review_sufficient': getattr(state, 'review_sufficient', False),
                'all_errors_found': identified_count == total_problems and total_problems > 0
            }
            
            logger.debug(f"Extracted review data: {review_data}")
            return review_data
            
        except Exception as e:
            logger.error(f"Error extracting review data: {str(e)}")
            return None
    
    def _calculate_session_time(self, state) -> int:
        """Calculate total session time from workflow state."""
        try:
            # Try to get from session state if available
            import streamlit as st
            if hasattr(st, 'session_state'):
                start_time = st.session_state.get('workflow_start_time')
                if start_time:
                    return int(time.time() - start_time)
            
            # Fallback: estimate based on iterations
            current_iteration = getattr(state, 'current_iteration', 1)
            estimated_time_per_iteration = 180  # 3 minutes per iteration
            return current_iteration * estimated_time_per_iteration
            
        except Exception as e:
            logger.warning(f"Could not calculate session time: {str(e)}")
            return 0
    
    def _extract_categories_from_state(self, state) -> List[str]:
        """Extract error categories from workflow state."""
        try:
            categories = []
            
            # From selected categories
            if hasattr(state, 'selected_error_categories'):
                java_errors = state.selected_error_categories.get('java_errors', [])
                categories.extend(java_errors)
            
            # From specific errors
            if hasattr(state, 'selected_specific_errors'):
                for error in state.selected_specific_errors:
                    if isinstance(error, dict):
                        category = error.get('category', error.get('type', ''))
                        if category and category not in categories:
                            categories.append(category)
            
            # From code snippet raw errors
            if hasattr(state, 'code_snippet') and state.code_snippet:
                if hasattr(state.code_snippet, 'raw_errors'):
                    raw_errors = state.code_snippet.raw_errors
                    if isinstance(raw_errors, dict) and 'java_errors' in raw_errors:
                        for error in raw_errors['java_errors']:
                            if isinstance(error, dict):
                                category = error.get('category', error.get('type', ''))
                                if category and category not in categories:
                                    categories.append(category)
            
            logger.debug(f"Extracted categories: {categories}")
            return categories
            
        except Exception as e:
            logger.error(f"Error extracting categories: {str(e)}")
            return []

# =================================================================
# WORKFLOW NODE INTEGRATION
# =================================================================

def integrate_badge_system_into_workflow_nodes():
    """
    Integration function to add to workflow/node.py
    
    Add this method to the WorkflowNodes class in workflow/node.py
    """
    def generate_comparison_report_node_with_badges(self, state):
        """
        Enhanced comparison report node that also processes badges.
        This replaces the existing generate_comparison_report_node method.
        """
        try:
            logger.debug("PHASE 3: Generating comparison report with badge processing")
            
            # Original comparison report generation logic
            original_result = self.generate_comparison_report_node_original(state)
            
            # Process badges if user is authenticated
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and 'auth' in st.session_state:
                    user_id = st.session_state.auth.get('user_id')
                    
                    if user_id and user_id != 'demo_user':
                        # Initialize badge integrator
                        badge_integrator = WorkflowBadgeIntegrator()
                        
                        # Process badge awards
                        badge_result = badge_integrator.process_review_completion_with_badges(
                            state, user_id
                        )
                        
                        # Store badge results in state for UI display
                        if badge_result.get('success'):
                            # Add badge information to state
                            if not hasattr(state, 'badge_awards'):
                                state.badge_awards = {}
                            
                            state.badge_awards = {
                                'awarded_badges': badge_result.get('awarded_badges', []),
                                'points_awarded': badge_result.get('points_awarded', 0),
                                'total_badges_awarded': badge_result.get('total_badges_awarded', 0)
                            }
                            
                            logger.info(f"Badge processing completed: {badge_result.get('total_badges_awarded', 0)} badges awarded")
                        else:
                            logger.warning(f"Badge processing failed: {badge_result.get('error', 'Unknown error')}")
                    else:
                        logger.debug("Skipping badge processing for demo user or unauthenticated user")
                else:
                    logger.debug("No authenticated user found for badge processing")
                    
            except Exception as badge_error:
                logger.error(f"Error in badge processing: {str(badge_error)}")
                # Don't fail the workflow if badge processing fails
                pass
            
            return original_result
            
        except Exception as e:
            logger.error(f"Error in enhanced comparison report node: {str(e)}")
            return state

# =================================================================
# FEEDBACK SYSTEM INTEGRATION
# =================================================================

def integrate_badge_display_into_feedback_system():
    """
    Integration for displaying newly awarded badges in the feedback system.
    
    Add this to ui/components/feedback_system.py
    """
    def render_newly_awarded_badges(self, state):
        """Render newly awarded badges in the feedback tab."""
        try:
            if not hasattr(state, 'badge_awards') or not state.badge_awards:
                return
            
            badge_awards = state.badge_awards
            awarded_badges = badge_awards.get('awarded_badges', [])
            points_awarded = badge_awards.get('points_awarded', 0)
            
            if not awarded_badges and points_awarded == 0:
                return
            
            import streamlit as st
            
            # Celebration header for new badges
            if awarded_badges:
                st.markdown(f"""
                <div class="badge-celebration-container">
                    <div class="celebration-header">
                        <h3>🎉 {t('new_badges_earned')}!</h3>
                        <p>{t('congratulations_on_earning')} {len(awarded_badges)} {t('new_badges')}!</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Display new badges
                cols = st.columns(min(len(awarded_badges), 3))
                for i, badge in enumerate(awarded_badges):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="new-badge-card">
                            <div class="badge-icon-large">{badge.get('icon', '🏅')}</div>
                            <div class="badge-name-large">{badge.get('name', 'New Badge')}</div>
                            <div class="badge-description-small">{badge.get('description', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Celebration effects
                st.balloons()
            
            # Points summary
            if points_awarded > 0:
                st.markdown(f"""
                <div class="points-award-summary">
                    <span class="points-icon">⭐</span>
                    <span>{t('points_earned')}: <strong>{points_awarded}</strong></span>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            logger.error(f"Error rendering newly awarded badges: {str(e)}")

# =================================================================
# CSS STYLES FOR BADGE DISPLAY
# =================================================================

def get_badge_celebration_css():
    """CSS styles for badge celebration display."""
    return """
    <style>
    .badge-celebration-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
        text-align: center;
    }
    
    .celebration-header h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
    }
    
    .celebration-header p {
        margin: 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    .new-badge-card {
        background: linear-gradient(145deg, #f0f0f0, #ffffff);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border: 2px solid #ffd700;
        animation: badgeGlow 2s ease-in-out infinite alternate;
    }
    
    .badge-icon-large {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .badge-name-large {
        font-weight: bold;
        font-size: 1.2rem;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .badge-description-small {
        font-size: 0.9rem;
        color: #666;
        line-height: 1.3;
    }
    
    .points-award-summary {
        background: #28a745;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
        font-size: 1.1rem;
    }
    
    .points-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
    }
    
    @keyframes badgeGlow {
        0% { box-shadow: 0 4px 8px rgba(255,215,0,0.3); }
        100% { box-shadow: 0 4px 16px rgba(255,215,0,0.6); }
    }
    </style>
    """