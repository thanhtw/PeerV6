"""
LLM Manager module for Java Peer Review Training System.

This module provides the LLMManager class for handling model initialization,
configuration, and management of OpenAI LLM provider with support for both
Chat Completions API and Responses API (required for GPT-5-Codex).
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Tuple, List, Union
from dotenv import load_dotenv 

# OpenAI integration
from openai import OpenAI as OpenAIClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
OPENAI_AVAILABLE = True

from langchain_core.language_models import BaseLanguageModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResponsesAPIWrapper:
    """
    Wrapper to make Responses API compatible with LangChain's BaseLanguageModel interface.
    GPT-5-Codex requires the Responses API, not Chat Completions API.
    """
    
    def __init__(self, client: OpenAIClient, model: str, temperature: float = 0.7, 
                 max_tokens: int = 4096, **kwargs):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        
    def invoke(self, input_data: Union[str, List[BaseMessage]], **kwargs) -> str:
        """
        Invoke the Responses API with LangChain-compatible interface.
        
        Args:
            input_data: Either a string or list of messages
            
        Returns:
            String response from the model
        """
        # Convert input to proper format
        if isinstance(input_data, str):
            user_content = input_data
        elif isinstance(input_data, list):
            # Extract the last user message
            user_messages = [msg for msg in input_data if hasattr(msg, 'content')]
            user_content = user_messages[-1].content if user_messages else str(input_data)
        else:
            user_content = str(input_data)
        
        try:
            # Call Responses API
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_content
                            }
                        ]
                    }
                ],
                text={
                    "format": {"type": "text"},
                    "verbosity": "medium"
                },
                tools=[],
                store=False
            )
            
            # Extract text from response
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                return content_item.text
            
            return str(response)
            
        except Exception as e:
            logger.error(f"Error calling Responses API: {str(e)}")
            raise
    
    def __call__(self, input_data: Union[str, List[BaseMessage]], **kwargs) -> str:
        """Allow direct calling of the wrapper."""
        return self.invoke(input_data, **kwargs)


class LLMManager:
    """
    LLM Manager for handling model initialization, configuration and management.
    Supports OpenAI models via Chat Completions API and Responses API.
    """
    
    def __init__(self):
        """Initialize the LLM Manager with environment variables."""
        load_dotenv(override=True)
        
        # Provider settings - set to OpenAI
        self.provider = "openai"
        
        # OpenAI settings
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY", "")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.openai_default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
        
        # Models that require Responses API
        self.responses_api_models = [
            "gpt-5-codex",
            "gpt-5-pro",
            "o3",
            "o3-mini"
        ]
        
        # Available OpenAI models
        self.openai_available_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-5-codex",  # Responses API only
            "gpt-5-pro"     # Responses API only
        ]
        
        # Track initialized models
        self.initialized_models = {}
        
        # Connection caching to avoid repeated tests
        self._connection_cache = {}
        self._cache_duration = 300  # 5 minutes
        
        # OpenAI client for Responses API
        self._openai_client = None
    
    def _get_openai_client(self) -> OpenAIClient:
        """Get or create OpenAI client for Responses API."""
        if self._openai_client is None:
            self._openai_client = OpenAIClient(
                api_key=self.openai_api_key,
                base_url=self.openai_api_base
            )
        return self._openai_client
    
    def set_provider(self, provider: str, api_key: str = None) -> bool:
        """
        Set the LLM provider to use and persist the selection.
        
        Args:
            provider: Provider name (must be 'openai')
            api_key: API key for OpenAI (required)
            
        Returns:
            bool: True if configuration successful, False otherwise
        """
        if provider.lower() != "openai":
            logger.error(f"Unsupported provider: {provider}. Only 'openai' is supported.")
            return False
            
        # Set the provider in instance and persist to environment
        self.provider = "openai"
        os.environ["LLM_PROVIDER"] = "openai"
        logger.debug(f"Provider set to: {self.provider}")
        
        # Clear initialized models to force reinitialization
        self.initialized_models = {}
        
        # Handle OpenAI setup
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI integration is not available. Please install openai package.")
            return False
            
        # Validate and set API key
        if not api_key and not self.openai_api_key:
            logger.error("API key is required for OpenAI provider")
            return False
            
        if api_key:
            self.openai_api_key = api_key
            os.environ["OPEN_AI_API_KEY"] = api_key
            # Reset client to use new API key
            self._openai_client = None
        
        # Clear connection cache when provider changes
        self._connection_cache = {}
        
        logger.debug(f"Successfully configured OpenAI provider")
        return True    
    
    def _is_connection_cached(self) -> Tuple[bool, Optional[bool], Optional[str]]:
        """Check if we have a recent connection test result cached."""
        if not self._connection_cache:
            return False, None, None
            
        cache_time = self._connection_cache.get("timestamp", 0)
        current_time = time.time()
        
        if current_time - cache_time < self._cache_duration:
            return True, self._connection_cache.get("connected", False), self._connection_cache.get("message", "")
        
        return False, None, None
    
    def _cache_connection_result(self, connected: bool, message: str):
        """Cache the connection test result."""
        self._connection_cache = {
            "connected": connected,
            "message": message,
            "timestamp": time.time()
        }
    
    def check_openai_connection(self, force_check: bool = False) -> Tuple[bool, str]:
        """
        Check if OpenAI API is accessible with the current API key.
        Uses caching to avoid repeated checks unless forced.
        
        Args:
            force_check: Force a new connection check even if cached
            
        Returns:
            Tuple[bool, str]: (is_connected, message)
        """
        # Check cache first unless forced
        if not force_check:
            has_cache, is_connected, message = self._is_connection_cached()
            if has_cache:
                logger.debug(f"Using cached connection status: {is_connected}")
                return is_connected, message
        
        if not self.openai_api_key:
            result = False, "No OpenAI API key provided"
            self._cache_connection_result(*result)
            return result
            
        if not OPENAI_AVAILABLE:
            result = False, "OpenAI integration is not available. Please install openai package."
            self._cache_connection_result(*result)
            return result
            
        try:
            # Use ChatOpenAI for connection testing
            chat = ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-3.5-turbo",
                max_tokens=10
            )
            
            # Make a minimal API call
            response = chat.invoke([HumanMessage(content="test")])
            
            result = True, f"Connected to OpenAI API successfully"
            logger.debug("OpenAI connection test successful")
            
        except Exception as e:
            error_message = str(e)
            if "auth" in error_message.lower() or "api key" in error_message.lower() or "unauthorized" in error_message.lower():
                result = False, "Invalid OpenAI API key"
            else:
                result = False, f"Error connecting to OpenAI API: {error_message}"
            logger.debug(f"OpenAI connection test failed: {result[1]}")
        
        self._cache_connection_result(*result)
        return result

    def initialize_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[BaseLanguageModel]:
        """
        Initialize an OpenAI model.
        Automatically uses Chat Completions API or Responses API based on model.
        
        Args:
            model_name (str): Name of the model to initialize
            model_params (Dict[str, Any], optional): Model parameters
            
        Returns:
            Optional[BaseLanguageModel]: Initialized LLM or None if initialization fails
        """
        return self._initialize_openai_model(model_name, model_params)
    
    def _initialize_openai_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[Union[ChatOpenAI, ResponsesAPIWrapper]]:
        """
        Initialize an OpenAI model using the appropriate API.
        Uses Responses API for gpt-5-codex and similar models.
        Uses Chat Completions API for other models.
        
        Args:
            model_name: Name of the model to initialize
            model_params: Model parameters
            
        Returns:
            Initialized model instance or None if initialization fails
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI integration is not available. Please install openai package.")
            return None
            
        if not self.openai_api_key:
            logger.error("No OpenAI API key provided")
            return None
            
        # Apply default model parameters if none provided
        if model_params is None:
            model_params = self._get_openai_default_params(model_name)
            
        try:
            # Check if model requires Responses API
            if model_name in self.responses_api_models:
                logger.info(f"Initializing {model_name} with Responses API")
                client = self._get_openai_client()
                llm = ResponsesAPIWrapper(
                    client=client,
                    model=model_name,
                    temperature=model_params.get("temperature", 0.7),
                    max_tokens=model_params.get("max_tokens", 4096)
                )
            else:
                # Use Chat Completions API for standard models
                logger.info(f"Initializing {model_name} with Chat Completions API")
                llm = ChatOpenAI(
                    api_key=self.openai_api_key,
                    model=model_name,
                    temperature=model_params.get("temperature", 0.7),
                    max_tokens=model_params.get("max_tokens", 2048),
                    verbose=True
                )
            
            logger.debug(f"Successfully initialized OpenAI model: {model_name}")
            return llm
                
        except Exception as e:
            logger.error(f"Error initializing OpenAI model {model_name}: {str(e)}")
            return None
    
    def initialize_model_from_env(self, model_key: str, temperature_key: str) -> Optional[BaseLanguageModel]:
        """
        Initialize a model using environment variables.
        
        Args:
            model_key (str): Environment variable key for model name
            temperature_key (str): Environment variable key for temperature
            
        Returns:
            Optional[BaseLanguageModel]: Initialized LLM or None if initialization fails
        """
        logger.debug(f"Initializing model from env with OpenAI provider")
        
        # Get OpenAI model name from environment variables
        openai_model_key = f"OPENAI_{model_key}"
        model_name = os.getenv(openai_model_key, self.openai_default_model)
        
        # Map common model name aliases
        model_aliases = {
            "gpt4": "gpt-4",
            "gpt-4-turbo-preview": "gpt-4-turbo",
            "gpt35": "gpt-3.5-turbo",
            "gpt-35-turbo": "gpt-3.5-turbo"
        }
        
        if model_name in model_aliases:
            model_name = model_aliases[model_name]
        
        logger.info(f"Using OpenAI model: {model_name}")
        
        # Get temperature
        try:
            temperature = float(os.getenv(temperature_key, "0.7"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid temperature value for {temperature_key}, using default 0.7")
            temperature = 0.7
        
        # Set up model parameters
        model_params = {
            "temperature": temperature
        }
        
        # Initialize the model
        logger.debug(f"Initializing model {model_name} with params: {model_params}")
        return self.initialize_model(model_name, model_params)
    
    def _get_openai_default_params(self, model_name: str) -> Dict[str, Any]:
        """
        Get default parameters for an OpenAI model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Default parameters for the model
        """
        # Basic defaults for OpenAI
        params = {
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        # Adjust based on model capabilities and role
        if "gpt-4" in model_name or "gpt-5" in model_name:
            params["max_tokens"] = 4096  # GPT-4/5 models can handle more tokens
        
        # Special settings for GPT-5-Codex (Responses API model)
        if "gpt-5-codex" in model_name:
            params["temperature"] = 0.3  # Lower temperature for coding tasks
            params["max_tokens"] = 4096
            params["reasoning_effort"] = "medium"  # Responses API parameter
        # Adjust temperature based on task type (inferred from context)
        elif "generative" in model_name.lower():
            params["temperature"] = 0.8  # Higher creativity for generative tasks
        elif "review" in model_name.lower():
            params["temperature"] = 0.3  # Lower temperature for review tasks
        elif "summary" in model_name.lower():
            params["temperature"] = 0.4  # Moderate temperature for summary tasks
        elif "compare" in model_name.lower():
            params["temperature"] = 0.5  # Balanced temperature for comparison tasks
        
        return params

    def get_available_models(self) -> list:
        """
        Get list of available OpenAI models.
        
        Returns:
            List of available model names
        """
        return self.openai_available_models.copy()
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available in OpenAI.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        return model_name in self.openai_available_models