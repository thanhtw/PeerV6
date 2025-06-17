"""
Fixed Enhanced Leaderboard Rendering - Resolves HTML display issues
"""

import streamlit as st
import logging
import html # Added for escaping
from typing import Dict, Any, List
from analytics.badge_manager import BadgeManager
from utils.language_utils import t, get_current_language

logger = logging.getLogger(__name__)

class ProfileLeaderboardSidebar:
    """Fixed enhanced combined profile and leaderboard sidebar component."""
    
    def __init__(self):
        self.badge_manager = BadgeManager()
    
    def render_combined_sidebar(self, user_info: Dict[str, Any], user_id: str) -> None:
        """
        Render enhanced combined user profile and leaderboard with fixed HTML rendering.
        """
        try:
            
            # Extract user data
            display_name, level, reviews_completed, total_points = self._extract_user_data(user_info)
            
            # Get user badges and rank
            user_badges = self.badge_manager.get_user_badges(user_id)[:4]
            user_rank_info = self.badge_manager.get_user_rank(user_id)
            leaders = self.badge_manager.get_leaderboard_with_badges(8)
            
            # Render profile section
            self._render_profile_section(display_name, level, reviews_completed, 
                                             total_points, user_badges, user_rank_info)
            
            # Render leaderboard section with proper error handling
            if leaders:
                self._render_leaderboard_section(leaders, user_id)
            else:
                st.info(f"{t('no_leaderboard_data')}")
                
        except Exception as e:
            logger.error(f"Error rendering enhanced sidebar: {str(e)}")

    def _extract_user_data(self, user_info: Dict[str, Any]) -> tuple:
        """
        Extract user data with language support.
        FIXED: Returns total_points instead of score.
        """
        current_lang = get_current_language()
        display_name = user_info.get(f"display_name_{current_lang}", 
                                user_info.get("display_name", "User"))
        level = user_info.get(f"level_name_{current_lang}", 
                            user_info.get("level", "basic")).capitalize()
        # Use get() with default values to handle missing fields
        reviews_completed = user_info.get("reviews_completed", 0)
        
        # FIXED: Use total_points instead of score
        total_points = user_info.get("total_points", 0)
        
        return display_name, level, reviews_completed, total_points
    
    def _render_profile_section(self, display_name: str, level: str, 
                                    reviews_completed: int, total_points: int, 
                                    user_badges: List[Dict], user_rank_info: Dict) -> None:
        """
        Render profile section with total points display.
        FIXED: Uses total_points instead of score in display.
        """
        
        # Get user avatar (first letter)
        avatar_letter = display_name[0].upper() if display_name else "U"
        
        # Build badge HTML safely
        badge_html = ""
        if user_badges:
            for badge in user_badges[:4]:  # Limit to 4 badges
                icon = badge.get("icon", "🏅")
                badge_name = badge.get("name", "Badge") # Assume 'name' key exists
                escaped_badge_name = html.escape(badge_name)
                badge_html += f'<span class="badge-icon-fixed" title="{escaped_badge_name}">{icon}</span>'
        else:
            badge_html = '<span class="badge-icon-fixed">🏅</span>'
        
        # Profile HTML - FIXED: Display total_points with proper label
        profile_html = f'''
        <div class="sidebar-container">
            <div class="enhanced-profile-card">
                <div class="profile-header-enhanced">
                    <div class="profile-avatar">{avatar_letter}</div>
                    <div class="profile-name-enhanced">{display_name}</div>
                    <div class="profile-level-enhanced">{level}</div>
                    <div class="badge-showcase-fixed">
                        {badge_html}
                    </div>
                </div>
                <div class="stats-grid-enhanced">
                    <div class="stats-row">
                        <div class="stat-item-enhanced">
                            <div class="stat-value-enhanced">{reviews_completed}</div>
                            <div class="stat-label-enhanced">{t("review_times")}</div>
                        </div>
                        <div class="stat-item-enhanced">
                            <div class="stat-value-enhanced">{total_points:,}</div>
                            <div class="stat-label-enhanced">{t("total_points")}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
        # Render profile with error handling
        try:
            st.markdown(profile_html, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error rendering profile HTML: {str(e)}")
            # Fallback to simple display with total points
            st.markdown(f"**{display_name}** ({level})")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(t("reviews"), reviews_completed)
            with col2:
                st.metric(t("total_points"), f"{total_points:,}")
    
    def _render_leaderboard_section(self, leaders: List[Dict], user_id: str) -> None:
        """
        Render leaderboard with total points instead of score.
        FIXED: Uses total_points for leaderboard ranking.
        """
        
        try:
            
            # Build the leaderboard HTML in smaller, safer chunks
            header_html = f'''
            <div class="leaderboard-container-enhanced">
                <div class="leaderboard-header-enhanced">
                    🏆 {t('top_performers')}
                </div>
                <div class="leaderboard-list">
            '''
            
            # Render header first
            st.markdown(header_html, unsafe_allow_html=True)
            
            # Build items HTML safely - FIXED: Use total_points
            items_html = ""
            for i, leader in enumerate(leaders[:6]):  # Show top 6
                rank = leader.get("rank", i + 1)
                usname = leader.get("display_name", "Unknown")[:10]  # Truncate long names
                level = leader.get("level", "basic").capitalize()
                
                # FIXED: Use total_points instead of points or score
                total_points = leader.get("total_points", 0)
                
                badges = leader.get("top_badges", [])[:3]
                is_current = leader.get("uid") == user_id
                
                # Get rank display and styling
                if rank == 1:
                    rank_display = "🥇"
                    rank_class = "rank-1"
                elif rank == 2:
                    rank_display = "🥈"
                    rank_class = "rank-2"
                elif rank == 3:
                    rank_display = "🥉"
                    rank_class = "rank-3"
                else:
                    rank_display = str(rank)
                    rank_class = ""
                
                # Get badge icons
                badge_icons_html = ""
                for badge_item in badges:
                    icon = badge_item.get("icon", "🏅")
                    name = badge_item.get("name", "Badge")
                    escaped_name = html.escape(name)
                    badge_icons_html += f'<span class="badge-icon-fixed" title="{escaped_name}">{icon}</span>'
                
                
                # Current user styling
                current_class = "current-user-enhanced" if is_current else ""
                current_indicator = '<span class="current-user-indicator-enhanced">(You)</span>' if is_current else ""
                
                # Build individual item HTML - FIXED: Display total_points
                user_name_parts = [
                    html.escape(str(usname)), # Ensure name is string before escape
                    f'<span class="user-level-tag">{html.escape(str(level))}</span>' # Ensure level is string
                ]
                if current_indicator: # current_indicator is already HTML string or empty string
                    user_name_parts.append(current_indicator)
                
                user_name_content = "".join(user_name_parts)

                item_html_parts = [
                    f'<div class="leaderboard-item-enhanced {current_class}">',
                    f'    <div class="rank-position-enhanced {rank_class}">{rank_display}</div>', # rank_display is emoji or str(num)
                    f'    <div class="user-info-enhanced">',
                    f'        <div class="user-name-enhanced">',
                    f'            {user_name_content}',
                    f'        </div>',
                    f'        <div class="user-badges-enhanced">{badge_icons_html}</div>', # Use the generated HTML directly
                    f'    </div>',
                    f'    <div class="user-points-enhanced">',
                    f'        <div class="points-number">{total_points:,}</div>', # FIXED: total_points
                    f'        <div class="points-label">{html.escape(t("total_points"))}</div>', # FIXED: total_points label
                    f'    </div>',
                    f'</div>'
                ]
                item_html = "\n".join(item_html_parts)
                items_html += item_html
            
            # Render items
            st.markdown(items_html, unsafe_allow_html=True)
            
            # Close container and add button
            footer_html = f'''
                </div>
                <button class="view-full-btn" onclick="alert('Feature coming soon!')">
                    📊 {t('view_full_leaderboard')}
                </button>
            </div>
            '''
            
            st.markdown(footer_html, unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Error rendering styled leaderboard: {str(e)}")
            
            
    

    