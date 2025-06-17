"""
Student Behavior Tracking Service for Java Peer Review Training System.

This service provides comprehensive tracking of student interactions, learning patterns,
and behavior analytics for educational research and system improvement.
"""

import uuid
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import streamlit as st
from data.mysql_connection import MySQLConnection
from utils.language_utils import get_current_language

logger = logging.getLogger(__name__)

class BehaviorTracker:
    """
    Comprehensive behavior tracking service for educational analytics.
    """
    
    def __init__(self):
        """Initialize the behavior tracker with database connection."""
        self.db = MySQLConnection()
        self.current_language = get_current_language()
    
    def log_interaction(self, 
                       user_id: str,
                       interaction_type: str,
                       interaction_category: str,    
                       details: Dict[str, Any] = None,
                       time_spent_seconds: int = 0,
                       success: bool = True) -> None:
        """
        Log a detailed user interaction.
        
        Args:
            user_id: The user's ID
            interaction_type: Type of interaction (e.g., 'click', 'submit', 'navigation')
            interaction_category: Category (e.g., 'code_generation', 'review', 'practice')   
            details: Additional details about the interaction
            time_spent_seconds: Time spent on this interaction
            success: Whether the interaction was successful
        """
        try:
            # Validate required parameters
            if not user_id or not interaction_type or not interaction_category:
                logger.error(f"Missing required parameters: user_id={user_id}, interaction_type={interaction_type}, interaction_category={interaction_category}")
                return
            
            # Check database connection
            if not self.db:
                logger.error("Database connection not initialized")
                return
            
            # Test database connection
            try:
                self.db.execute_query("SELECT 1", ())
            except Exception as db_test_error:
                logger.error(f"Database connection test failed: {str(db_test_error)}")
                return
            
            # Increment interaction counter (optional - only if session state is available)
            if hasattr(st, 'session_state'):
                st.session_state.interaction_count = st.session_state.get("interaction_count", 0) + 1
            
            # Prepare data with validation
            details_json = json.dumps(details) if details else None
            time_spent_seconds = 0
            # Log the data being inserted for debugging
            logger.debug(f"Attempting to log interaction - User: {user_id}, Type: {interaction_type}, Category: {interaction_category}")
            
            # Insert interaction record with proper error handling
            query = """
            INSERT INTO user_interactions 
            (user_id, interaction_type, interaction_category, 
             details, time_spent_seconds, success)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = (               
                user_id,
                interaction_type,
                interaction_category,   
                details_json,
                time_spent_seconds,
                success              
            )
            
            # Log parameters for debugging
            logger.debug(f"Query parameters: {params}")
            
            # Execute with better error handling
            result = self.db.execute_query(query, params)
            
            # Verify insertion was successful
            if result is not None:
                logger.debug(f"Successfully logged interaction: {interaction_category}.for user {user_id}")
            else:
                logger.warning(f"Query executed but no result returned for interaction: {interaction_category}")
            
        except Exception as e:
            logger.error(f"Error logging interaction: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
     
behavior_tracker = BehaviorTracker()