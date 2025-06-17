"""
Language utilities for Java Peer Review Training System.

This module provides utilities for handling language selection and translation.
Updated to use the new i18n package for proper internationalization.
"""

import streamlit as st
import os
import logging
import sys
from typing import Dict, Any, Optional

# Add the parent directory to the path to allow absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import i18n package
from i18n import init_i18n, get_i18n, t as i18n_t, set_locale as i18n_set_locale, get_locale as i18n_get_locale, get_llm_instructions as i18n_get_llm_instructions

# Configure logging
logger = logging.getLogger(__name__)

# Initialize i18n with locales directory
_i18n_initialized = False

def _ensure_i18n_initialized():
    """Ensure i18n is initialized."""
    global _i18n_initialized
    if not _i18n_initialized:
        locales_dir = os.path.join(parent_dir, "i18n", "locales")
        init_i18n(default_locale="en", locales_dir=locales_dir)
        _i18n_initialized = True

# Constants for backward compatibility
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "zh"]

def init_language():
    """Initialize language selection in session state."""
    _ensure_i18n_initialized()
    
    if "language" not in st.session_state:
        st.session_state.language = DEFAULT_LANGUAGE
    
    # Set i18n locale to match session state
    i18n_set_locale(st.session_state.language)

def set_language(lang: str):
    """
    Set the application language.
    
    Args:
        lang: Language code (e.g., 'en', 'zh')
    """
    _ensure_i18n_initialized()
    
    if lang in SUPPORTED_LANGUAGES:
        st.session_state.language = lang
        i18n_set_locale(lang)
    else:
        logger.warning(f"Unsupported language: {lang}, using default: {DEFAULT_LANGUAGE}")
        st.session_state.language = DEFAULT_LANGUAGE
        i18n_set_locale(DEFAULT_LANGUAGE)

def get_current_language() -> str:
    """
    Get the current language.
    
    Returns:
        Current language code
    """
    _ensure_i18n_initialized()
    
    # Sync session state with i18n if needed
    if hasattr(st, 'session_state') and 'language' in st.session_state:
        session_lang = st.session_state.language
        i18n_lang = i18n_get_locale()
        if session_lang != i18n_lang:
            i18n_set_locale(session_lang)
        return session_lang
    
    return i18n_get_locale()

def t(key: str, **kwargs) -> str:
    """
    Translate a text key to the current language.
    
    Args:
        key: Text key to translate
        **kwargs: Variables for string formatting
        
    Returns:
        Translated text
    """
    _ensure_i18n_initialized()
    
    # Ensure locale is synced
    current_lang = get_current_language()
    if i18n_get_locale() != current_lang:
        i18n_set_locale(current_lang)
    
    return i18n_t(key, **kwargs)

def get_translations(language: str = None) -> Dict[str, str]:
    """
    Get translations for the specified language.
    
    Args:
        language: Language code ('en' or 'zh'), uses current if None
        
    Returns:
        Dictionary of translations (for backward compatibility)
    """
    _ensure_i18n_initialized()
    
    target_lang = language or get_current_language()
    
    # Get the i18n instance
    i18n_instance = get_i18n()
    
    # Return the translations dictionary for the target language
    return i18n_instance._translations.get(target_lang, {})

def get_llm_prompt_instructions(language: str = None) -> Dict[str, Any]:
    """
    Get LLM prompt instructions for the specified language.
    
    Args:
        language: Language code ('en' or 'zh'), uses current if None
        
    Returns:
        Dictionary of LLM instructions
    """
    _ensure_i18n_initialized()
    
    target_lang = language or get_current_language()
    
    # Temporarily set locale if different
    original_locale = i18n_get_locale()
    if target_lang != original_locale:
        i18n_set_locale(target_lang)
    
    instructions = i18n_get_llm_instructions()
    
    # Restore original locale
    if target_lang != original_locale:
        i18n_set_locale(original_locale)
    
    return instructions

def render_language_selector():
    """Render a simplified language selector in the sidebar."""
    _ensure_i18n_initialized()
    
    with st.sidebar:
        st.subheader(t("language"))
        cols = st.columns([1, 1])
        
        with cols[0]:
            if st.button("English", use_container_width=True, 
                         disabled=get_current_language() == "en"):
                set_language("en")
                st.session_state.full_reset = True
                st.rerun()
                
        with cols[1]:
            if st.button("繁體中文", use_container_width=True, 
                         disabled=get_current_language() == "zh"):
                set_language("zh")
                st.session_state.full_reset = True
                st.rerun()

def get_available_languages() -> Dict[str, str]:
    """
    Get available languages with their display names.
    
    Returns:
        Dictionary mapping language codes to display names
    """
    return {
        "en": "English",
        "zh": "繁體中文"
    }

# Backward compatibility exports
__all__ = [
    'init_language',
    'set_language', 
    'get_current_language',
    't',
    'get_translations',
    'get_llm_prompt_instructions',
    'render_language_selector',
    'get_available_languages',
    'DEFAULT_LANGUAGE',
    'SUPPORTED_LANGUAGES'
]