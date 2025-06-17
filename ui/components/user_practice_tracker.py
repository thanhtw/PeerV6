import streamlit as st
import os
import logging
import time
import json
from typing import Dict, List, Any, Optional
from data.database_error_repository import DatabaseErrorRepository
from data.mysql_connection import MySQLConnection
from utils.language_utils import t


logger = logging.getLogger(__name__)

class UserPracticeTracker:
    """Class to track user practice progress on individual errors."""
    
    def __init__(self):
        self.db = MySQLConnection()
    
    def get_user_practice_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive practice data for a user with improved error matching."""
        if not user_id:
            return {"practiced_errors": [], "unpracticed_errors": [], "practice_stats": {}}
        
        try:
            # Get practiced errors with statistics
            practiced_query = """
            SELECT 
                uep.*,
                je.difficulty_level,
                je.error_code as je_error_code,
                je.error_name_en as je_error_name_en,
                je.error_name_zh as je_error_name_zh,
                ec.name_en as category_name_en,
                ec.name_zh as category_name_zh
            FROM user_error_practice uep
            LEFT JOIN java_errors je ON uep.error_code = je.error_code
            LEFT JOIN error_categories ec ON je.category_id = ec.id
            WHERE uep.user_id = %s AND uep.practice_count > 0
            ORDER BY uep.last_practiced DESC
            """
            practiced_errors_raw = self.db.execute_query(practiced_query, (user_id,)) or []
            
            # Clean up practiced errors data
            practiced_errors = []
            for error in practiced_errors_raw:
                # Use the error_code from java_errors table if available, otherwise from practice table
                error_code = error.get('je_error_code') or error.get('error_code')
                error_name_en = error.get('je_error_name_en') or error.get('error_name_en')
                error_name_zh = error.get('je_error_name_zh') or error.get('error_name_zh')
                
                if error_code and error_name_en:  # Only include if we have essential data
                    practiced_errors.append({
                        'error_code': error_code,
                        'error_name_en': error_name_en,
                        'error_name_zh': error_name_zh,
                        'difficulty_level': error.get('difficulty_level', 'medium'),
                        'category_name_en': error.get('category_name_en', 'Unknown'),
                        'category_name_zh': error.get('category_name_zh', '未知'),
                        'practice_count': error.get('practice_count', 0),
                        'total_attempts': error.get('total_attempts', 0),
                        'successful_completions': error.get('successful_completions', 0),
                        'best_accuracy': error.get('best_accuracy', 0.0),
                        'completion_status': error.get('completion_status', 'not_started'),
                        'mastery_level': error.get('mastery_level', 0.0),
                        'last_practiced': error.get('last_practiced')
                    })
            
            # Get all available errors
            all_errors_query = """
            SELECT 
                je.error_code,
                je.error_name_en,
                je.error_name_zh,
                je.description_en,
                je.description_zh,
                je.implementation_guide_en,
                je.implementation_guide_zh,
                je.difficulty_level,
                ec.name_en as category_name_en,
                ec.name_zh as category_name_zh
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id
            ORDER BY ec.sort_order, je.error_name_en
            """
            all_errors = self.db.execute_query(all_errors_query) or []
            
            # Separate practiced and unpracticed
            practiced_codes = {error['error_code'] for error in practiced_errors if error.get('error_code')}
            unpracticed_errors = [error for error in all_errors if error.get('error_code') not in practiced_codes]
            
            # Get overall practice statistics
            stats_query = """
            SELECT 
                COUNT(*) as total_practiced,
                SUM(CASE WHEN completion_status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN completion_status = 'mastered' THEN 1 ELSE 0 END) as mastered_count,
                AVG(best_accuracy) as avg_accuracy,
                SUM(total_time_spent) as total_time,
                MAX(last_practiced) as last_session
            FROM user_error_practice 
            WHERE user_id = %s AND practice_count > 0
            """
            stats_result = self.db.execute_query(stats_query, (user_id,), fetch_one=True)
            practice_stats = stats_result or {}
            
            logger.debug(f"Practice data retrieved: {len(practiced_errors)} practiced, {len(unpracticed_errors)} unpracticed")
            
            return {
                "practiced_errors": practiced_errors,
                "unpracticed_errors": unpracticed_errors,
                "practice_stats": practice_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting user practice data: {str(e)}")
            return {"practiced_errors": [], "unpracticed_errors": [], "practice_stats": {}}
    
    def start_practice_session(self, user_id: str, error_data: Dict[str, Any]) -> None:
        """Record the start of a practice session with improved error code handling."""
        if not user_id:
            return
            
        try:
            # Extract error information with fallbacks
            error_code = error_data.get('error_code', '')
            error_name_en = error_data.get(t("error_name_variable"), error_data.get('error_name', ''))
            error_name_zh = error_data.get('error_name_zh', error_name_en)
            category = error_data.get('category', '')
            
            # If no error_code, try to get it from database by name
            if not error_code and error_name_en:
                lookup_query = """
                SELECT je.error_code 
                FROM java_errors je 
                WHERE je.error_name_en = %s OR je.error_name_zh = %s
                LIMIT 1
                """
                lookup_result = self.db.execute_query(lookup_query, (error_name_en, error_name_en), fetch_one=True)
                if lookup_result:
                    error_code = lookup_result['error_code']
            
            # Generate error_code if still missing
            if not error_code:
                import hashlib
                hash_input = f"{error_name_en}_{category}"
                hash_object = hashlib.md5(hash_input.encode())
                error_code = f"gen_{hash_object.hexdigest()[:8]}"
            
            # Insert or update practice record
            upsert_query = """
            INSERT INTO user_error_practice 
            (user_id, error_code, error_name_en, error_name_zh, category_name, 
            practice_count, total_attempts, completion_status, last_practiced)
            VALUES (%s, %s, %s, %s, %s, 1, 1, 'in_progress', NOW())
            ON DUPLICATE KEY UPDATE
                practice_count = practice_count + 1,
                total_attempts = total_attempts + 1,
                completion_status = CASE 
                    WHEN completion_status = 'not_started' THEN 'in_progress'
                    ELSE completion_status 
                END,
                last_practiced = NOW(),
                updated_at = NOW()
            """
            
            self.db.execute_query(upsert_query, (
                user_id, error_code, error_name_en, error_name_zh, category
            ))
            
            logger.debug(f"Started practice session for user {user_id}, error {error_code} ({error_name_en})")
            
        except Exception as e:
            logger.error(f"Error starting practice session: {str(e)}")
    
    def complete_practice_session(self, user_id: str, error_code: str, 
                            session_data: Dict[str, Any]) -> None:
        """Record the completion of a practice session with results."""
        if not user_id or not error_code:
            return
            
        try:
            accuracy = session_data.get('accuracy', 0.0)
            time_spent = session_data.get('time_spent_seconds', 0)
            successful = session_data.get('successful_completion', False)
            
            # Determine completion status based on performance
            if accuracy >= 90:
                status = 'mastered'
                mastery_level = min(100.0, accuracy)
            elif accuracy >= 70:
                status = 'completed'
                mastery_level = accuracy
            else:
                status = 'in_progress'
                mastery_level = accuracy * 0.8  # Partial mastery
            
            update_query = """
            UPDATE user_error_practice SET
                successful_completions = CASE WHEN %s THEN successful_completions + 1 ELSE successful_completions END,
                best_accuracy = GREATEST(best_accuracy, %s),
                total_time_spent = total_time_spent + %s,
                completion_status = CASE 
                    WHEN %s >= 90 THEN 'mastered'
                    WHEN %s >= 70 THEN 'completed'
                    ELSE completion_status
                END,
                mastery_level = GREATEST(mastery_level, %s),
                last_practiced = NOW(),
                updated_at = NOW()
            WHERE user_id = %s AND error_code = %s
            """
            
            affected_rows = self.db.execute_query(update_query, (
                successful, accuracy, time_spent, accuracy, accuracy, 
                mastery_level, user_id, error_code
            ))
            
            if affected_rows == 0:
                logger.warning(f"No practice session found to update for user {user_id}, error {error_code}")
            else:
                logger.debug(f"Completed practice session for user {user_id}, error {error_code}, accuracy: {accuracy}%")
            
        except Exception as e:
            logger.error(f"Error completing practice session: {str(e)}")