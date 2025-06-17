"""
Enhanced Badge Manager with Comprehensive Decision System
for Java Peer Review Training System.

This module handles all badge-related decisions after review completion.
"""

import logging
import datetime
import json
from typing import Dict, Any, List, Optional, Tuple
from data.mysql_connection import MySQLConnection
from utils.language_utils import get_current_language, t

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BadgeManager:
    """Enhanced manager for badges, points, and comprehensive user progress tracking."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(BadgeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Enhanced Badge Manager."""
        if self._initialized:
            return
            
        self.db = MySQLConnection()
        self._initialized = True
        self.current_language = get_current_language()
        
        # Badge criteria thresholds
        self.BADGE_CRITERIA = {
            'perfect_review_threshold': 5,
            'consecutive_perfect_threshold': 3,
            'mastery_threshold': 85.0,
            'consistency_days': 5,
            'speed_threshold_seconds': 120,
            'accuracy_for_speed': 80.0,
            'rising_star_points': 500,
            'rising_star_days': 7
        }
    
    def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all badges earned by a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of badge dictionaries with badge details
        """
        if not user_id:
            return []
        
        # Update current language
        self.current_language = get_current_language()
        
        try:
            # Use language-specific field based on current language
            name_field = f"name_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "description_en"
            
            query = f"""
                SELECT b.badge_id, b.{name_field} as name, b.{desc_field} as description, 
                       b.icon, b.category, b.difficulty, b.points, ub.awarded_at
                FROM badges b
                JOIN user_badges ub ON b.badge_id = ub.badge_id
                WHERE ub.user_id = %s
                ORDER BY ub.awarded_at DESC
            """
            
            badges = self.db.execute_query(query, (user_id,))
            print(f"\nRetrieved {badges} badges for user {user_id}")
            return badges or []
                
        except Exception as e:
            logger.error(f"{t('error_getting_user_badges')}: {str(e)}")
            return []

    def get_user_rank(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's rank on the leaderboard.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing rank and total users
        """
        if not user_id:
            return {"rank": 0, "total_users": 0}
        
        try:
            # Get the user's points
            points_query = "SELECT total_points FROM users WHERE uid = %s"
            result = self.db.execute_query(points_query, (user_id,), fetch_one=True)
            
            if not result:
                return {"rank": 0, "total_users": 0}
            
            points = result.get("total_points", 0)
            
            # Get the user's rank
            rank_query = """
                SELECT COUNT(*) AS rank_pos
                FROM users
                WHERE total_points > %s
            """
            
            rank_result = self.db.execute_query(rank_query, (points,), fetch_one=True)
            
            # Get total users
            total_query = "SELECT COUNT(*) AS total FROM users"
            total_result = self.db.execute_query(total_query, fetch_one=True)
            
            return {
                "rank": rank_result.get("rank_pos", 0) + 1,
                "total_users": total_result.get("total", 0)
            }
                
        except Exception as e:
            logger.error(f"{t('error_getting_user_rank')}: {str(e)}")
            return {"rank": 0, "total_users": 0}

    def get_leaderboard_with_badges(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the user leaderboard with badge icons for display.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of user dictionaries with badge icons and ranking
        """
        try:
            # Update current language
            self.current_language = get_current_language()
            
            # Set display name and level fields based on language
            display_name_field = f"display_name_{self.current_language}" if self.current_language in ["en", "zh"] else "display_name_en"
            level_field = f"level_name_{self.current_language}" if self.current_language in ["en", "zh"] else "level_name_en"
            
            # Build query with appropriate fields
            query = f"""
                SELECT uid, {display_name_field} as display_name, total_points, {level_field} as level,
                    (SELECT COUNT(*) FROM user_badges WHERE user_id = uid) AS badge_count
                FROM users
                WHERE total_points > 0
                ORDER BY total_points DESC
                LIMIT %s
            """
            
            leaders = self.db.execute_query(query, (limit,))
            
            if not leaders:
                return []
            
            # Add rank and get top badges for each user
            for i, leader in enumerate(leaders, 1):
                leader["rank"] = i
                
                # Get top 3 badges for this user
                badge_query = f"""
                    SELECT b.icon, b.{f"name_{self.current_language}" if self.current_language in ["en", "zh"] else "name_en"} as name,
                        b.category, b.difficulty
                    FROM badges b
                    JOIN user_badges ub ON b.badge_id = ub.badge_id
                    WHERE ub.user_id = %s
                    ORDER BY 
                        CASE b.difficulty 
                            WHEN 'hard' THEN 3 
                            WHEN 'medium' THEN 2 
                            WHEN 'easy' THEN 1 
                            ELSE 0 
                        END DESC,
                        ub.awarded_at DESC
                    LIMIT 3
                """
                
                badges = self.db.execute_query(badge_query, (leader["uid"],))
                leader["top_badges"] = badges or []
                    
            return leaders
                
        except Exception as e:
            logger.error(f"{t('error_getting_leaderboard')}: {str(e)}")
            return []

    def process_review_completion(self, user_id: str, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: Process completed review and handle all badge decisions.
        
        Args:
            user_id: The user's ID
            review_data: Dictionary containing review completion data
                - accuracy_percentage: float
                - identified_count: int 
                - total_problems: int
                - time_spent_seconds: int
                - session_type: str ('practice', 'regular', 'tutorial')
                - practice_error_code: str (optional)
                - code_difficulty: str
                - review_iterations: int
                - categories_encountered: List[str]
        
        Returns:
            Dict containing awarded badges and updated statistics
        """
        try:
            logger.info(f"Processing review completion for user {user_id}")
            
            # 1. Store review session data
            session_id = self._store_review_session(user_id, review_data)
            
            # 2. Update user statistics
            self._update_user_statistics(user_id, review_data)
            
            # 3. Update category statistics
            self._update_category_statistics(user_id, review_data)
            
            # 4. Update streaks
            self._update_user_streaks(user_id, review_data)
            
            # 5. Award points for the review
            points_awarded = self._calculate_and_award_points(user_id, review_data)
            
            # 6. Update badge progress for all relevant badges
            self._update_all_badge_progress(user_id, review_data)

            # 7. Check and award badges
            awarded_badges = self._check_and_award_all_badges(user_id, review_data)
            
            # 8. Update badge check timestamp
            self._update_badge_check_timestamp(user_id)
            
            result = {
                'success': True,
                'session_id': session_id,
                'points_awarded': points_awarded,
                'awarded_badges': awarded_badges,
                'total_badges_awarded': len(awarded_badges)
            }
            
            logger.info(f"Review completion processed: {len(awarded_badges)} badges awarded, {points_awarded} points")
            return result
            
        except Exception as e:
            logger.error(f"Error processing review completion: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'awarded_badges': [],
                'points_awarded': 0
            }
    
    def _store_review_session(self, user_id: str, review_data: Dict[str, Any]) -> str:
        """Store detailed review session data."""
        try:
            session_id = f"session_{user_id}_{int(datetime.datetime.now().timestamp())}"
            
            query = """
                INSERT INTO review_sessions 
                (user_id, session_id, code_difficulty, total_errors, identified_errors, 
                 accuracy_percentage, review_iterations, time_spent_seconds, session_type, 
                 practice_error_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                user_id,
                session_id,
                review_data.get('code_difficulty', 'medium'),
                review_data.get('total_problems', 0),
                review_data.get('identified_count', 0),
                review_data.get('accuracy_percentage', 0.0),
                review_data.get('review_iterations', 1),
                review_data.get('time_spent_seconds', 0),
                review_data.get('session_type', 'regular'),
                review_data.get('practice_error_code')
            )
            
            self.db.execute_query(query, params)
            logger.debug(f"Stored review session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error storing review session: {str(e)}")
            return ""
    
    def _update_all_badge_progress(self, user_id: str, review_data: Dict[str, Any]) -> None:
        """Update badge progress for all applicable badges based on review completion."""
        try:
            # Get all badges that could potentially be progressed
            badges_query = """
            SELECT badge_id, criteria, name_en, name_zh
            FROM badges 
            WHERE is_active = TRUE
            """
            
            badges = self.db.execute_query(badges_query) or []
            
            for badge in badges:
                self._update_badge_progress(user_id, badge['badge_id'], badge['criteria'], review_data)
                
        except Exception as e:
            logger.error(f"Error updating all badge progress: {str(e)}")

    def _update_badge_progress(self, user_id: str, badge_id: str, criteria_json: str, review_data: Dict[str, Any]) -> None:
        """Update progress for a specific badge based on review completion."""
        try:
            # Parse badge criteria
            criteria = json.loads(criteria_json) if isinstance(criteria_json, str) else criteria_json
            
            if not criteria:
                return
            
            # Calculate progress based on badge type
            progress_update = self._calculate_badge_progress_update(criteria, review_data, user_id)
            
            if progress_update['increment'] > 0:
                # Update or create badge progress record
                upsert_query = """
                INSERT INTO badge_progress 
                (user_id, badge_id, current_progress, target_progress, progress_data)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    current_progress = LEAST(target_progress, current_progress + VALUES(current_progress)),
                    progress_data = VALUES(progress_data),
                    last_updated = CURRENT_TIMESTAMP
                """
                
                progress_data = json.dumps({
                    'last_review_date': datetime.datetime.now().isoformat(),
                    'last_increment': progress_update['increment'],
                    'review_type': review_data.get('session_type', 'regular'),
                    'accuracy': review_data.get('accuracy_percentage', 0)
                })
                
                params = (
                    user_id,
                    badge_id,
                    progress_update['increment'],
                    progress_update['target'],
                    progress_data
                )
                
                self.db.execute_query(upsert_query, params)
                
                logger.debug(f"Updated badge progress for {badge_id}: +{progress_update['increment']} (target: {progress_update['target']})")
                
        except Exception as e:
            logger.error(f"Error updating badge progress for {badge_id}: {str(e)}")

    def _calculate_badge_progress_update(self, criteria: Dict[str, Any], review_data: Dict[str, Any], user_id: str) -> Dict[str, int]:
        """Calculate how much progress should be added for a badge based on review completion."""
        try:
            badge_type = criteria.get('type', '')
            increment = 0
            target = criteria.get('threshold', 1)
            
            # Review count based badges
            if badge_type == 'review_count':
                increment = 1  # Each review adds 1 to progress
                target = criteria.get('threshold', 1)
                
            # Perfect review badges
            elif badge_type == 'perfect_reviews':
                identified = review_data.get('identified_count', 0)
                total = review_data.get('total_problems', 1)
                if identified == total and total > 0:
                    increment = 1
                target = criteria.get('threshold', 5)
                
            # Consecutive perfect reviews
            elif badge_type == 'consecutive_perfect':
                identified = review_data.get('identified_count', 0)
                total = review_data.get('total_problems', 1)
                if identified == total and total > 0:
                    # Check if this continues a streak
                    current_streak = self._get_consecutive_perfect_count(user_id)
                    increment = 1 if current_streak > 0 else 1  # Always increment, streak logic handled elsewhere
                target = criteria.get('threshold', 3)
                
            # Speed and accuracy badges
            elif badge_type == 'speed_accuracy':
                time_spent = review_data.get('time_spent_seconds', 999)
                accuracy = review_data.get('accuracy_percentage', 0)
                time_limit = criteria.get('time_limit', 120)
                accuracy_threshold = criteria.get('accuracy_threshold', 80)
                
                if time_spent <= time_limit and accuracy >= accuracy_threshold:
                    increment = 1
                target = 1  # Usually one-time achievement
                
            # Category mastery badges
            elif badge_type == 'category_mastery':
                category = criteria.get('category', '')
                required_accuracy = criteria.get('accuracy', 85)
                min_encounters = criteria.get('min_encounters', 10)
                
                # Check current category performance
                category_stats = self._get_category_statistics(user_id)
                category_data = category_stats.get(category, {})
                
                if category_data:
                    mastery_level = category_data.get('mastery_level', 0)
                    encounters = category_data.get('encountered', 0)
                    
                    if encounters >= min_encounters and mastery_level >= required_accuracy:
                        increment = 1
                        target = 1
                
            # Points-based badges
            elif badge_type == 'total_points':
                points_threshold = criteria.get('threshold', 1000)
                # Get current total points
                current_points = self._get_user_total_points(user_id)
                points_awarded = review_data.get('points_awarded', 0)
                
                if current_points >= points_threshold:
                    increment = 1
                    target = 1
                
            # Time-based point achievements (rising star)
            elif badge_type == 'points_timeframe':
                points_required = criteria.get('points', 500)
                timeframe_days = criteria.get('days', 7)
                
                # Check if user is within timeframe and has enough points
                user_stats = self._get_user_stats(user_id)
                if user_stats:
                    created_at = user_stats.get('created_at')
                    total_points = user_stats.get('total_points', 0)
                    
                    if created_at:
                        days_since_creation = (datetime.datetime.now() - created_at).days
                        if days_since_creation <= timeframe_days and total_points >= points_required:
                            increment = 1
                            target = 1
                
            # Daily practice streaks
            elif badge_type == 'consecutive_days':
                target = criteria.get('threshold', 5)
                current_streak = self._get_streak_count(user_id, 'daily_practice')
                if current_streak >= target:
                    increment = 1
                    target = 1
                
            # Practice session badges
            elif badge_type == 'practice_sessions':
                if review_data.get('session_type') == 'practice':
                    increment = 1
                target = criteria.get('threshold', 10)
                
            # Feature usage badges
            elif badge_type == 'feature_usage':
                feature = criteria.get('feature', '')
                if feature == 'error_explorer' and review_data.get('session_type') == 'practice':
                    increment = 1
                target = criteria.get('threshold', 10)
            
            return {'increment': increment, 'target': target}
            
        except Exception as e:
            logger.error(f"Error calculating badge progress: {str(e)}")
            return {'increment': 0, 'target': 1}

    def get_user_badge_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all badge progress for a user."""
        if not user_id:
            return []
        
        try:
            self.current_language = get_current_language()
            name_field = f"name_{self.current_language}" if self.current_language in ["en", "zh"] else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language in ["en", "zh"] else "description_en"
            
            query = f"""
            SELECT 
                bp.badge_id,
                bp.current_progress,
                bp.target_progress,
                bp.progress_data,
                bp.last_updated,
                b.{name_field} as name,
                b.{desc_field} as description,
                b.icon,
                b.category,
                b.difficulty,
                b.points,
                CASE 
                    WHEN bp.current_progress >= bp.target_progress THEN 'completed'
                    WHEN bp.current_progress > 0 THEN 'in_progress'
                    ELSE 'not_started'
                END as progress_status,
                CASE 
                    WHEN bp.target_progress > 0 THEN (bp.current_progress * 100.0 / bp.target_progress)
                    ELSE 0
                END as progress_percentage
            FROM badge_progress bp
            JOIN badges b ON bp.badge_id = b.badge_id
            WHERE bp.user_id = %s AND b.is_active = TRUE
            ORDER BY progress_percentage DESC, bp.last_updated DESC
            """
            
            progress_records = self.db.execute_query(query, (user_id,)) or []
            
            return progress_records
            
        except Exception as e:
            logger.error(f"Error getting user badge progress: {str(e)}")
            return []

    def get_badge_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's badge progress."""
        if not user_id:
            return {}
        
        try:
            progress_records = self.get_user_badge_progress(user_id)
            
            total_badges = len(progress_records)
            in_progress = len([p for p in progress_records if p['progress_status'] == 'in_progress'])
            completed = len([p for p in progress_records if p['progress_status'] == 'completed'])
            not_started = total_badges - in_progress - completed
            
            # Calculate average progress
            avg_progress = 0
            if progress_records:
                total_progress = sum(p['progress_percentage'] for p in progress_records)
                avg_progress = total_progress / len(progress_records)
            
            return {
                'total_badges': total_badges,
                'in_progress': in_progress,
                'completed': completed,
                'not_started': not_started,
                'average_progress': avg_progress,
                'completion_rate': (completed / total_badges * 100) if total_badges > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting badge progress summary: {str(e)}")
            return {}

    def _update_user_statistics(self, user_id: str, review_data: Dict[str, Any]) -> None:
        """Update user's overall statistics."""
        try:
            accuracy = review_data.get('accuracy_percentage', 0.0)
            identified_count = review_data.get('identified_count', 0)
            total_problems = review_data.get('total_problems', 1)
            time_spent = review_data.get('time_spent_seconds', 0)
            
            # Check if this is a perfect review
            is_perfect = identified_count == total_problems and total_problems > 0
            
            # Update user statistics
            update_query = """
                UPDATE users SET
                    reviews_completed = reviews_completed + 1,
                    score = score + %s,
                    total_session_time = total_session_time + %s,
                    perfect_reviews_count = perfect_reviews_count + %s,
                    average_accuracy = (
                        CASE 
                        WHEN reviews_completed = 0 THEN %s
                        ELSE (average_accuracy * reviews_completed + %s) / (reviews_completed + 1)
                        END
                    ),
                    last_activity = CURDATE()
                WHERE uid = %s
            """
            
            params = (
                identified_count,  # score increase
                time_spent,
                1 if is_perfect else 0,
                accuracy,  # for first review
                accuracy,  # for average calculation
                user_id
            )
            
            self.db.execute_query(update_query, params)
            logger.debug(f"Updated user statistics for {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user statistics: {str(e)}")
    
    def _update_category_statistics(self, user_id: str, review_data: Dict[str, Any]) -> None:
        """Update category-specific performance statistics."""
        try:
            categories = review_data.get('categories_encountered', [])
            identified_count = review_data.get('identified_count', 0)
            total_problems = review_data.get('total_problems', 1)
            
            for category in categories:
                # Calculate category performance (simplified - assume equal distribution)
                category_encountered = 1
                category_identified = 1 if identified_count >= len(categories) else 0
                
                # Insert or update category stats
                upsert_query = """
                    INSERT INTO error_category_stats 
                    (user_id, category_name, encountered, identified)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        encountered = encountered + VALUES(encountered),
                        identified = identified + VALUES(identified),
                        mastery_level = CASE 
                            WHEN (encountered + VALUES(encountered)) > 0 
                            THEN ((identified + VALUES(identified)) * 100.0) / (encountered + VALUES(encountered))
                            ELSE 0 
                        END
                """
                
                params = (user_id, category, category_encountered, category_identified)
                self.db.execute_query(upsert_query, params)
            
            logger.debug(f"Updated category statistics for {len(categories)} categories")
            
        except Exception as e:
            logger.error(f"Error updating category statistics: {str(e)}")
    
    def _update_user_streaks(self, user_id: str, review_data: Dict[str, Any]) -> None:
        """Update user streak data."""
        try:
            today = datetime.date.today()
            identified_count = review_data.get('identified_count', 0)
            total_problems = review_data.get('total_problems', 1)
            is_perfect = identified_count == total_problems and total_problems > 0
            
            # Update daily practice streak
            self._update_streak(user_id, 'daily_practice', today, True)
            
            # Update perfect review streak
            if is_perfect:
                self._update_streak(user_id, 'perfect_reviews', today, True)
            else:
                self._reset_streak(user_id, 'perfect_reviews')
            
        except Exception as e:
            logger.error(f"Error updating user streaks: {str(e)}")
    
    def _update_streak(self, user_id: str, streak_type: str, date: datetime.date, increment: bool) -> None:
        """Update a specific streak type."""
        try:
            if increment:
                query = """
                    INSERT INTO user_streaks (user_id, streak_type, current_streak, longest_streak, last_activity_date)
                    VALUES (%s, %s, 1, 1, %s)
                    ON DUPLICATE KEY UPDATE
                        current_streak = CASE 
                            WHEN last_activity_date = DATE_SUB(%s, INTERVAL 1 DAY) THEN current_streak + 1
                            WHEN last_activity_date < DATE_SUB(%s, INTERVAL 1 DAY) THEN 1
                            ELSE current_streak
                        END,
                        longest_streak = GREATEST(longest_streak, 
                            CASE 
                                WHEN last_activity_date = DATE_SUB(%s, INTERVAL 1 DAY) THEN current_streak + 1
                                WHEN last_activity_date < DATE_SUB(%s, INTERVAL 1 DAY) THEN 1
                                ELSE current_streak
                            END
                        ),
                        last_activity_date = %s
                """
                params = (user_id, streak_type, date, date, date, date, date, date)
            else:
                query = """
                    UPDATE user_streaks 
                    SET current_streak = 0, last_activity_date = %s
                    WHERE user_id = %s AND streak_type = %s
                """
                params = (date, user_id, streak_type)
            
            self.db.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Error updating streak {streak_type}: {str(e)}")
    
    def _reset_streak(self, user_id: str, streak_type: str) -> None:
        """Reset a specific streak type."""
        try:
            query = """
                UPDATE user_streaks 
                SET current_streak = 0
                WHERE user_id = %s AND streak_type = %s
            """
            self.db.execute_query(query, (user_id, streak_type))
            
        except Exception as e:
            logger.error(f"Error resetting streak {streak_type}: {str(e)}")
    
    def _calculate_and_award_points(self, user_id: str, review_data: Dict[str, Any]) -> int:
        """Calculate and award points based on review performance."""
        try:
            base_points = 10
            accuracy = review_data.get('accuracy_percentage', 0.0)
            identified_count = review_data.get('identified_count', 0)
            total_problems = review_data.get('total_problems', 1)
            time_spent = review_data.get('time_spent_seconds', 0)
            
            # Base points for completion
            points = base_points
            
            # Accuracy bonus
            if accuracy >= 90:
                points += 15
            elif accuracy >= 80:
                points += 10
            elif accuracy >= 70:
                points += 5
            
            # Perfect review bonus
            if identified_count == total_problems and total_problems > 0:
                points += 20
            
            # Speed bonus (if completed quickly with good accuracy)
            if time_spent > 0 and time_spent <= 120 and accuracy >= 80:
                points += 10
            
            # Award the points
            self.award_points(user_id, points, 'review_completion', 
                            f"Review completed: {accuracy:.1f}% accuracy")
            
            return points
            
        except Exception as e:
            logger.error(f"Error calculating points: {str(e)}")
            return 0
    
    def _check_and_award_all_badges(self, user_id: str, review_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check all badge criteria and award appropriate badges."""
        awarded_badges = []
        
        try:
            # Get user stats
            user_stats = self._get_user_stats(user_id)
            if not user_stats:
                return awarded_badges
            
            # Check each badge category
            awarded_badges.extend(self._check_completion_badges(user_id, user_stats, review_data))
            awarded_badges.extend(self._check_skill_badges(user_id, user_stats, review_data))
            awarded_badges.extend(self._check_consistency_badges(user_id, user_stats, review_data))
            awarded_badges.extend(self._check_mastery_badges(user_id, user_stats, review_data))
            awarded_badges.extend(self._check_special_badges(user_id, user_stats, review_data))
            
            return awarded_badges
            
        except Exception as e:
            logger.error(f"Error checking badges: {str(e)}")
            return awarded_badges
    
    def _check_completion_badges(self, user_id: str, user_stats: Dict, review_data: Dict) -> List[Dict[str, Any]]:
        """Check completion-based badges."""
        badges = []
        reviews_completed = user_stats.get('reviews_completed', 0)
        
        badge_thresholds = [
            (1, 'first-review'),
            (5, 'reviewer-novice'),
            (25, 'reviewer-adept'),
            (50, 'reviewer-master'),
            (100, 'reviewer-legend')
        ]
        
        for threshold, badge_id in badge_thresholds:
            if reviews_completed == threshold:  # Exact match for awarding
                badge = self.award_badge(user_id, badge_id)
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
        
        return badges
    
    def _check_skill_badges(self, user_id: str, user_stats: Dict, review_data: Dict) -> List[Dict[str, Any]]:
        """Check skill-based badges."""
        badges = []
        
        # Perfect review tracking
        identified = review_data.get('identified_count', 0)
        total = review_data.get('total_problems', 1)
        accuracy = review_data.get('accuracy_percentage', 0.0)
        time_spent = review_data.get('time_spent_seconds', 0)
        
        is_perfect = identified == total and total > 0
        
        if is_perfect:
            # Update perfect review progress
            perfect_count = self._get_perfect_review_count(user_id)
            
            # Bug Hunter badge - 5 perfect reviews
            if perfect_count >= self.BADGE_CRITERIA['perfect_review_threshold']:
                badge = self.award_badge(user_id, 'bug-hunter')
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
            
            # Check consecutive perfect reviews
            consecutive_perfect = self._get_consecutive_perfect_count(user_id)
            if consecutive_perfect >= self.BADGE_CRITERIA['consecutive_perfect_threshold']:
                badge = self.award_badge(user_id, 'perfectionist')
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
        
        # Speed demon badge
        if (time_spent > 0 and time_spent <= self.BADGE_CRITERIA['speed_threshold_seconds'] 
            and accuracy >= self.BADGE_CRITERIA['accuracy_for_speed']):
            badge = self.award_badge(user_id, 'speed-demon')
            if badge.get('success'):
                badges.append(badge.get('badge', {}))
        
        return badges
    
    def _check_consistency_badges(self, user_id: str, user_stats: Dict, review_data: Dict) -> List[Dict[str, Any]]:
        """Check consistency-based badges."""
        badges = []
        
        # Get streak data
        daily_streak = self._get_streak_count(user_id, 'daily_practice')
        
        consistency_thresholds = [
            (5, 'consistency-champ'),
            (7, 'week-warrior'),
            (30, 'month-master')
        ]
        
        for threshold, badge_id in consistency_thresholds:
            if daily_streak >= threshold:
                badge = self.award_badge(user_id, badge_id)
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
        
        return badges
    
    def _check_mastery_badges(self, user_id: str, user_stats: Dict, review_data: Dict) -> List[Dict[str, Any]]:
        """Check category mastery badges."""
        badges = []
        
        # Get category statistics
        category_stats = self._get_category_statistics(user_id)
        
        mastery_badges = {
            'Logical Errors': 'logic-guru',
            'Syntax Errors': 'syntax-specialist', 
            'Code Quality': 'quality-inspector',
            'Standard Violation': 'standards-expert',
            'Java Specific': 'java-maven'
        }
        
        categories_mastered = 0
        
        for category, badge_id in mastery_badges.items():
            stats = category_stats.get(category, {})
            mastery_level = stats.get('mastery_level', 0)
            encountered = stats.get('encountered', 0)
            
            if (mastery_level >= self.BADGE_CRITERIA['mastery_threshold'] 
                and encountered >= 10):  # Minimum encounters
                badge = self.award_badge(user_id, badge_id)
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
                    categories_mastered += 1
        
        # Full spectrum badge - mastery in all categories
        if categories_mastered >= len(mastery_badges):
            badge = self.award_badge(user_id, 'full-spectrum')
            if badge.get('success'):
                badges.append(badge.get('badge', {}))
        
        return badges
    
    def _check_special_badges(self, user_id: str, user_stats: Dict, review_data: Dict) -> List[Dict[str, Any]]:
        """Check special achievement badges."""
        badges = []
        
        # Rising star badge - 500 points in first week
        total_points = user_stats.get('total_points', 0)
        created_at = user_stats.get('created_at')
        
        if total_points >= self.BADGE_CRITERIA['rising_star_points'] and created_at:
            days_since_creation = (datetime.datetime.now() - created_at).days
            if days_since_creation <= self.BADGE_CRITERIA['rising_star_days']:
                badge = self.award_badge(user_id, 'rising-star')
                if badge.get('success'):
                    badges.append(badge.get('badge', {}))
        
        # Century club badge - 100% accuracy
        accuracy = review_data.get('accuracy_percentage', 0.0)
        if accuracy == 100.0:
            badge = self.award_badge(user_id, 'century-club')
            if badge.get('success'):
                badges.append(badge.get('badge', {}))
        
        return badges
    
    
    
    def _get_perfect_review_count(self, user_id: str) -> int:
        """Get count of perfect reviews."""
        try:
            query = """
                SELECT COUNT(*) as count 
                FROM review_sessions 
                WHERE user_id = %s AND accuracy_percentage = 100.0
            """
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            return result.get('count', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting perfect review count: {str(e)}")
            return 0
    
    def _update_badge_check_timestamp(self, user_id: str) -> None:
        """Update the timestamp of last badge check."""
        try:
            query = "UPDATE users SET last_badge_check = NOW() WHERE uid = %s"
            self.db.execute_query(query, (user_id,))
        except Exception as e:
            logger.error(f"Error updating badge check timestamp: {str(e)}")
    
    
    def _check_point_badges(self, user_id: str, total_points: int) -> None:
        """
        Check if a user qualifies for any point-based badges.
        
        Args:
            user_id: The user's ID
            total_points: The user's total points
        """
        # Rising Star badge - 500 points in first week
        if total_points >= 500:
            # Check when the user joined
            query = "SELECT created_at FROM users WHERE uid = %s"
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                created_at = result.get("created_at")
                now = datetime.datetime.now()
                
                if created_at and (now - created_at).days <= 7:
                    self.award_badge(user_id, "rising-star")

    def _check_category_mastery(self, user_id: str, category: str, stats: Dict[str, Any]) -> None:
        """
        Check if a user qualifies for category mastery badges.
        
        Args:
            user_id: The user's ID
            category: The error category
            stats: Category statistics
        """
        # Required mastery level and minimum encounters to earn the badge
        MASTERY_THRESHOLD = 0.85
        MIN_ENCOUNTERS = 10
        
        if stats and stats.get("mastery_level", 0) >= MASTERY_THRESHOLD and stats.get("encountered", 0) >= MIN_ENCOUNTERS:
            # Update current language before mapping categories
            self.current_language = get_current_language()
            
            # Map categories to badge IDs - support both English and Chinese categories
            # Categories are not translated with t() because they need to match exactly what's in the database
            category_badges = {
                t("logical"): "logic-guru",
                "Logical": "logic-guru",
                "邏輯錯誤": "logic-guru",  # Chinese equivalent
                t("syntax"): "syntax-specialist",
                "Syntax": "syntax-specialist",
                "語法錯誤": "syntax-specialist",  # Chinese equivalent
                t("code_quality"): "quality-inspector",
                "Code Quality": "quality-inspector",
                "程式碼品質": "quality-inspector",  # Chinese equivalent
                t("standard_violation"): "standards-expert",
                "Standard Violation": "standards-expert",
                "標準違規": "standards-expert",  # Chinese equivalent
                t("java_specific"): "java-maven",
                "Java Specific": "java-maven",
                "Java 特定錯誤": "java-maven"  # Chinese equivalent
            }
            
            # Award the appropriate badge if available
            badge_id = category_badges.get(category)
            if badge_id:
                self.award_badge(user_id, badge_id)
            
        # Check for "Full Spectrum" badge - at least one error in each category
        query = """
            SELECT COUNT(DISTINCT category) AS category_count
            FROM error_category_stats
            WHERE user_id = %s AND identified > 0
        """
        
        result = self.db.execute_query(query, (user_id,), fetch_one=True)
        
        if result and result.get("category_count", 0) >= 5:  # Assuming 5 main categories
            self.award_badge(user_id, "full-spectrum")
    
    def check_review_completion_badges(self, user_id: str, reviews_completed: int, 
                                    all_errors_found: bool) -> None:
        """
        Check if a user qualifies for review completion badges.
        
        Args:
            user_id: The user's ID
            reviews_completed: Number of reviews completed
            all_errors_found: Whether all errors were found in the review
        """
        # Review progression badges
        if reviews_completed >= 5:
            self.award_badge(user_id, "reviewer-novice")
        
        if reviews_completed >= 25:
            self.award_badge(user_id, "reviewer-adept")
        
        if reviews_completed >= 50:
            self.award_badge(user_id, "reviewer-master")
        
        # Bug Hunter badge - find all errors in at least 5 reviews
        if all_errors_found:
            # Count how many perfect reviews the user has
            query = """
                SELECT COUNT(*) AS perfect_count
                FROM activity_log
                WHERE user_id = %s AND activity_type = 'perfect_review'
            """
            
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result and result.get("perfect_count", 0) >= 5:
                self.award_badge(user_id, "bug-hunter")            
          
                self.db.execute_query(
                    "INSERT INTO activity_log (user_id, activity_type, points, details_en, details_zh) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, "perfect_review", 0, t("completed_perfect_review"), t("completed_perfect_review"))
                )
          
            
            # Perfectionist badge - 3 consecutive perfect reviews
            query = """
                SELECT activity_type
                FROM activity_log
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 3
            """
            
            result = self.db.execute_query(query, (user_id,))
            
            if result and len(result) >= 3:
                all_perfect = all(r.get("activity_type") == "perfect_review" for r in result)
                if all_perfect:
                    self.award_badge(user_id, "perfectionist")

    def update_consecutive_days(self, user_id: str) -> Dict[str, Any]:
        """
        Update a user's consecutive days of activity.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing success status and updated statistics
        """
        if not user_id:
            return {"success": False, "error": t("invalid_user_id")}
        
        try:
            # Get current last_activity and consecutive_days
            query = """
                SELECT last_activity, consecutive_days 
                FROM users 
                WHERE uid = %s
            """
            
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result:
                return {"success": False, "error": t("user_not_found")}
            
            today = datetime.date.today()
            last_activity = result.get("last_activity")
            consecutive_days = result.get("consecutive_days", 0)
            
            # Calculate new consecutive days
            new_consecutive_days = consecutive_days
            
            if not last_activity:
                # First activity
                new_consecutive_days = 1
            elif last_activity == today:
                # Already logged today, no change
                pass
            elif last_activity == today - datetime.timedelta(days=1):
                # Activity on consecutive day
                new_consecutive_days += 1
            else:
                # Break in streak
                new_consecutive_days = 1
            
            # Update user record
            update_query = """
                UPDATE users 
                SET last_activity = %s,
                    consecutive_days = %s
                WHERE uid = %s
            """
            
            self.db.execute_query(update_query, (today, new_consecutive_days, user_id))
            
            # Check for consistency badges
            if new_consecutive_days >= 5:
                self.award_badge(user_id, "consistency-champ")
            
            return {
                "success": True, 
                "consecutive_days": new_consecutive_days
            }
                
        except Exception as e:
            logger.error(f"{t('error_updating_consecutive_days')}: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def _get_user_total_points(self, user_id: str) -> int:
        """Get user's total points."""
        try:
            query = "SELECT total_points FROM users WHERE uid = %s"
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            return result.get('total_points', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting user total points: {str(e)}")
            return 0
    
    def _get_consecutive_perfect_count(self, user_id: str) -> int:
        """Get current consecutive perfect review count."""
        try:
            query = """
                SELECT current_streak 
                FROM user_streaks 
                WHERE user_id = %s AND streak_type = 'perfect_reviews'
            """
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            return result.get('current_streak', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting consecutive perfect count: {str(e)}")
            return 0
    
    def _get_streak_count(self, user_id: str, streak_type: str) -> int:
        """Get current streak count for a specific type."""
        try:
            query = """
                SELECT current_streak 
                FROM user_streaks 
                WHERE user_id = %s AND streak_type = %s
            """
            result = self.db.execute_query(query, (user_id, streak_type), fetch_one=True)
            return result.get('current_streak', 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting streak count: {str(e)}")
            return 0
    
    def _get_category_statistics(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get category-specific statistics."""
        try:
            query = """
                SELECT category_name, encountered, identified, mastery_level
                FROM error_category_stats 
                WHERE user_id = %s
            """
            results = self.db.execute_query(query, (user_id,))
            
            stats = {}
            for result in results or []:
                stats[result['category_name']] = {
                    'encountered': result['encountered'],
                    'identified': result['identified'],
                    'mastery_level': float(result['mastery_level'])
                }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting category statistics: {str(e)}")
            return {}
    
    def _get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive user statistics."""
        try:
            query = """
                SELECT uid, reviews_completed, score, total_points, perfect_reviews_count,
                       average_accuracy, total_session_time, created_at, last_activity
                FROM users 
                WHERE uid = %s
            """
            return self.db.execute_query(query, (user_id,), fetch_one=True)
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return None
    
   
    def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all badges earned by a user."""
        if not user_id:
            return []
        
        self.current_language = get_current_language()
        
        try:
            name_field = f"name_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "description_en"
            
            query = f"""
                SELECT b.badge_id, b.{name_field} as name, b.{desc_field} as description, 
                       b.icon, b.category, b.difficulty, b.points, ub.awarded_at
                FROM badges b
                JOIN user_badges ub ON b.badge_id = ub.badge_id
                WHERE ub.user_id = %s
                ORDER BY ub.awarded_at DESC
            """
            
            badges = self.db.execute_query(query, (user_id,))
            return badges or []
                
        except Exception as e:
            logger.error(f"Error getting user badges: {str(e)}")
            return []

    def award_badge(self, user_id: str, badge_id: str) -> Dict[str, Any]:
        """Award a badge to a user."""
        if not user_id or not badge_id:
            return {"success": False, "error": "Invalid user ID or badge ID"}
        
        try:
            name_field = f"name_{self.current_language}" if self.current_language in ["en", "zh"] else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language in ["en", "zh"] else "description_en"
            
            badge_query = f"SELECT badge_id, {name_field} as name, {desc_field} as description, points FROM badges WHERE badge_id = %s"
            badge = self.db.execute_query(badge_query, (badge_id,), fetch_one=True)
            
            if not badge:
                return {"success": False, "error": "Badge not found"}
            
            # Check if the user already has this badge
            has_badge_query = """
                SELECT * FROM user_badges 
                WHERE user_id = %s AND badge_id = %s
            """
            existing = self.db.execute_query(has_badge_query, (user_id, badge_id), fetch_one=True)
            
            if existing:
                return {"success": True, "badge": badge, "message": "Badge already awarded"}
            
            # Award the badge
            award_query = """
                INSERT INTO user_badges 
                (user_id, badge_id) 
                VALUES (%s, %s)
            """
            self.db.execute_query(award_query, (user_id, badge_id))
            
            # Award points for earning the badge
            badge_points = badge.get("points", 10)
            self.award_points(
                user_id, 
                badge_points,
                "badge_earned",
                f"Earned badge: {badge.get('name')}"
            )
            
            # Mark badge as completed in progress table
            self._mark_badge_progress_completed(user_id, badge_id)
            
            return {
                "success": True, 
                "badge": badge,
                "message": f"Badge awarded successfully: {badge.get('name')}"
            }
                
        except Exception as e:
            logger.error(f"Error awarding badge: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _mark_badge_progress_completed(self, user_id: str, badge_id: str) -> None:
        """Mark a badge as completed in the progress table."""
        try:
            update_query = """
            UPDATE badge_progress 
            SET current_progress = target_progress,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s AND badge_id = %s
            """
            self.db.execute_query(update_query, (user_id, badge_id))
        except Exception as e:
            logger.error(f"Error marking badge progress as completed: {str(e)}")

    def award_points(self, user_id: str, points: int, activity_type: str, details: str = None) -> Dict[str, Any]:
        """Award points to a user and log the activity."""
        if not user_id:
            return {"success": False, "error": "Invalid user ID"}
        
        try:
            # Update the user's total points
            update_query = """
                UPDATE users 
                SET total_points = total_points + %s 
                WHERE uid = %s
            """
            self.db.execute_query(update_query, (points, user_id))
           
            # Log the activity
            log_query = """
                INSERT INTO activity_log 
                (user_id, activity_type, points, details_en, details_zh) 
                VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute_query(log_query, (user_id, activity_type, points, details, details))
            
            # Get the updated total points
            points_query = "SELECT total_points FROM users WHERE uid = %s"
            result = self.db.execute_query(points_query, (user_id,), fetch_one=True)
            
            if result:
                total_points = result.get("total_points", 0)
                return {"success": True, "total_points": total_points}
            else:
                return {"success": False, "error": "User not found"}
                
        except Exception as e:
            logger.error(f"Error awarding points: {str(e)}")
            return {"success": False, "error": str(e)}