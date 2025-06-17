"""
FIXED: Schema-compliant Workflow Builder for Java Peer Review Training System.

This module provides the GraphBuilder class with dynamic entry points to prevent
unnecessary code regeneration during review phase.
FIXED: Separate entry points for code generation and review phases.
"""

import logging
from langgraph.graph import StateGraph, END

from state_schema import WorkflowState
from workflow.node import WorkflowNodes
from workflow.conditions import WorkflowConditions
from utils.language_utils import t

# Configure logging
logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    FIXED: Builder for the Java Code Review workflow graph with dynamic entry points.
    
    This class builds separate workflows for code generation and review phases
    to prevent unnecessary code regeneration during review submissions.
    """
    
    def __init__(self, workflow_nodes: WorkflowNodes):
        """
        Initialize the graph builder with workflow nodes.
        
        Args:
            workflow_nodes: WorkflowNodes instance containing node handlers
        """
        self.workflow_nodes = workflow_nodes
        self.conditions = WorkflowConditions()
    
    def build_code_generation_graph(self) -> StateGraph:
        """
        Build the code generation workflow (Phase 1 only).
        
        Returns:
            StateGraph: The code generation workflow graph
        """
        logger.debug("Building code generation workflow graph")
        
        # Create a new graph with our state schema
        workflow = StateGraph(WorkflowState)
        
        # Add code generation nodes
        workflow.add_node("generate_code", self.workflow_nodes.generate_code_node)
        workflow.add_node("evaluate_code", self.workflow_nodes.evaluate_code_node)
        workflow.add_node("regenerate_code", self.workflow_nodes.regenerate_code_node)
        
        # Add edges for code generation phase
        workflow.add_edge("generate_code", "evaluate_code")
        workflow.add_edge("regenerate_code", "evaluate_code")
        
        # Add conditional edge for regeneration or completion
        workflow.add_conditional_edges(
            "evaluate_code",
            self.conditions.should_regenerate_or_complete,
            {
                "regenerate_code": "regenerate_code",
                "complete": END  # End when code generation is complete
            }
        )
        
        # Set entry point for code generation
        workflow.set_entry_point("generate_code")
        
        logger.debug("Code generation workflow graph construction completed")
        return workflow
    
    def build_review_graph(self) -> StateGraph:
        """
        Build the review processing workflow (Phase 2 only).
        
        Returns:
            StateGraph: The review processing workflow graph
        """
        logger.debug("Building review processing workflow graph")
        
        # Create a new graph with our state schema
        workflow = StateGraph(WorkflowState)
        
        # Add review processing nodes
        workflow.add_node("process_review", self.workflow_nodes.process_review_node)
        workflow.add_node("analyze_review", self.workflow_nodes.analyze_review_node)
        workflow.add_node("generate_comparison_report", self.workflow_nodes.generate_comparison_report_node)
        
        # Add edges for review phase
        workflow.add_edge("process_review", "analyze_review")
        
        # Add conditional edge for review continuation or completion
        workflow.add_conditional_edges(
            "analyze_review",
            self.conditions.should_continue_review_or_complete,
            {
                "continue_review": END,  # Wait for next review submission
                "generate_comparison_report": "generate_comparison_report"
            }
        )
        
        # Add final edge
        workflow.add_edge("generate_comparison_report", END)
        
        # Set entry point for review processing
        workflow.set_entry_point("process_review")
        
        logger.debug("Review processing workflow graph construction completed")
        return workflow
    
    def build_graph(self) -> StateGraph:
        """
        Build the complete LangGraph workflow (legacy method for compatibility).
        This is mainly used for initial code generation.
        
        Returns:
            StateGraph: The constructed workflow graph
        """
        return self.build_code_generation_graph()