"""
Main UI utilities for Java Peer Review Training System.

This module provides core UI utility functions for the Streamlit interface,
including session state management, tab rendering, and LLM logs.
"""

import streamlit as st
import os
import logging
import re
import json
import time
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

def create_tabs_with_workflow_control(tab_labels: List[str], workflow_info: Dict[str, Any]):
    """
    Create tabs with workflow-based visual indicators and accessibility.
    
    Args:
        tab_labels: List of tab label strings
        workflow_info: Dictionary containing workflow state information
        
    Returns:
        Streamlit tabs object
    """
    try:
        enhanced_labels = []
        
        for i, label in enumerate(tab_labels):
            accessible_tabs = workflow_info.get("accessible_tabs", [])
            blocked_tabs = workflow_info.get("blocked_tabs", [])
            current_phase = workflow_info.get("current_phase", "initial")
            
            if i in blocked_tabs:
                enhanced_labels.append(f"🔒 {label}")
            elif i in accessible_tabs:
                tab_step_mapping = {
                    0: "tutorial", 1: "generate", 2: "review", 3: "complete"
                }
                expected_step = tab_step_mapping.get(i, "")
                
                if current_phase == expected_step:
                    enhanced_labels.append(f"▶️ {label}")
                elif _is_tab_completed(i, workflow_info):
                    enhanced_labels.append(f"✅ {label}")
                else:
                    enhanced_labels.append(f"🔓 {label}")
            else:
                enhanced_labels.append(label)
        
        return st.tabs(enhanced_labels)
        
    except Exception as e:
        logger.error(f"Error creating enhanced tabs: {str(e)}")
        return st.tabs(tab_labels)
    
def _is_tab_completed(tab_index: int, workflow_info: Dict[str, Any]) -> bool:
    """Check if a specific tab/step is completed."""
    try:
        if tab_index == 1:  # Generate tab
            return workflow_info.get("has_code", False)
        elif tab_index == 2:  # Review tab
            return workflow_info.get("review_complete", False)
        return False
    except Exception as e:
        logger.error(f"Error checking tab completion: {str(e)}")
        return False

def render_professional_sidebar(llm_manager):
    """
    Render an enhanced professional sidebar with better styling.
    
    Args:
        llm_manager: LLMManager instance
    """
    from utils.language_utils import t
    
    with st.sidebar:
        # Enhanced LLM Provider info with better styling
        st.markdown(f"""
        <div class="sidebar-section">
            <h3 class="sidebar-title">🤖 {t('llm_provider_setup')}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        provider = llm_manager.provider.capitalize()
        
        if provider == "Groq":
            connection_status, message = llm_manager.check_groq_connection()
            
            # Enhanced status display
            status_color = "#28a745" if connection_status else "#dc3545"
            status_icon = "✅" if connection_status else "❌"
            status_text = t("connected") if connection_status else t("disconnected")
            
            st.markdown(f"""
            <div class="provider-status">
                <div class="provider-info">
                    <strong>{t('provider')}:</strong> {provider}
                </div>
                <div class="status-indicator" style="color: {status_color};">
                    {status_icon} <strong>{status_text}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if not connection_status:
                st.error(f"⚠️ {t('error')}: {message}")
                st.info(t("groq_api_message"))
        
        # Add system status section
        st.markdown("---")
        st.markdown(f"""
        <div class="sidebar-section">
            <h4 class="sidebar-subtitle">📊 {t('system_status')}</h4>
        </div>
        """, unsafe_allow_html=True)

