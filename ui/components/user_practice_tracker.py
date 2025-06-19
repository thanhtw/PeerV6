import streamlit as st
import os
import logging
import time
import json
from typing import Dict, List, Any, Optional
from data.database_error_repository import DatabaseErrorRepository
from data.mysql_connection import MySQLConnection
from utils.language_utils import t, get_current_language


logger = logging.getLogger(__name__)

class UserPracticeTracker:
    """Class to track user practice progress on individual errors."""
    
    def __init__(self):
        self.db = MySQLConnection()
    
    def _get_language_fields(self, base_field: str) -> str:
        """Get the appropriate language field name."""
        if self.current_language == 'zh':
            return f"{base_field}_zh"
        else:
            return f"{base_field}_en"
        
    def get_user_practice_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive practice data for a user with improved error matching."""
        if not user_id:
            return {t("practiced_errors"): [], t("unpracticed_errors"): [], t("practice_stats"): {}}
        
        try:
            self.current_language = get_current_language()
            name_field = self._get_language_fields('error_name')
            description_field = self._get_language_fields('description')
            cat_name_field = self._get_language_fields('name')
            guide_field = self._get_language_fields('implementation_guide')

            # Get practiced errors with statistics
            practiced_query = f"""
            SELECT 
                uep.*,
                je.difficulty_level,
                je.error_code as error_code,
                je.{name_field} as error_name,               
                ec.{cat_name_field} as category_name
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
                practiced_errors.append({
                    t('error_code'): error.get('error_code'),
                    t('error_name'): error.get('error_name'),                       
                    t('difficulty_level'): error.get('difficulty_level', 'medium'),
                    t('category'): error.get('category', 'Unknown'),                       
                    t('practice_count'): error.get('practice_count', 0),
                    t('total_attempts'): error.get('total_attempts', 0),
                    t('successful_completions'): error.get('successful_completions', 0),
                    t('best_accuracy'): error.get('best_accuracy', 0.0),
                    t('completion_status'): error.get('completion_status', 'not_started'),
                    t('mastery_level'): error.get('mastery_level', 0.0),
                    t('last_practiced'): error.get('last_practiced')
                })
            # Get all available errors
            all_errors_query = f"""
            SELECT 
                je.error_code,
                je.{name_field} as error_name,              
                je.{description_field} as description,              
                je.{guide_field} as implementation_guide,               
                je.difficulty_level,
                ec.{cat_name_field} as category_name
            FROM java_errors je
            JOIN error_categories ec ON je.category_id = ec.id
            ORDER BY ec.sort_order, je.error_name_en
            """
            all_errors = self.db.execute_query(all_errors_query) or []
            
            # Separate practiced and unpracticed
            practiced_codes = {error['error_code'] for error in practiced_errors if error.get('error_code')}
            unpracticed_errors = [error for error in all_errors if error.get('error_code') not in practiced_codes]
            
            # Get overall practice statistics
            stats_query = f"""
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

            practice_stats = stats_result
            
            logger.debug(f"Practice data retrieved: {len(practiced_errors)} practiced, {len(unpracticed_errors)} unpracticed")
            
            return {
                t("practiced_errors"): practiced_errors,
                t("unpracticed_errors"): unpracticed_errors,
                t("practice_stats"): practice_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting user practice data: {str(e)}")
            return {t("practiced_errors"): [], t("unpracticed_errors"): [], t("practice_stats"): {}}
    
    def start_practice_session(self, user_id: str, error_data: Dict[str, Any]) -> None:
        """Record the start of a practice session with improved error code handling."""
        if not user_id:
            return
            
        try:
            self.current_language = get_current_language()
            name_field = self._get_language_fields('error_name')
            description_field = self._get_language_fields('description')
            cat_name_field = self._get_language_fields('name')
            guide_field = self._get_language_fields('implementation_guide')
            
            # Extract error information with fallbacks
            error_code = error_data.get(t('error_code'), '')
            error_name= error_data.get(t("error_name"),'')            
            category = error_data.get(t('category'), '')
            
            # If no error_code, try to get it from database by name
            if not error_code and error_name:
                lookup_query = f"""
                SELECT je.error_code 
                FROM java_errors je 
                WHERE je.{name_field} = %s
                LIMIT 1
                """
                lookup_result = self.db.execute_query(lookup_query, (error_name,), fetch_one=True)
                if lookup_result:
                    error_code = lookup_result['error_code']
            
            # Generate error_code if still missing
            if not error_code:
                import hashlib
                hash_input = f"{error_name}_{category}"
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
                user_id, error_code, error_name, error_name, category
            ))
            
            logger.info(f"Started practice session for user {user_id}, error {error_code} ({error_name})")
            
        except Exception as e:
            logger.error(f"Error starting practice session: {str(e)}")
    
    def complete_practice_session(self, user_id: str, error_code: str, 
                            session_data: Dict[str, Any]) -> None:
        """Record the completion of a practice session with results."""      
        if not user_id or not error_code:
            return
            
        try:
            accuracy = session_data.get(t('accuracy'), 0.0)
            time_spent = session_data.get(t('time_spent_seconds'), 0)
            successful = session_data.get(t('successful_completion'), False)            
            
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
                logger.warning(f"Completed practice session for user {user_id}, error {error_code}, accuracy: {accuracy}%")
            
        except Exception as e:
            logger.error(f"Error completing practice session: {str(e)}")