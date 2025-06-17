"""
State Schema for Java Code Review Training System.

This module defines the simplified state schema for the LangGraph-based workflow.
"""

__all__ = ['WorkflowState', 'CodeSnippet', 'ReviewAttempt']

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import time

# --- Code Snippet Data ---
class CodeSnippet(BaseModel):
    """Schema for code snippet data"""
    code: str = Field(description="The Java code snippet with annotations")
    clean_code: str = Field("", description="The Java code snippet without annotations")
    raw_errors: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Raw error data organized by type")
    expected_error_count: int = Field(0, description="Number of errors originally requested for code generation")

# --- Review Attempt Data ---
class ReviewAttempt(BaseModel):
    """Schema for a student review attempt"""
    student_review: str = Field(description="The student's review text")
    iteration_number: int = Field(description="Iteration number of this review")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis of the review")
    targeted_guidance: Optional[str] = Field(None, description="Targeted guidance for next iteration")

# --- Workflow State ---
class WorkflowState(BaseModel):
    """The simplified state for the Java Code Review workflow"""
    # Current workflow step
    current_step: Literal[
        "generate", "evaluate", "regenerate", "review", "analyze", "generate_comparison_report", "complete"
    ] = Field("generate", description="Current step in the workflow")

    # Code generation parameters
    code_length: str = Field("medium", description="Length of code (short, medium, long)")
    difficulty_level: str = Field("medium", description="Difficulty level (easy, medium, hard)")
    domain: Optional[str] = Field(None, description="Domain context for the generated code")
    error_count_start: int = Field(1, description="Minimum number of errors to generate")
    error_count_end: int = Field(2, description="Maximum number of errors to generate")

    # Error selection parameters
    selected_error_categories: Dict[str, List[str]] = Field(
        default_factory=lambda: {"java_errors": []},
        description="Selected error categories"
    )
    selected_specific_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Specifically selected errors (when using specific mode)"
    )

    # Code Generation State
    code_snippet: Optional[CodeSnippet] = Field(None, description="Generated code snippet data")
    original_error_count: int = Field(0, description="Original number of errors requested for generation")

    # Code Evaluation State
    evaluation_attempts: int = Field(0, description="Number of attempts to generate code")
    max_evaluation_attempts: int = Field(3, description="Maximum number of code generation attempts")
    evaluation_result: Optional[Dict[str, Any]] = Field(None, description="Results from code evaluation")
    code_generation_feedback: Optional[str] = Field(None, description="Feedback for code generation")

    # Review State
    pending_review: Optional[str] = Field(None, description="Student review waiting to be processed")
    current_iteration: int = Field(1, description="Current iteration number")
    max_iterations: int = Field(3, description="Maximum number of iterations")
    review_sufficient: bool = Field(False, description="Whether the review is sufficient")
    review_history: List[ReviewAttempt] = Field(default_factory=list, description="History of review attempts")

    # Final Output
    comparison_report: Optional[str] = Field(None, description="Comparison report")
    error: Optional[str] = Field(None, description="Error message if any")
    final_summary: Optional[str] = Field(None, description="Final summary of the workflow")

     # ADDED: Missing fields that were causing AttributeError
    workflow_completed: bool = Field(False, description="Whether the workflow has been marked as completed")
    code_generation_completed: bool = Field(False, description="Whether code generation phase is completed")
    review_phase_started: Optional[float] = Field(None, description="Timestamp when review phase started")
    code_generation_timestamp: Optional[float] = Field(None, description="Timestamp when code was generated")
    
    # ADDED: Additional tracking fields for robustness
    last_update_timestamp: float = Field(default_factory=time.time, description="Last time state was updated")
    session_id: Optional[str] = Field(None, description="Session identifier for debugging")
    debug_info: Dict[str, Any] = Field(default_factory=dict, description="Debug information")
    badge_awards: Optional[Dict[str, Any]] = Field(None, description="Newly awarded badges and points")
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True
        extra = "allow"  # Allow additional fields for flexibility