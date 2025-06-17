"""
Internationalization (i18n) package for Java Peer Review Training System.

This package provides proper i18n support with translation management,
language switching, and pluralization support.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class I18n:
    """
    Internationalization manager for the application.
    
    Provides translation services, language switching, and format support.
    """
    
    def __init__(self, default_locale: str = "en", locales_dir: str = None):
        """
        Initialize the I18n manager.
        
        Args:
            default_locale: Default language locale (e.g., 'en', 'zh')
            locales_dir: Directory containing translation files
        """
        self.default_locale = default_locale
        self.current_locale = default_locale
        self._translations = {}
        self._llm_instructions = {}
        
        # Set locales directory
        if locales_dir is None:
            self.locales_dir = Path(__file__).parent / "locales"
        else:
            self.locales_dir = Path(locales_dir)
        
        # Load all available translations
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files from the locales directory."""
        try:
            if not self.locales_dir.exists():
                logger.warning(f"Locales directory not found: {self.locales_dir}")
                return
            
            for locale_file in self.locales_dir.glob("*.json"):
                locale = locale_file.stem
                try:
                    with open(locale_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._translations[locale] = data.get('translations', {})
                        self._llm_instructions[locale] = data.get('llm_instructions', {})
                        logger.debug(f"Loaded {locale} translations: {len(self._translations[locale])} keys")
                except Exception as e:
                    logger.error(f"Error loading {locale} translations: {e}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
    
    def set_locale(self, locale: str) -> bool:
        """
        Set the current locale.
        
        Args:
            locale: Language locale to set
            
        Returns:
            True if locale was set successfully, False otherwise
        """
        if locale in self._translations:
            self.current_locale = locale
            logger.debug(f"Locale set to: {locale}")
            return True
        else:
            logger.warning(f"Locale not available: {locale}, using default: {self.default_locale}")
            self.current_locale = self.default_locale
            return False
    
    def get_locale(self) -> str:
        """Get the current locale."""
        return self.current_locale
    
    def translate(self, key: str, locale: str = None, **kwargs) -> str:
        """
        Translate a key to the specified or current locale.
        
        Args:
            key: Translation key
            locale: Target locale (uses current if None)
            **kwargs: Variables for string formatting
            
        Returns:
            Translated string
        """
        target_locale = locale or self.current_locale
        
        # Get translations for target locale
        translations = self._translations.get(target_locale, {})
        
        # Fall back to default locale if key not found
        if key not in translations and target_locale != self.default_locale:
            translations = self._translations.get(self.default_locale, {})
        
        # Get the translation
        translation = translations.get(key, key)
        
        # Apply formatting if kwargs provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Translation formatting error for key '{key}': {e}")
                return translation
        
        return translation
    
    def get_llm_instructions(self, locale: str = None) -> Dict[str, Any]:
        """
        Get LLM instructions for the specified or current locale.
        
        Args:
            locale: Target locale (uses current if None)
            
        Returns:
            Dictionary of LLM instructions
        """
        target_locale = locale or self.current_locale
        
        # Get instructions for target locale
        instructions = self._llm_instructions.get(target_locale, {})
        
        # Fall back to default locale if not found
        if not instructions and target_locale != self.default_locale:
            instructions = self._llm_instructions.get(self.default_locale, {})
        
        return instructions
    
    def get_available_locales(self) -> list:
        """Get list of available locales."""
        return list(self._translations.keys())
    
    def has_translation(self, key: str, locale: str = None) -> bool:
        """
        Check if a translation exists for a key.
        
        Args:
            key: Translation key
            locale: Target locale (uses current if None)
            
        Returns:
            True if translation exists, False otherwise
        """
        target_locale = locale or self.current_locale
        translations = self._translations.get(target_locale, {})
        return key in translations

# Global i18n instance
_i18n_instance = None

def init_i18n(default_locale: str = "en", locales_dir: str = None) -> I18n:
    """
    Initialize the global i18n instance.
    
    Args:
        default_locale: Default language locale
        locales_dir: Directory containing translation files
        
    Returns:
        I18n instance
    """
    global _i18n_instance
    _i18n_instance = I18n(default_locale, locales_dir)
    return _i18n_instance

def get_i18n() -> I18n:
    """
    Get the global i18n instance.
    
    Returns:
        I18n instance
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance

# Convenience functions for common operations
def t(key: str, **kwargs) -> str:
    """
    Translate a key using the global i18n instance.
    
    Args:
        key: Translation key
        **kwargs: Variables for string formatting
        
    Returns:
        Translated string
    """
    return get_i18n().translate(key, **kwargs)

def set_locale(locale: str) -> bool:
    """
    Set the current locale using the global i18n instance.
    
    Args:
        locale: Language locale to set
        
    Returns:
        True if locale was set successfully, False otherwise
    """
    return get_i18n().set_locale(locale)

def get_locale() -> str:
    """Get the current locale using the global i18n instance."""
    return get_i18n().get_locale()

def get_llm_instructions() -> Dict[str, Any]:
    """Get LLM instructions for the current locale."""
    return get_i18n().get_llm_instructions()

# Export main functions and classes
__all__ = [
    'I18n',
    'init_i18n', 
    'get_i18n',
    't',
    'set_locale',
    'get_locale',
    'get_llm_instructions'
]
