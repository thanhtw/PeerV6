import streamlit as st
import os
import logging
import time
from typing import Dict, List, Any, Optional
from data.database_error_repository import DatabaseErrorRepository
from utils.language_utils import t
from utils.code_utils import _get_category_icon, _get_difficulty_icon, add_line_numbers, _log_user_interaction_tutorial
from state_schema import WorkflowState
from ui.components.comparison_report_renderer import ComparisonReportRenderer
from analytics.behavior_tracker import behavior_tracker
from ui.components.user_practice_tracker import UserPracticeTracker

logger = logging.getLogger(__name__)

class TutorialUI:
    """UI component for exploring Java errors with examples and solutions - REVISED with Practice workflow phases."""
    
    def __init__(self, workflow=None):
        """Initialize the Tutorial UI."""
        self.repository = DatabaseErrorRepository()
        self.practice_tracker = UserPracticeTracker()
        self.workflow = workflow  # JavaCodeReviewGraph instance
        self.comparison_renderer = ComparisonReportRenderer()
        self.behavior_tracker = behavior_tracker
        
        # Session tracking variables
        self.current_session_id = None
        self.current_practice_session_id = None
        self.practice_start_time = None
        
        # Initialize session state
        self._initialize_session_state()
        self._load_styles()
    
    def _initialize_session_state(self):
        """Initialize session state variables."""
        if "selected_error_code" not in st.session_state:
            st.session_state.selected_error_code = None
        if "user_progress" not in st.session_state:
            st.session_state.user_progress = {}
        if "practice_mode_active" not in st.session_state:
            st.session_state.practice_mode_active = False
        if "tutorial_load_time" not in st.session_state:
            st.session_state.tutorial_load_time = time.time()
        if "tutorial_view_mode" not in st.session_state:
            st.session_state.tutorial_view_mode = "all"
        # ADDED: Tutorial workflow phase tracking
        if "tutorial_workflow_phase" not in st.session_state:
            st.session_state.tutorial_workflow_phase = "explore"
    
    def _load_styles(self):
        """Load CSS styles for the Tutorial UI with safe encoding handling."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_dir = os.path.join(current_dir, "..", "..", "static", "css", "error_explorer")
            from static.css_utils import load_css_safe
            result = load_css_safe(css_directory=css_dir)
            
            # Also load tutorial-specific CSS
            tutorial_css_path = os.path.join(css_dir, "tutorial.css")
            if os.path.exists(tutorial_css_path):
                result_tutorial = load_css_safe(css_file=tutorial_css_path)
                
        except Exception as e:
            logger.error(f"Error loading Tutorial CSS: {str(e)}")
            st.warning(t("css_loading_warning"))

    def render(self, workflow=None):
        """Render the complete tutorial interface with workflow phases."""
        # Only update workflow if one is provided, otherwise keep the existing one
        if workflow is not None:
            self.workflow = workflow
        
        # Check if we're in practice mode
        if st.session_state.get("practice_mode_active", False):
            self._render_practice_mode_with_phases()
        else:
            self._render_exploration_mode_compact()
    
    def _render_practice_mode_with_phases(self):
        """REVISED: Render practice mode using compact workflow phases like Practice tab."""
        practice_error = st.session_state.get("practice_error_data", {})   
        error_name = practice_error.get(t("error_name"), t("unknown_error"))        
        difficulty = practice_error.get(t("difficulty_level"), "medium")
        category = practice_error.get(t("category"), "")
        
        # Compact practice header (reduced size)
        self._render_compact_practice_header(error_name, difficulty, category)
        
        # Get tutorial workflow info (similar to practice workflow)
        tutorial_workflow_info = self._get_tutorial_workflow_info()
        current_phase = st.session_state.get('tutorial_workflow_phase', 'generate')
        
        # ADDED: Scroll to current phase functionality
        self._add_scroll_to_current_phase(current_phase)
        
        # Render compact phases using Practice UI patterns
        self._render_tutorial_compact_generation_phase(tutorial_workflow_info, current_phase)
        self._render_tutorial_compact_review_phase(tutorial_workflow_info, current_phase)
        self._render_tutorial_compact_feedback_phase(tutorial_workflow_info, current_phase)

    def _render_exploration_mode_compact(self):
        """REVISED: Render exploration mode with more compact, user-friendly design."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        # Compact header (reduced size)
        self._render_compact_header(user_id)       
        
        # Compact search and filter section
        self._render_compact_search_filters()
        
        # Compact main content area
        self._render_compact_error_content(user_id)

    def _render_compact_practice_header(self, error_name: str, difficulty: str, category: str):
        """REVISED: Compact practice header (reduced size)."""
        difficulty_config = {
            "easy": {"class": "difficulty-easy", "icon": "🟢"},
            "medium": {"class": "difficulty-medium", "icon": "🟡"},
            "hard": {"class": "difficulty-hard", "icon": "🔴"}
        }
        
        config = difficulty_config.get(difficulty, difficulty_config["medium"])
        category_icon = _get_category_icon(category.lower()) if category else "📚"
        
        st.markdown(f"""
        <div class="compact-practice-phase compact-phase-active">
            <div class="compact-phase-header">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <span class="compact-phase-icon">🎯</span>
                    <div>
                        <h3 class="compact-phase-title">{error_name}</h3>
                        <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
                            <span class="difficulty-badge {config['class']}">
                                {config['icon']} {t(difficulty)}
                            </span>
                            <span class="category-badge">
                                {category_icon} {category}
                            </span>
                        </div>
                    </div>
                </div>
                <span class="compact-phase-status compact-status-active">{t('active')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _render_compact_header(self, user_id: str):
        """REVISED: Compact header with reduced size and better responsiveness."""
        try:
            stats = self.repository.get_error_statistics()
            total_errors = stats.get('total_errors', 0)
            total_categories = stats.get('total_categories', 0)
            practice_stats = {}
            
            if user_id:
                practice_data = self.practice_tracker.get_user_practice_data(user_id)              
                practice_stats = practice_data.get(t('practice_stats'), {})
        except Exception as e:
            logger.debug(f"Could not get database statistics: {str(e)}")
            total_errors = 0
            total_categories = 0
            practice_stats = {}           
        
        st.markdown(f"""
        <div class="compact-practice-phase">
            <div class="compact-phase-header">
                <div>
                    <h2 class="compact-phase-title">🔍 {t('error_explorer')}</h2>
                    <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">{t('explore_comprehensive_error_library')}</p>
                </div>
                <div class="compact-metrics">
                    <div class="compact-metric">
                        <div class="compact-metric-value">{total_errors}</div>
                        <div class="compact-metric-label">{t('errors')}</div>
                    </div>
                    <div class="compact-metric">
                        <div class="compact-metric-value">{total_categories}</div>
                        <div class="compact-metric-label">{t('categories')}</div>
                    </div>
                    <div class="compact-metric" style="background: rgba(40, 167, 69, 0.1);">
                        <div class="compact-metric-value" style="color: #28a745;">{practice_stats.get('total_practiced', 0)}</div>
                        <div class="compact-metric-label">{t('practiced')}</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _render_compact_search_filters(self):
        """REVISED: More compact search and filter controls."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        
        
        # More compact filter controls
        col1, col2, col3 = st.columns([3, 2, 2])
        
        with col1:
            search_term = st.text_input(
                "",
                placeholder=f"🔍 {t('search_errors_placeholder')}",
                key="error_search_compact",
                help=t('search_help_text')
            )
        
        with col2:
            categories = self._get_categories()
            selected_category = st.selectbox(
                f"📂 {t('category')}",
                options=[t('all_categories')] + categories,
                key="category_filter_compact"
            )
    
        with col3:
            if user_id:
                practice_filters = [t('all_errors'), t('practiced_errors'), t('unpracticed_errors'), 
                                  t('completed_errors'), t('mastered_errors')]
                selected_practice = st.selectbox(
                    f"🎯 {t('practice_status')}",
                    options=practice_filters,
                    key="practice_filter_compact"
                )
            else:
                selected_practice = t('all_errors')
        
       
        # Store filter values
        st.session_state.search_term = search_term
        st.session_state.selected_category = selected_category
        st.session_state.selected_practice = selected_practice

    def _render_compact_error_content(self, user_id: str):
        """REVISED: Compact error content with smaller cards."""
        practice_data = {}
        if user_id:
            practice_data = self.practice_tracker.get_user_practice_data(user_id)
       
        filtered_errors = self._get_filtered_errors(practice_data)        
        if not filtered_errors:
            self._render_compact_no_results()
            return
        
        # Render errors with compact design
        self._render_compact_error_sections_grouped(filtered_errors, practice_data)

    def _render_compact_error_sections_grouped(self, filtered_errors: List[Dict[str, Any]], 
                                         practice_data: Dict[str, Any]):
        """REVISED: Compact error sections with smaller category headers."""
        errors_by_category = self._group_errors_by_category(filtered_errors)        
        all_categories = self._get_categories()
        
        for category_name in all_categories:
            if category_name not in errors_by_category:
                continue
                
            errors = errors_by_category[category_name]
            if not errors:
                continue
            
            # Compact category header
            practiced_count = len([e for e in errors if e.get(t('practice_stats'))])
            completed_count = len([e for e in errors if e.get(t('practice_stats')) and 
                                e[t('practice_stats')].get(t('completion_status')) in ['completed', 'mastered']])
            total_count = len(errors)
            completion_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
            
            st.markdown(f"""
            <div class="compact-practice-phase compact-phase-upcoming">
                <div class="compact-phase-header">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span class="compact-phase-icon">{_get_category_icon(category_name.lower())}</span>
                        <h4 class="compact-phase-title">{category_name}</h4>
                    </div>
                    <div class="compact-metrics">
                        <div class="compact-metric">
                            <div class="compact-metric-value">{total_count}</div>
                            <div class="compact-metric-label">{t('total')}</div>
                        </div>
                        <div class="compact-metric">
                            <div class="compact-metric-value">{practiced_count}</div>
                            <div class="compact-metric-label">{t('practiced')}</div>
                        </div>
                        <div class="compact-metric">
                            <div class="compact-metric-value">{completion_percentage:.0f}%</div>
                            <div class="compact-metric-label">{t('completed')}</div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Render compact error cards
            for error in errors:
                self._render_compact_error_card(error)

    def _render_compact_error_card(self, error: Dict[str, Any]):
        """REVISED: More compact error cards with smaller design."""
        error_name = error.get(t("error_name"), t("unknown_error"))        
        difficulty = error.get(t('difficulty_level'), 'medium')
        practice_stats = error.get(t('practice_stats'))       
        
        # Get full error details if not provided
        if not error.get(t("description")):
            category = error.get(t('category'), '')
            full_error_data = None
            if category:
                category_errors = self.repository.get_category_errors(category)
                full_error_data = next((e for e in category_errors 
                                      if e.get(t("error_name")) == error_name), None)
            if full_error_data:
                error.update(full_error_data)
        
        # Compact practice status indicators
        practice_indicator = ""
        if practice_stats:
            status = practice_stats.get(t('completion_status'), 'not_started')
            accuracy = practice_stats.get(t('best_accuracy'), 0)
            practice_count = practice_stats.get(t('practice_count'), 0)
            
            if status == 'mastered':
                practice_indicator = f"🏆 {accuracy:.0f}%"
            elif status == 'completed':
                practice_indicator = f"✅ {accuracy:.0f}%"
            elif status == 'in_progress':
                practice_indicator = f"🔄 {practice_count}x"
            else:
                practice_indicator = f"📝 {practice_count}x"
        else:
            practice_indicator = "🆕"
        
        # Compact expander
        expander_title = f"{_get_difficulty_icon(difficulty.title())} **{error_name}** | {practice_indicator}"
        
        with st.expander(expander_title, expanded=False):
            
            description = error.get(t("description"), "")
            implementation_guide = error.get(t("implementation_guide"), "")
                
            if description:
                st.markdown(f"""
                    <div class="error-detail-card">
                        <strong>📋 {t('what_is_this_error')}:</strong><br>
                        {description}
                    </div>
                    """, unsafe_allow_html=True)
                
            if implementation_guide:
                st.markdown(f"""
                    <div class="error-detail-card" style="background: #e8f5e8; border-left-color: #4caf50;">
                        <strong>💡 {t('how_to_fix')}:</strong><br>
                        {implementation_guide}
                    </div>
                    """, unsafe_allow_html=True)
                
            # Compact code examples
            examples = self.repository.get_error_examples(error_name)
            if examples.get("wrong_examples") or examples.get("correct_examples"):
                if examples.get("wrong_examples") and examples.get("correct_examples"):
                        # Side by side for compact view
                    example_col1, example_col2 = st.columns(2)
                    with example_col1:
                        st.markdown("**❌ Problem:**")
                        st.code(examples["wrong_examples"][0][:200] + "..." if len(examples["wrong_examples"][0]) > 200 else examples["wrong_examples"][0], language="java")
                    with example_col2:
                        st.markdown("**✅ Solution:**")
                        st.code(examples["correct_examples"][0][:200] + "..." if len(examples["correct_examples"][0]) > 200 else examples["correct_examples"][0], language="java")
            
            self._render_compact_practice_button(error, practice_stats)

    def _render_compact_practice_button(self, error: Dict[str, Any], practice_stats: Optional[Dict[str, Any]]):
        """REVISED: Compact practice button."""
        error_name = error.get(t("error_name"), t("unknown_error"))
        error_code = error.get(t('error_code'), f"error_{hash(error_name) % 10000}")
        
        if practice_stats:
            status = practice_stats.get(t('completion_status'), 'not_started')
            if status == 'mastered':
                button_text = f"🏆 {t('master_again')}"
                button_type = "secondary"
            elif status == 'completed':
                button_text = f"🔄 {t('retry')}"
                button_type = "secondary"
            else:
                button_text = f"🚀 {t('continue')}"
                button_type = "primary"
        else:
            button_text = f"🚀 {t('start')}"
            button_type = "primary"
        
        practice_key = f"practice_compact_{error_code}_{hash(error_name) % 1000}"
        
        if st.button(
            button_text,
            key=practice_key,
            use_container_width=True,
            type=button_type,
            help=t('generate_practice_code_with_error_type')
        ):
            self._start_practice_session(error, practice_stats)

    def _render_compact_no_results(self):
        """REVISED: Compact no results message."""
        st.markdown(f"""
        <div class="compact-practice-phase no-results-container">
            <div class="no-results-icon">🔍</div>
            <h4 class="no-results-title">{t('no_errors_found')}</h4>
            <p class="no-results-message">{t('no_errors_found_message')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ADDED: Tutorial workflow phase management functions
    def _get_tutorial_workflow_info(self) -> Dict:
        """Get tutorial workflow information similar to practice workflow."""
        default_state = {
            "current_phase": "generate",
            "has_code": False,
            "review_complete": False,
            "workflow_status": "setup"
        }
        
        workflow_status = st.session_state.get("practice_workflow_status", "setup")
        has_code = st.session_state.get("practice_code_generated", False)
        
        return {
            "current_phase": st.session_state.get('tutorial_workflow_phase', 'generate'),
            "has_code": has_code,
            "review_complete": workflow_status == "review_complete",
            "workflow_status": workflow_status
        }

    def _render_tutorial_compact_generation_phase(self, workflow_info, current_phase):
        """REVISED: Tutorial generation phase using compact design like Practice."""
        workflow_status = workflow_info["workflow_status"]
        has_code = workflow_info["has_code"]
        
        if workflow_status == "setup" and current_phase == "generate":
            phase_class = "compact-phase-active"
            status_class = "compact-status-active"
            status_text = t("active")
        elif has_code:
            phase_class = "compact-phase-completed"
            status_class = "compact-status-completed"
            status_text = t("completed")
        else:
            phase_class = "compact-phase-upcoming"
            status_class = "compact-status-upcoming"
            status_text = t("pending")
        
        st.markdown(f"""
        <div class="compact-practice-phase {phase_class}" id="tutorial-generation-phase">
            <div class="compact-phase-header">
                <span class="compact-phase-icon">🔧</span>
                <span class="compact-phase-title">{t('phase_1_generate_code')}</span>
                <span class="compact-phase-status {status_class}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if workflow_status == "setup" and not has_code:
            self._render_tutorial_setup_content()

    def _render_tutorial_compact_review_phase(self, workflow_info, current_phase):
        """REVISED: Tutorial review phase using compact design."""
        has_code = workflow_info["has_code"]
        review_complete = workflow_info["review_complete"]
        
        if has_code and not review_complete:
            phase_class = "compact-phase-active"
            status_class = "compact-status-active"
            status_text = t("active")
        elif review_complete:
            phase_class = "compact-phase-completed"
            status_class = "compact-status-completed"
            status_text = t("completed")
        else:
            phase_class = "compact-phase-upcoming"
            status_class = "compact-status-upcoming"
            status_text = t("pending")
        
        st.markdown(f"""
        <div class="compact-practice-phase {phase_class}" id="tutorial-review-phase">
            <div class="compact-phase-header">
                <span class="compact-phase-icon">📋</span>
                <span class="compact-phase-title">{t('phase_2_review_code')}</span>
                <span class="compact-phase-status {status_class}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if has_code and not review_complete:
            self._render_tutorial_review_content()

    def _render_tutorial_compact_feedback_phase(self, workflow_info, current_phase):
        """REVISED: Tutorial feedback phase using compact design."""
        review_complete = workflow_info["review_complete"]
        
        if review_complete:
            phase_class = "compact-phase-active"
            status_class = "compact-status-active"
            status_text = t("active")
        else:
            phase_class = "compact-phase-upcoming"
            status_class = "compact-status-upcoming"
            status_text = t("pending")
        
        st.markdown(f"""
        <div class="compact-practice-phase {phase_class}" id="tutorial-feedback-phase">
            <div class="compact-phase-header">
                <span class="compact-phase-icon">📊</span>
                <span class="compact-phase-title">{t('phase_3_feedback')}</span>
                <span class="compact-phase-status {status_class}">{status_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if review_complete:
            self._render_tutorial_feedback_content()

    def _add_scroll_to_current_phase(self, current_phase: str):
        """ADDED: Scroll to current phase functionality like Practice tab."""
        phase_mappings = {
            'generate': 'tutorial-generation-phase',
            'review': 'tutorial-review-phase', 
            'feedback': 'tutorial-feedback-phase'
        }
        
        target_id = phase_mappings.get(current_phase, 'tutorial-generation-phase')
        
        st.markdown(f"""
        <script>
        function scrollToTutorialPhase() {{
            const targetElement = document.getElementById('{target_id}');
            if (targetElement) {{
                targetElement.style.boxShadow = '0 0 20px rgba(76, 104, 215, 0.3)';
                targetElement.style.transform = 'scale(1.02)';
                
                const yOffset = -20;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset + yOffset;
                
                window.scrollTo({{
                    top: offsetPosition,
                    behavior: 'smooth'
                }});
                
                setTimeout(() => {{
                    targetElement.style.boxShadow = '';
                    targetElement.style.transform = '';
                }}, 2000);
            }}
        }}
        
        setTimeout(scrollToTutorialPhase, 300);
        </script>
        """, unsafe_allow_html=True)

    # Keep existing methods but make them more compact
    def _render_tutorial_setup_content(self):
        """Compact tutorial setup content."""
        practice_error = st.session_state.get("practice_error_data", {})
        
        # Compact error details
        st.markdown('<div class="compact-content">', unsafe_allow_html=True)
        self._render_error_details_compact(practice_error)
        
        # Auto-generate code
        if not self.workflow:
            st.error(f"❌ {t('practice_mode_requires_workflow_refresh')}")
            return
        
        if "practice_code_generated" not in st.session_state:
            self._generate_practice_code_with_tracking(practice_error)
        
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_error_details_compact(self, practice_error):
        """REVISED: Compact error details."""
        description = practice_error.get(t('description'), t('no_description_available'))
        implementation_guide = practice_error.get('implementation_guide', '')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if description:
                st.markdown(f"""
                <div class="what-youll-learn">
                    <strong>📝 {t('what_youll_learn')}:</strong><br>
                    {description}
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            difficulty = practice_error.get('difficulty_level', 'medium')
            st.markdown(f"""
            <div class="error-description-card">
                <div><strong>{t('difficulty')}:</strong> {t(difficulty)}</div>
                <div style="margin-top: 0.5rem;"><strong>{t('focus')}:</strong> {t('single_error_type')}</div>
            </div>
            """, unsafe_allow_html=True)

    def _render_tutorial_review_content(self):
        """Compact tutorial review content."""
        workflow_state = st.session_state.get("practice_workflow_state")
        
        if not workflow_state or not hasattr(workflow_state, 'code_snippet'):
            st.error(t('no_practice_session_data'))
            return
        
        st.markdown('<div class="compact-content">', unsafe_allow_html=True)
        
        # Compact code display
        code_to_display = workflow_state.code_snippet.clean_code
        
        st.markdown(f"""
        <div class="code-header">
            <span class="code-filename">📄 PracticeChallenge.java</span>
            <span class="code-language">☕ Java</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.code(add_line_numbers(code_to_display), language="java")
        
        # Compact review input
        self._render_tutorial_review_input_compact(workflow_state)
        
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_tutorial_review_input_compact(self, workflow_state):
        """REVISED: Compact review input."""
        current_iteration = getattr(workflow_state, 'current_iteration', 1)
        max_iterations = getattr(workflow_state, 'max_iterations', 3)
        
        st.markdown(f"""
        <div class="review-input-header">
            <strong>✍️ {t('submit_your_analysis')} ({t('attempt')} {current_iteration}/{max_iterations})</strong>
        </div>
        """, unsafe_allow_html=True)
        
        review_key = f"tutorial_review_{current_iteration}"
        student_review = st.text_area(
            "",
            height=200,
            key=review_key,
            placeholder=f"🔍 {t('example_review_format_line')}",
            label_visibility="collapsed"
        )
        
        col1, col2, col3 = st.columns([6, 6, 4])
        
        with col1:
            if st.button(f"🚀 {t('submit_review_button')}", key="submit_tutorial_review", type="primary"):
                if student_review and student_review.strip():
                    self._process_practice_review_with_tracking(student_review.strip())
                    # Update phase after submission
                    st.session_state.tutorial_workflow_phase = "review"
                else:
                    st.warning(f"⚠️ {t('please_enter_review')}")
        
        with col2:
            if st.button(f"🔄 {t('generate_new_challenge')}", key="regenerate_tutorial"):
                self._regenerate_practice_code()
        
        with col3:
            if st.button(f"🏠 {t('exit')}", key="exit_tutorial"):
                self._exit_practice_mode_with_tracking()

    def _render_tutorial_feedback_content(self):
        """Compact tutorial feedback content."""
        workflow_state = st.session_state.get("practice_workflow_state")
        
        if not workflow_state:
            st.error(t('no_practice_session_data'))
            return
        
        st.markdown('<div class="compact-content">', unsafe_allow_html=True)
        
        # Compact feedback header
        st.markdown(f"""
        <div class="feedback-complete-header">
            <h3 class="feedback-complete-title">🎉 {t('practice_session_complete')}</h3>
            <p class="feedback-complete-subtitle">{t('excellent_work_analysis_complete')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Compact results
        self._render_compact_results_dashboard(workflow_state)
        self._render_compact_action_panel()
        
        st.markdown('</div>', unsafe_allow_html=True)

    def _render_compact_results_dashboard(self, workflow_state):
        """REVISED: Compact results dashboard."""
        review_history = getattr(workflow_state, 'review_history', [])
        
        if review_history:
            comparison_report = getattr(workflow_state, 'comparison_report', None)
            if comparison_report:               
                self.comparison_renderer.render_comparison_report(comparison_report)

    def _render_compact_action_panel(self):
        """REVISED: Compact action panel."""
        col1, col2, col3 = st.columns([4,4,2])
        
        with col1:
            if st.button(f"🔄 {t('try_another_challenge')}", key="restart_tutorial", type="primary"):
                self._restart_practice_session()
        
        with col2:
            if st.button(f"🎲 {t('generate_new_challenge')}", key="new_tutorial"):
                self._regenerate_practice_code()
        
        with col3:
            if st.button(f"🏠 {t('back_to_explorer')}", key="exit_to_explorer"):
                self._exit_practice_mode_with_tracking()

    # Keep all existing methods from the original code...
    # (All the other methods remain the same, just the rendering methods above are revised)
    
    def _get_categories(self) -> List[str]:
        """Get all available categories."""
        try:
            categories_data = self.repository.get_all_categories()
            return categories_data.get("java_errors", [])
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []

    def _group_errors_by_category(self, errors: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group errors by category."""
        grouped = {}
        for error in errors:
            category = error.get(t('category'), 'Unknown')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(error)
        return grouped

    def _get_filtered_errors(self, practice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get errors filtered by search, category, difficulty, and practice status."""
        try:
            selected_practice = st.session_state.get('selected_practice', t('all_errors'))
            
            if selected_practice == t('practiced_errors'):
                errors = practice_data.get(t('practiced_errors'), [])
                formatted_errors = []
                for error in errors:
                    formatted_errors.append({
                        t('error_code'): error[t('error_code')],
                        t("error_name"): error[t('error_name')],
                        t('difficulty_level'): error[t('difficulty_level')],
                        t('category'): error[t('category')],
                        t('practice_stats'): error
                    })
                return self._apply_standard_filters(formatted_errors)
                
            elif selected_practice == t('unpracticed_errors'):
                errors = practice_data.get(t('unpracticed_errors'), [])
                formatted_errors = []
                for error in errors:
                    formatted_errors.append({
                        t('error_code'): error['error_code'],
                        t("error_name"): error['error_name'],
                        t('description'): error.get('description'),  
                        t('difficulty_level'): error['difficulty_level'],
                        t('category'): error['category_name'],
                        t('practice_stats'): None
                    })
                return self._apply_standard_filters(formatted_errors)
                
            elif selected_practice == t('completed_errors'):
                errors = [e for e in practice_data.get(t('practiced_errors'), []) 
                        if e[t('completion_status')] in ['completed', 'mastered']]
                formatted_errors = []
                for error in errors:
                    formatted_errors.append({
                        t('error_code'): error[t('error_code')],
                        t("error_name"): error[t('error_name')],
                        t('difficulty_level'): error[t('difficulty_level')],
                        t('category'): error[t('category')],
                        t('practice_stats'): error
                    })
                return self._apply_standard_filters(formatted_errors)
                
            elif selected_practice == t('mastered_errors'):
                errors = [e for e in practice_data.get(t('practiced_errors'), []) 
                        if e[t('completion_status')] == 'mastered']
                formatted_errors = []
                for error in errors:
                    formatted_errors.append({
                        t('error_code'): error[t('error_code')],
                        t("error_name"): error[t('error_name')],
                        t('difficulty_level'): error[t('difficulty_level')],
                        t('category'): error[t('category')],
                        t('practice_stats'): error
                    })
                return self._apply_standard_filters(formatted_errors)
            
            else:
                return self._get_all_errors_with_practice_data(practice_data)
                
        except Exception as e:
            logger.error(f"Error getting filtered errors: {str(e)}")
            return []

    def _get_all_errors_with_practice_data(self, practice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all errors with practice data merged, grouped by category and ordered by difficulty."""
        try:
            selected_category = st.session_state.get('selected_category', t('all_categories'))
            
            if selected_category == t('all_categories'):
                categories = self._get_categories()
            else:
                categories = [selected_category]
            
            practiced_errors_lookup = {}
            for practiced_error in practice_data.get(t('practiced_errors'), []):
                error_code = practiced_error.get(t('error_code'))
                error_name = practiced_error.get(t('error_name'))              

                if error_code:
                    practiced_errors_lookup[error_code] = practiced_error
                if error_name:
                    practiced_errors_lookup[error_name] = practiced_error
            
            all_errors = []
            for category in categories:
                category_errors = self.repository.get_category_errors(category)
                
                category_errors_with_practice = []
                for error in category_errors:
                    error_name = error.get(t("error_name"), "")
                    error_code = error.get(t('error_code'), '')
                    
                    practice_stats = None
                    if error_code and error_name in practiced_errors_lookup:
                        practice_stats = practiced_errors_lookup[error_name]

                    enhanced_error = {
                        t('error_code'): error_code or f"gen_{hash(error_name) % 10000}",
                        t("error_name"): error_name,
                        t("description"): error.get(t("description"), ""),
                        t("implementation_guide"): error.get(t("implementation_guide"), ""),
                        t('difficulty_level'): error.get(t('difficulty_level'), 'medium'),
                        t('category'): category,
                        t('practice_stats'): practice_stats
                    }
                    
                    category_errors_with_practice.append(enhanced_error)
                
                category_errors_sorted = self._sort_errors_by_difficulty(category_errors_with_practice)
                all_errors.extend(category_errors_sorted)
            
            return self._apply_standard_filters(all_errors)
            
        except Exception as e:
            logger.error(f"Error getting all errors with practice data: {str(e)}")
            return []

    def _apply_standard_filters(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply search and difficulty filters to errors."""
        filtered = errors
        
        search_term = st.session_state.get('search_term', '').lower()
        if search_term:
            filtered = [
                error for error in filtered
                if search_term in error.get(t("error_name"), "").lower() or
                search_term in error.get(t("description"), "").lower() or
                search_term in error.get(t("implementation_guide"), "").lower()
            ]
        return  self._sort_errors_by_difficulty(filtered)
       

    def _sort_errors_by_difficulty(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort errors by difficulty level (easy -> medium -> hard)."""
        difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
        
        def get_difficulty_sort_key(error):
            difficulty = error.get(t('difficulty_level'), 'medium')
            return difficulty_order.get(difficulty, 2)
        
        return sorted(errors, key=get_difficulty_sort_key)

    def _start_practice_session(self, error: Dict[str, Any], practice_stats: Optional[Dict[str, Any]]):
        """Enhanced practice session start with comprehensive tracking."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        error_name = error.get(t("error_name"), t("unknown_error"))

        try:
            if user_id:
                self.practice_tracker.start_practice_session(user_id, error)
                
            logger.debug(f"Starting practice session for error: {error_name}")
            st.session_state.practice_mode_active = True
            st.session_state.practice_error_data = error
            st.session_state.practice_workflow_status = "setup"
            st.session_state.tutorial_workflow_phase = "generate"  # ADDED: Set tutorial phase
            
            st.success(t('starting_practice_session_with').format(error_name=error_name))
            
            if practice_stats:
                previous_attempts = practice_stats.get(t('practice_count'), 0)
                #st.success(f"🔄 {t('continuing_practice_with')} {error_name} ({previous_attempts} {t('previous_attempts')})")
            else:
                st.success(f"🆕 {t('starting_first_practice_with')} {error_name}")
            
            #st.info(f"✨ {t('practice_mode_activated_interface_reload')}")
            time.sleep(0.5)
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error starting practice session: {str(e)}", exc_info=True)            
            st.error(f"❌ {t('error_setting_up_practice_session')}: {str(e)}")

    def _generate_practice_code_with_tracking(self, practice_error):
        """Enhanced code generation with step-by-step tracking."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        if not self.workflow:
            logger.error("No workflow available for practice mode")
            st.error(f"❌ {t('practice_mode_requires_workflow_refresh')}")
            return
        
        try:
            generation_start_time = time.time()     
            
            with st.status(f"🚀 {t('generating_practice_challenge')}", expanded=True) as status:
                workflow_state = self._prepare_practice_workflow_state(practice_error)
                
                if not workflow_state:
                    st.error(f"❌ {t('failed_prepare_practice_session')}")
                    return
                
                logger.debug(f"Executing code generation with workflow: {type(self.workflow)}")
                updated_state = self.workflow.execute_code_generation(workflow_state)
                
                generation_duration = time.time() - generation_start_time
                
                if hasattr(updated_state, 'error') and updated_state.error:
                    error_msg = updated_state.error    
                    st.error(f"❌ {t('failed_to_generate_practice_code')}: {error_msg}")
                    return
                
                if not hasattr(updated_state, 'code_snippet') or not updated_state.code_snippet:
                    st.error(f"❌ {t('failed_to_generate_practice_code')}: No code generated")
                    return
                
                if user_id:
                    code_snippet = updated_state.code_snippet
                    code_stats = {
                        "lines_of_code": len(code_snippet.code.split('\n')) if hasattr(code_snippet, 'code') else 0,
                        "code_length_chars": len(code_snippet.code) if hasattr(code_snippet, 'code') else 0,
                        "has_clean_code": hasattr(code_snippet, 'clean_code') and bool(code_snippet.clean_code),
                        "expected_errors": getattr(code_snippet, 'expected_error_count', 0)
                    }

                    _log_user_interaction_tutorial(
                        user_id=user_id,
                        interaction_category="tutorial",
                        interaction_type="code_generate_complete",                       
                        success=True,                       
                        details= {
                            "generation_successful": True,
                            "generation_duration": generation_duration,
                            "generation_attempts": getattr(updated_state, 'evaluation_attempts', 1),
                            "code_stats": code_stats,
                            "workflow_step": getattr(updated_state, 'current_step', 'unknown')
                        },
                        time_spent_seconds=int(generation_duration)
                    )
            
            st.session_state.practice_workflow_state = updated_state
            st.session_state.practice_code_generated = True
            st.session_state.practice_workflow_status = "code_ready"
            st.session_state.tutorial_workflow_phase = "review"  # ADDED: Auto-advance phase
            
            if user_id:               
                _log_user_interaction_tutorial(
                    user_id=user_id,
                    interaction_category="tutorial",
                    interaction_type="code_ready_for_review",                    
                    success=True,                   
                    details= {
                        "code_ready": True,
                        "total_generation_time": generation_duration
                    },
                    time_spent_seconds=int(generation_duration)
                )
            
            st.success(f"✅ {t('practice_challenge_ready')}!")
            
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error generating practice code: {str(e)}", exc_info=True)
            st.error(f"❌ {t('error_setting_up_practice_session')}: {str(e)}")

    def _prepare_practice_workflow_state(self, error: Dict[str, Any]) -> Optional[WorkflowState]:
        """Prepare a WorkflowState specifically for practice sessions with a single error."""
        try:
            error_name = error.get(t("error_name"), t("unknown_error"))
            difficulty_level = error.get(t('difficulty_level'), 'medium')
            category = error.get(t('category'), 'Other')
            
            logger.debug(f"Preparing practice state for error: {error_name}, difficulty: {difficulty_level}")
            
            state = WorkflowState()
            
            state.code_length = "medium"
            state.difficulty_level = difficulty_level
            state.error_count_start = 1
            state.error_count_end = 1
            
            domain_mapping = {
                "logical errors": "calculation",
                "logical_errors": "calculation", 
                "syntax errors": "user_management",
                "syntax_errors": "user_management",
                "code quality": "file_processing",
                "code_quality": "file_processing",
                "standard violation": "data_validation",
                "standard_violation": "data_validation",
                "java specific": "banking",
                "java_specific": "banking"
            }
            state.domain = domain_mapping.get(category.lower(), "student_management")
            
            state.selected_error_categories = {"java_errors": []}
            state.selected_specific_errors = [error]
            
            state.current_step = "generate"
            state.max_evaluation_attempts = 3
            state.max_iterations = 3
            
            state.evaluation_attempts = 0
            state.current_iteration = 1
            state.review_sufficient = False
            state.review_history = []
            state.evaluation_result = None
            state.code_snippet = None
            state.comparison_report = None
            state.error = None
            
            logger.debug(f"Practice state prepared successfully for {error_name}")
            return state
            
        except Exception as e:
            logger.error(f"Error preparing practice workflow state: {str(e)}")
            return None

    def _process_practice_review_with_tracking(self, student_review):
        """Process the submitted practice review with step-by-step tracking."""
        try:
            user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
            workflow_state = st.session_state.practice_workflow_state
            practice_error = st.session_state.get("practice_error_data", {})
            error_code = practice_error.get(t('error_code'), '')

            if user_id:                         
                _log_user_interaction_tutorial(
                    user_id=user_id,
                    interaction_category="tutorial",
                    interaction_type="submit_review",
                    success=True,                    
                    details= {
                        "review_length": len(student_review),
                        "review_iteration": getattr(workflow_state, 'current_iteration', 1),
                        "word_count": len(student_review.split())
                    },
                    time_spent_seconds=0
                )

            with st.spinner(f"🔄 {t('analyzing_your_review')}"):
                start_time = time.time()
                updated_state = self.workflow.submit_review(workflow_state, student_review)
                st.session_state.practice_workflow_state = updated_state
                
                review_sufficient = getattr(updated_state, 'review_sufficient', False)
                current_iteration = getattr(updated_state, 'current_iteration', 1)
                max_iterations = getattr(updated_state, 'max_iterations', 3)
                
                latest_review = updated_state.review_history[-1] if updated_state.review_history else None
                analysis = latest_review.analysis if latest_review else {}
                identified_count = analysis.get(t('identified_count'), 0)
                total_problems = analysis.get(t('total_problems'), 0)
                accuracy = (identified_count / total_problems * 100) if total_problems > 0 else 0     
                time_spent_seconds = time.time() - start_time          
                
                if review_sufficient or current_iteration > max_iterations:
                    if user_id and error_code:
                        session_data = {
                            t('accuracy'): accuracy,
                            t('time_spent_seconds'): time_spent_seconds,
                            t('successful_completion'): review_sufficient and identified_count == total_problems
                        }
                        
                        self.practice_tracker.complete_practice_session(user_id, error_code, session_data)
                        self._update_badge_progress(user_id, practice_error, session_data)
                    
                    st.session_state.practice_workflow_status = "review_complete"
                    st.session_state.tutorial_workflow_phase = "feedback"  # ADDED: Auto-advance to feedback
                    st.success(f"✅ {t('review_analysis_complete')}")
                    
                    if user_id:                       
                        passed = review_sufficient and identified_count == total_problems                        
                        practice_error = st.session_state.get("practice_error_data", {})                        
                        _log_user_interaction_tutorial(
                            user_id=user_id,
                            interaction_category="tutorial",
                            interaction_type="review_analysis_complete",                            
                            success=True,                           
                            details={
                                "accuracy": accuracy,
                                "identified_count": identified_count,
                                "total_problems": total_problems,
                                "iterations_used": current_iteration,
                                "review_sufficient": review_sufficient,
                                "identified_correctly": identified_count == total_problems,
                                "error_code": practice_error.get('error_code', ''),
                                "final_review_text": student_review,
                                "review_iterations": current_iteration,
                                "analysis_data": analysis,
                                "passed": passed
                            },
                            time_spent_seconds=0
                        )
                else:                    
                    st.info(f"📝 {t('review_submitted_try_improve')}")
                
                time.sleep(1)
                st.rerun()
                
        except Exception as e:
            logger.error(f"Error processing practice review: {str(e)}")            
            st.error(f"❌ {t('error_processing_review')}: {str(e)}")

    def _update_badge_progress(self, user_id: str, practice_error: Dict[str, Any], session_data: Dict[str, Any]):
        """Update badge progress after practice session completion."""
        try:
            from analytics.badge_manager import BadgeManager
            badge_manager = BadgeManager()
            
            review_data = {
                'accuracy_percentage': session_data.get('accuracy', 0),
                'identified_count': 1 if session_data.get('successful_completion') else 0,
                'total_problems': 1,
                'time_spent_seconds': session_data.get('time_spent_seconds', 0),
                'session_type': 'practice',
                'practice_error_code': practice_error.get('error_code', ''),
                'code_difficulty': practice_error.get('difficulty_level', 'medium'),
                'review_iterations': 1,
                'categories_encountered': [practice_error.get('category', '')]
            }
            
            result = badge_manager.process_review_completion(user_id, review_data)
            
            if result.get('success') and result.get('awarded_badges'):
                st.session_state.practice_badge_awards = {
                    'badges': result.get('awarded_badges', []),
                    'points': result.get('points_awarded', 0)
                }
                logger.info(f"Badge progress updated: {len(result.get('awarded_badges', []))} badges awarded")
            
        except Exception as e:
            logger.error(f"Error updating badge progress: {str(e)}")

    def _exit_practice_mode_with_tracking(self):
        """Exit practice mode with proper tracking."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        if user_id and self.current_practice_session_id:
            _log_user_interaction_tutorial(
                user_id=user_id,
                interaction_category="tutorial",
                interaction_type="complete_tutorial_abandoned",                
                success=True,                
                details= {
                    "abandoned": True,
                    "exit_reason": "user_requested",
                    "practice_error": st.session_state.get("practice_error_data", {}),
                    "workflow_status": st.session_state.get("practice_workflow_status", "unknown")
                },
                time_spent_seconds=0
            )
        
        practice_keys = [key for key in st.session_state.keys() if key.startswith("practice_")]
        for key in practice_keys:
            del st.session_state[key]
        
        st.session_state.practice_mode_active = False
        st.session_state.tutorial_workflow_phase = "explore"  # ADDED: Reset to explore phase
        st.rerun()

    def _restart_practice_session(self):
        """Restart the practice session with the same error."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        if user_id:
            _log_user_interaction_tutorial(
                    user_id=user_id,
                    interaction_category="tutorial",
                    interaction_type="restart_tutorial_session",                  
                    success=True,                   
                    details=None,
                    time_spent_seconds=0
                )
        keys_to_clear = [
            "practice_code_generated",
            "practice_workflow_state", 
            "practice_workflow_status"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.practice_workflow_status = "setup"
        st.session_state.tutorial_workflow_phase = "generate"  # ADDED: Reset to generate phase
        st.rerun()

    def _regenerate_practice_code(self):
        """Regenerate practice code with the same error."""
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        if user_id:
            _log_user_interaction_tutorial(
                user_id=user_id,
                interaction_category="tutorial",
                interaction_type="regenerate_tutorial_code",               
                success=True,                
                details=None,
                time_spent_seconds=0
            )

        if "practice_code_generated" in st.session_state:
            del st.session_state["practice_code_generated"]
        if "practice_workflow_state" in st.session_state:
            del st.session_state["practice_workflow_state"]
        
        st.session_state.practice_workflow_status = "setup"
        st.session_state.tutorial_workflow_phase = "generate"  # ADDED: Reset to generate phase
        st.rerun()