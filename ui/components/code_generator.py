"""
Code Generator UI component for Java Peer Review Training System.

This module provides a professional UI for configuring and generating Java code snippets
with intentional errors for review practice. Revised to properly integrate with workflow manager.
FIXED: Proper handling of LangGraph state objects (AddableValuesDict).
"""

import streamlit as st
import logging
from typing import Dict, List, Any, Optional
from data.database_error_repository import DatabaseErrorRepository
from utils.language_utils import get_current_language, t
from state_schema import WorkflowState
from utils.code_utils import _get_category_icon, _log_user_interaction_code_generator
from utils.workflow_controller import workflow_controller
logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)
import time



class CodeGeneratorUI:
    """
    Professional UI component for Java code generation with clean layout and intuitive workflow.
    Now properly integrated with the workflow manager system.    
    """
    
    def __init__(self, workflow, code_display_ui):
        """Initialize the CodeGeneratorUI with database repository and workflow."""
        self.db_repository = DatabaseErrorRepository()
        self.current_language = get_current_language()
        self.workflow = workflow  # This is JavaCodeReviewGraph
        self.code_display_ui = code_display_ui
        
        # Get reference to the workflow manager for proper workflow execution
        self.workflow_manager = getattr(workflow, 'workflow_manager', None)        
        self.interaction_timers = {}
        self.session_start_time = time.time()
        
    def render(self, user_level: str = "medium"):
        """
        Render the professional code generation interface.
        
        Args:
            user_level: User's experience level (basic, medium, senior)
        """

        # Check workflow state before allowing generation
        workflow_info = workflow_controller.get_workflow_state_info()
        
        if not workflow_info["can_generate"]:
            st.warning("🔒 " + t("complete_current_review_before_generating"))
            st.info("📋 " + t("go_to_review_tab_to_continue"))
            
            # Show current code if available
            if workflow_info["has_code"] and hasattr(st.session_state.workflow_state, 'code_snippet'):
                st.markdown("### " + t("current_generated_code"))
                self.code_display_ui.render_code_display(st.session_state.workflow_state.code_snippet)
            
            return
        
        # Show workflow reset option if review is complete
        if workflow_info["review_complete"]:
            st.success("🎉 " + t("previous_review_completed"))
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info("💡 " + t("start_new_review_cycle"))
            with col2:
                if st.button("🔄 " + t("start_new_cycle"), type="primary"):
                    workflow_controller.reset_workflow_for_new_cycle()
                    st.rerun()
        
        # Check for tab switching flag and handle it
        if st.session_state.get("switch_to_review_tab", False):
            # Clear the flag
            st.session_state.switch_to_review_tab = False
            # Set active tab
            st.session_state.active_tab = 1
            st.rerun()
            return
        
        # Professional header section
        #self._render_header()
    
        # Initialize session state properly
        self._initialize_session_state()
        
        # Main content in clean sections
        self._render_configuration_section(user_level)
        
        # Generated code display section
        self._render_code_display_section()
   
    def _initialize_session_state(self):
        """Initialize session state variables with correct data types."""
        if "selected_categories" not in st.session_state:
            st.session_state.selected_categories = []
        
        # Remove advanced mode variables - only use random mode
        st.session_state.error_selection_mode = "random"
        
        # Ensure selected_categories is always a list
        if not isinstance(st.session_state.selected_categories, list):
            st.session_state.selected_categories = []

    def _render_code_display_section(self):
        """Render the generated code display section - FIXED: Handle regeneration properly."""
        if hasattr(st.session_state, 'workflow_state') and st.session_state.workflow_state:
            state = st.session_state.workflow_state
            
            if hasattr(state, 'code_snippet') and state.code_snippet:
                
                # Display the code
                self.code_display_ui.render_code_display(state.code_snippet)
                
                # Regenerate option
                st.markdown(f"""
                <div class="regenerate-section">
                    <h4>🔄 {t('not_satisfied_with_the_result')}</h4>
                    <p>{t('generate_a_new_code_snippet_with_the_same_configuration')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # FIXED: Remove on_click callback
                if st.button(f"🔄 {t('generate_new')}", key="regenerate", use_container_width=True):
                    self._handle_code_generation_with_tracking()

    def _render_configuration_section(self, user_level: str):
        """Render the configuration section with category selection only."""
        # st.markdown('<div class="generate-section">', unsafe_allow_html=True)
        
        # Section header
        # st.markdown(f"""
        # <div class="section-header">
        #     <span class="section-icon">⚙️</span>
        #     <div>
        #         <h3 class="section-title">{t('configuration')}</h3>
        #         <p class="section-subtitle">{t('setup_code_generation_parameters')}</p>
        #     </div>
        # </div>
        # """, unsafe_allow_html=True)
        
        # Parameters display
        self._render_parameters_display(user_level)
        
        # Category selection interface (no tabs needed)
        self._render_category_selection_interface()
        
        # st.markdown('</div>', unsafe_allow_html=True)

    def _render_category_selection_interface(self):
        """Render the category selection interface without mode tabs."""
        st.markdown(f"""
        <div class="mode-description">
            <p>🎲 {t('random_mode_description')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        self._render_category_selection()
        
        selected_categories = st.session_state.get("selected_categories", [])
        if selected_categories:
            st.markdown(
                f"<div class='selected-categories'>"
                + "".join(
                    f"<span class='selected-category-item'>{_get_category_icon(cat)} {cat}</span>"
                    for cat in selected_categories
                )
                + "</div>",
                unsafe_allow_html=True
            )
        
        # st.markdown('<div class="generate-button-section">', unsafe_allow_html=True)
        
        
        if st.button(
            f"🔧 {t('generate_code_problem')}",
            key="generate_code_main",
            type="primary",
            use_container_width=True,
            disabled=not self._can_generate()
        ):
            if self._can_generate():                
                self._handle_code_generation_with_tracking()
        
        # st.markdown('</div>', unsafe_allow_html=True)
        
        if not selected_categories:
            st.warning(f"⚠️ {t('please_select_at_least_one_error_category')}")

    def _render_parameters_display(self, user_level: str):
        """Render the parameters display with visual cards, supporting both English and Chinese."""
        # Always use the canonical user_level key for lookup (internal: 'basic', 'medium', 'senior')
        # Accept both English and localized user_level
        internal_levels = ["basic", "medium", "senior"]
        localized_levels = [t("basic"), t("medium"), t("senior")]
        # Map user_level to internal if possible
        user_level_key = user_level.lower()
        
        if user_level_key in internal_levels:
            internal_level = user_level_key
        elif user_level_key in localized_levels:
            internal_level = internal_levels[localized_levels.index(user_level_key)]
        else:
            internal_level = "medium"

        params = self._get_level_parameters(user_level)
        
        # Localize code_length and difficulty values
        code_length_localized = {
            "short": t("short"),
            "medium": t("medium"),
            "long": t("long")
        }.get(params['code_length'], params['code_length'])

        difficulty_localized = {
            "easy": t("easy"),
            "medium": t("medium"),
            "hard": t("hard")
        }.get(params['difficulty'], params['difficulty'])

        # Display parameters in a grid
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""
            <div class="parameter-card">
                <span class="parameter-icon">📏</span>
                <div class="parameter-label">{t('code_length')}</div>
                <div class="parameter-value">{code_length_localized}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"""
            <div class="parameter-card">
                <span class="parameter-icon">⭐</span>
                <div class="parameter-label">{t('difficulty')}</div>
                <div class="parameter-value">{difficulty_localized}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"""
            <div class="parameter-card">
                <span class="parameter-icon">🐛</span>
                <div class="parameter-label">{t('error_count')}</div>
                <div class="parameter-value">{params['error_count_start']} - {params['error_count_end']}</div>
            </div>
            """, unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"""
            <div class="parameter-card">
                <span class="parameter-icon">👤</span>
                <div class="parameter-label">{t('your_level')}</div>
                <div class="parameter-value">{t(user_level_key) if user_level_key in localized_levels else t(internal_level)}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="parameters-note">
            💡 {t('these_parameters_optimized')}
        </div>
        """, unsafe_allow_html=True)

    def _render_category_selection(self):
        """Render the category selection interface with professional styling."""
        
        # Load error categories
        categories_dict = self._get_error_categories()
        
        # Initialize selected categories
        if "selected_categories" not in st.session_state:
            st.session_state.selected_categories = []
        
        # Extract the java_errors list and pass it to the grid
        java_categories = categories_dict.get("java_errors", [])
        if java_categories:
            self._render_category_grid(java_categories)
        else:
            st.warning(t("no_categories_available"))

    def _toggle_category(self, category_name: str):
        """Toggle category selection without triggering rerun."""
        
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        if user_id:
            interaction_type = "select_category" if category_name not in st.session_state.get("selected_categories", []) else "deselect_category"
            _log_user_interaction_code_generator(
                user_id=user_id,
                interaction_category="practice",
                interaction_type=interaction_type,               
                details={"category": category_name}
            )
            
        # Ensure selected_categories is initialized as a list
        if "selected_categories" not in st.session_state:
            st.session_state.selected_categories = []
        
        # Ensure it's always a list
        if not isinstance(st.session_state.selected_categories, list):
            st.session_state.selected_categories = []
        
        if category_name in st.session_state.selected_categories:
            st.session_state.selected_categories.remove(category_name)
        else:
            st.session_state.selected_categories.append(category_name)
        
    def _render_category_grid(self, categories: List[str]):
        """Render categories in a compact three-column layout with parameter card styling."""
        # Ensure selected_categories is a list
        selected = st.session_state.get("selected_categories", [])
        if not isinstance(selected, list):
            selected = []
            st.session_state.selected_categories = []
        
        # Three-column grid for better space utilization
        cols = st.columns(3, gap="medium")
        
        # Distribute categories across three columns
        for i, category_name in enumerate(categories):
            description = f"{t('practice_with')} {category_name} {t('related_errors')}"
            icon = _get_category_icon(category_name)
            is_selected = category_name in selected
            
            # Current column (cycle through 0, 1, 2)
            current_col = cols[i % 3]
            
            with current_col:
                # Parameter card style with selection state
                selected_class = "selected" if is_selected else ""
                selection_indicator = f"✓ {t('selected')}" if is_selected else f"{t('click_to_select')}"

                st.markdown(f"""
                <div class="parameter-card category-card {selected_class}">
                    <span class="parameter-icon">{icon}</span>
                    <div class="parameter-label">{category_name}</div>
                </div>
                """, unsafe_allow_html=True)
               
                # FIXED: Remove st.rerun() from button callback
                if st.button(
                    selection_indicator,
                    key=f"category_card_{category_name}",
                    help=description,
                    use_container_width=True
                ):
                    self._toggle_category(category_name)
                    # FIXED: Remove st.rerun() call
        
        # Compact quick actions optimized for 3-column layout
        if categories and len(categories) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(
                    f"🎯 {t('select')} {t('all')}",
                    key="select_all_categories",
                    help=f"{t('select_all_available_categories')}",
                    use_container_width=True,
                    disabled=len(selected) == len(categories)
                ):
                    st.session_state.selected_categories = categories.copy()
                    # FIXED: Remove st.rerun() call
            
            with col2:
                if st.button(
                    f"🗑️ {t('clear_all')}",
                    key="clear_all_categories", 
                    help=f"{t('remove_all_selected_categories')}",
                    use_container_width=True,
                    disabled=len(selected) == 0
                ):
                    st.session_state.selected_categories = []
                    # FIXED: Remove st.rerun() call

    def _can_generate(self) -> bool:
        """Check if we can generate code based on selected categories."""
        selected_categories = st.session_state.get("selected_categories", [])
        return len(selected_categories) > 0

    def _get_level_parameters(self, user_level: str) -> Dict[str, Any]:
        """Get parameters based on user level."""

        level_configs = {
            f"{t('basic').lower()}": {
                "code_length": "short",
                "difficulty": "easy",
                "error_count_start": "1",
                "error_count_end": "2"
            },
            f"{t('medium').lower()}": {
                "code_length": "medium", 
                "difficulty": "medium",
                "error_count_start": "2",
                "error_count_end": "3"
            },
            f"{t('senior').lower()}": {
                "code_length": "long",
                "difficulty": "hard", 
                "error_count_start": "3",
                "error_count_end": "5"
            }
        }
        return level_configs.get(user_level.lower(), level_configs[f"{t('medium').lower()}"])

    def _render_header(self):
        """Render the professional header with branding and description."""
        st.markdown(f"""
        <div class="generate-header">
            <h2>🔧 {t('code_generation_workshop')}</h2>
            <p>{t('configure_generate_java_code')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    def _get_error_categories(self) -> Dict[str, List[str]]:
        """Get all available error categories."""
        try:      
            return self.db_repository.get_all_categories() 
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return {"java_errors": []}
    
    def _prepare_workflow_state(self) -> Optional[WorkflowState]:
        """
        Prepare the workflow state for code generation (random mode only).
        
        Returns:
            WorkflowState if preparation is successful, None otherwise
        """
        try:
            # Initialize or get workflow state
            if not hasattr(st.session_state, 'workflow_state') or st.session_state.workflow_state is None:
                st.session_state.workflow_state = WorkflowState()
            
            # Get user level from session state or use default
            user_level = st.session_state.get("user_level", "medium")
            params = self._get_level_parameters(user_level)
            
            # Update workflow state with parameters
            workflow_state = st.session_state.workflow_state
            workflow_state.code_length = params["code_length"]
            workflow_state.difficulty_level = params["difficulty"]
            workflow_state.error_count_start = params["error_count_start"]
            workflow_state.error_count_end = params["error_count_end"]  
            
            # Only random mode: use selected categories
            selected_categories = st.session_state.get("selected_categories", [])
            if not selected_categories:
                st.error("❌ Please select at least one category")
                return None
            
            # Format for workflow
            categories_dict = {"java_errors": selected_categories}
            workflow_state.selected_error_categories = categories_dict
            workflow_state.selected_specific_errors = []
            
            logger.debug(f"Random mode: Selected categories: {selected_categories}")
            
            # Reset workflow state for fresh generation
            workflow_state.current_step = "generate"
            workflow_state.evaluation_attempts = 0
            workflow_state.evaluation_result = None
            workflow_state.error = None
            
            return workflow_state
            
        except Exception as e:
            logger.error(f"Error preparing workflow state: {str(e)}")
            st.error(f"❌ Failed to prepare generation parameters: {str(e)}")
            return None

    def _execute_code_generation_workflow(self, workflow_state: WorkflowState) -> WorkflowState:
        """
        Execute the code generation through the LangGraph workflow system.
        
        Args:
            workflow_state: Prepared workflow state
            
        Returns:
            Updated workflow state after execution
        """
        try:
            logger.debug("Executing code generation through compiled LangGraph workflow")
            
            # Use the workflow manager to execute code generation
            updated_state = self.workflow_manager.execute_code_generation_workflow(workflow_state)
            return updated_state
                
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            workflow_state.error = f"Workflow execution failed: {str(e)}"
            return workflow_state

    def _safe_get_state_value(self, state, key: str, default=None):
        """
        Safely get a value from a state object, handling both dict-like and attribute access.
        
        Args:
            state: State object (could be WorkflowState, dict, or AddableValuesDict)
            key: Key to access
            default: Default value if key not found
            
        Returns:
            Value from state or default
        """
        try:
            # Try attribute access first (for WorkflowState objects)
            if hasattr(state, key):
                return getattr(state, key)
            
            # Try dictionary access (for dict-like objects)
            if hasattr(state, '__getitem__'):
                try:
                    return state[key]
                except (KeyError, TypeError):
                    pass
            
            # Try get method (for dict-like objects)
            if hasattr(state, 'get'):
                return state.get(key, default)
            
            return default
            
        except Exception as e:
            logger.warning(f"Error accessing key '{key}' from state: {str(e)}")
            return default

    def _convert_state_to_workflow_state(self, state) -> WorkflowState:
        """
        Convert a state object (potentially AddableValuesDict) to a WorkflowState object.
        
        Args:
            state: State object from LangGraph workflow
            
        Returns:
            WorkflowState object
        """
        try:
            # If it's already a WorkflowState, return as-is
            if isinstance(state, WorkflowState):
                return state
            
            # If it's dict-like, extract all the fields
            state_dict = {}
            
            # Define all possible WorkflowState fields
            workflow_state_fields = [
                'current_step', 'workflow_phase', 'code_length', 'difficulty_level', 'domain',
                'error_count_start', 'error_count_end', 'selected_error_categories',
                'selected_specific_errors', 'code_snippet', 'original_error_count',
                'evaluation_attempts', 'max_evaluation_attempts', 'evaluation_result',
                'code_generation_feedback', 'pending_review', 'current_iteration',
                'max_iterations', 'review_sufficient', 'review_history',
                'comparison_report', 'error', 'final_summary'
            ]
            
            # Extract each field
            for field in workflow_state_fields:
                value = self._safe_get_state_value(state, field)
                if value is not None:
                    state_dict[field] = value
            
            # Create and return new WorkflowState
            return WorkflowState(**state_dict)
            
        except Exception as e:
            logger.error(f"Error converting state to WorkflowState: {str(e)}")
            # Return a minimal WorkflowState with error
            return WorkflowState(error=f"State conversion failed: {str(e)}")

    def _handle_code_generation_with_tracking(self):
        """Enhanced code generation with comprehensive behavior tracking."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        generation_start_time = time.time()
        
        
        st.session_state.workflow_start_time = generation_start_time
        
        with st.spinner(f"🔧 {t('generating_your_java_code_challenge')}"):
            try:
                logger.debug("Starting code generation through workflow manager")
                
                # Track generation attempt
                
                # Prepare workflow state
                workflow_state = self._prepare_workflow_state()
                if not workflow_state:
                    return
                if user_id:
                    _log_user_interaction_code_generator(
                        user_id=user_id,
                        interaction_category="practice",
                        interaction_type="start_generate",                        
                        details={
                            "selected_categories": st.session_state.get("selected_categories", []),
                            "categories_count": len(st.session_state.get("selected_categories", [])),
                            "user_level": st.session_state.get("user_level", "medium")
                        }
                    )
                # Execute code generation through the workflow system
                updated_state = self._execute_code_generation_workflow(workflow_state)
                
                code_snippet = self._safe_get_state_value(updated_state, 'code_snippet')
                
                if user_id:
                    generation_time = int(time.time() - generation_start_time)
                    _log_user_interaction_code_generator(
                        user_id=user_id,
                        interaction_category="pratice",
                        interaction_type="generate_completed",                       
                        success=True,
                        time_spent_seconds=generation_time,
                        details={                            
                            "language": self.current_language,
                            "categories_generated": st.session_state.get("selected_categories", [])
                        }
                    )
                generation_duration = time.time() - generation_start_time
                
                # Handle the result with tracking
                self._handle_generation_result_with_tracking(updated_state, generation_duration)
                
                # Log code ready for review
                _log_user_interaction_code_generator(
                    user_id=user_id,
                    interaction_category="practice",
                    interaction_type="code_ready_for_review",                    
                    details={
                        "has_code_snippet": bool(code_snippet),
                        "ready_for_review": True,
                        "workflow_step": "review_ready"
                    }
                )
            except Exception as e:
                logger.error(f"Code generation error: {str(e)}", exc_info=True)
                st.error(f"❌ Generation failed: {str(e)}")
    
    def _handle_generation_result_with_tracking(self, updated_state, generation_duration: float):
        """Handle generation result with comprehensive tracking - FIXED: Immediate transition."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        try:
            # Convert state for session storage
            workflow_state = self._convert_state_to_workflow_state(updated_state)
            st.session_state.workflow_state = workflow_state
            
            # Check for success
            code_snippet = self._safe_get_state_value(updated_state, 'code_snippet')
            error = self._safe_get_state_value(updated_state, 'error')
            
            has_code_snippet = code_snippet is not None
            has_error = error is not None and error != ""
            
            if has_code_snippet:
                logger.debug("Code generation completed successfully")
                
                # FIXED: Set generation completed flag BEFORE showing messages
                st.session_state.generation_completed = True
                st.session_state.active_tab = 2  # Switch to Review tab
                
                # Update workflow step
                if hasattr(workflow_state, 'current_step'):
                    workflow_state.current_step = "review"
                
                # Show appropriate message
                if has_error:
                    st.warning(f"⚠️ {t('code_generated_with_warnings')}: {error}")
                    st.info(f"✅ {t('code_generation_completed_switching_to_review_tab...')}")
                else:
                    st.success(f"✅ {t('code_generated_successfully_switching_to_review_tab...')}")

                # FIXED: Use session state manager for safe transition
                # from utils.session_state_manager import session_state_manager
                # session_state_manager.handle_tab_transition_after_generation()
                
                # Small delay then rerun
                time.sleep(0.3)
                st.rerun()
                
            elif has_error:                              
                st.error(f"❌ {t('generation_failed')}: {error}")
                logger.error(f"{t('generation_failed')}: {error}")
                
            else:               
                st.error(f"❌ {t('generation_failed')}.")
                logger.warning("Code generation completed but no code snippet was created and no error message")
                
        except Exception as e:
            logger.error(f"{t('generation_failed')}: {str(e)}")
            st.error(f"❌ Error processing generation result: {str(e)}")
    