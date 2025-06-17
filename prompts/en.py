import streamlit as st
import re
import random
import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import os
from utils.language_utils import t, get_llm_prompt_instructions, get_current_language

class PromptTemplate:
    def __init__(self, language: str = "en"):
        self.language = get_current_language()
        
    def create_code_generation_prompt_template(
        self,
        code_length: str,
        difficulty_level: str,
        domain: str,
        complexity: str,
        error_count: int,
        error_instructions: str       
    ) -> str:
        """Function-based template for code generation prompt."""
        
        base_prompt = f"""You are an expert Java programming instructor creating educational code with deliberate errors for students to practice code review skills.

    TASK:
    Generate a {code_length} Java program for a {domain} system that contains EXACTLY {error_count} intentional errors for a code review exercise.

    CODE REQUIREMENTS:
    - Create {complexity} appropriate for {difficulty_level} level
    - Follow standard Java conventions for all correct portions
    - Make the code realistic and professional for a {domain} application
    - The program should appear well-structured except for the deliberate errors

    ERROR REQUIREMENTS:
    - Implement EXACTLY {error_count} errors from the specific list below
    - Each error must be an actual Java programming mistake (not comments)
    - Errors should be discoverable through code review
    - Do not add any explanatory comments about the errors in the clean version

    SPECIFIC ERRORS TO IMPLEMENT:
    {error_instructions}

    OUTPUT FORMAT:
    1.  ANNOTATED VERSION with error identification comments:
    ```java-annotated
    // Your code with error annotations
    ```

    2. CLEAN VERSION without error comments:
    ```java-clean
    // The same code with the same errors but no error annotations
    ```

    CRITICAL: Ensure you implement exactly {error_count} errors - verify this count before submitting both versions."""
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_evaluation_prompt_template(
        self,
        error_count: int,
        code: str,
        error_instructions: str        
    ) -> str:
        """Function-based template for evaluation prompt."""
        # Use format() instead of f-strings for complex templates with JSON
        base_prompt = """You are a Java code quality expert analyzing code to verify correct implementation of specific requested errors.

          TASK:
          Evaluate if the provided Java code correctly implements EXACTLY {error_count} specific errors from the requested list.

          CODE TO EVALUATE:
          ```java
          {code}
          ```

          REQUIRED ERRORS ({error_count} total):
          {error_instructions}

          EVALUATION PROCESS:

          1. Examine the code line by line to identify errors matching the requested list
          2. For each matching error, document:
            - Error type and name from the requested list
            - Exact line number(s)
            - Code segment showing the error
            - Brief explanation of why it matches the requirement
          3. Identify any requested errors missing from the code
          4. Verify total error count equals exactly {error_count}

          RESPONSE FORMAT:
          ```json
          {{
          "Identified Problems": [
              {{
              "Error Type": "Logical",
              "Error Name": "Misunderstanding of short-circuit evaluation",
              "Line Number": 42,
              "Code Segment": "if (obj != null & obj.getValue() > 0) {{ ... }}",
              "Explanation": "Uses non-short-circuit '&' operator instead of '&&', causing obj.getValue() to evaluate even if obj is null, potentially causing NullPointerException."
              }}
          ],
          "Missed Problems": [
              {{
              "Error Type": "Code Quality", 
              "Error Name": "Code duplication",
              "Explanation": "No instances of duplicated logic or repeated code blocks found. Code duplication occurs when similar functionality is implemented multiple times instead of being extracted into reusable methods."
              }}
          ],
          "Valid": true,
          "Feedback": "The code successfully implements all {error_count} requested errors."
          }}
          ```

          VALIDATION CRITERIA:
          - "Valid" = true ONLY if exactly {error_count} requested errors are implemented
          - Focus solely on the specified errors, not general code quality issues
          - Ensure each identified error truly matches a requested error          
          """.format(
              error_count=error_count,
              code=code,
              error_instructions=error_instructions
          )
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_regeneration_prompt_template(
        self,
        total_requested: int,
        domain: str,
        missing_text: str,
        found_text: str,
        code: str       
    ) -> str:
        """Function-based template for regeneration prompt."""
        base_prompt = f"""You are an educational Java error creator who deliberately introduces specific errors in code for teaching purposes.

    TASK:
    Modify the provided Java code to contain exactly {total_requested} errors - no more, no less.

    CURRENT STATE:
    - Original domain: {domain}
    - Missing errors to ADD: {missing_text}
    - Existing errors to PRESERVE: {found_text}

    MODIFICATION REQUIREMENTS:
    - Add only the specific missing errors listed above
    - Preserve all existing errors without modification
    - Maintain the original {domain} structure and functionality
    - Each error must be actual Java code mistakes, not comments
    - Do not improve or fix any existing code

    ERROR IMPLEMENTATION:
    - Implement exactly the missing errors from the provided list
    - Keep all existing errors unchanged
    - Ensure total error count equals exactly {total_requested}
    - In annotated version, mark new errors with: // ERROR: [type] - [name] - [brief description]
    - Do not add explanatory comments in the clean version

    OUTPUT FORMAT:
    1. ANNOTATED VERSION with error identification comments:
    ```java-annotated
    // Your modified code with error annotations for new errors only
    ```
    2. CLEAN VERSION without error comments:
    ```java-clean
    // The same code with the same errors but no error annotations
    ```

    CRITICAL: Verify you have exactly {total_requested} total errors before submitting both versions.

    ORIGINAL CODE:
    ```java
    {code}
    ```"""
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_review_analysis_prompt_template(
        self,
        code: str,
        problem_count: int,
        problems_text: str,
        student_review: str,
        accuracy_score_threshold: float,
        meaningful_score_threshold: float       
    ) -> str:
        """Function-based template for review analysis prompt."""
        # Use format() for complex templates with JSON
        base_prompt = """You are an educational assessment specialist analyzing a student's Java code review skills.

    TASK:
    Analyze how effectively the student identified known issues during their code review.

    CODE UNDER REVIEW:
    ```java
    {code}
    ```
    KNOWN ISSUES ({problem_count} total):
    {problems_text}

    STUDENT'S REVIEW:
    ```
    {student_review}
    ```
    SCORING THRESHOLDS:

    - Accuracy threshold: {accuracy_score_threshold} (correct identification and location)
    - Meaningfulness threshold: {meaningful_score_threshold} (quality of explanation)

    EVALUATION PROCESS:

    1. For each known issue, determine if the student addressed it
    2. Score relevant student comments (0.0-1.0 scale):
      - Accuracy: How correctly they identified the issue and location
      - Meaningfulness: How well they explained why it's problematic
    3. Classification rule: Issue is "Identified" ONLY if both scores meet thresholds
      - Both scores ≥ thresholds → "Identified Problems"
      -Otherwise → "Missed Problems"

    RESPONSE FORMAT:
    ```json
    {{
    "Identified Problems": [
        {{
        "Problem": "SPECIFIC KNOWN ISSUE TEXT",
        "Student Comment": "STUDENT'S RELEVANT COMMENT",
        "Accuracy": 0.9,
        "Meaningfulness": 0.8,
        "Feedback": "Brief feedback on this identification"
        }}
    ],
    "Missed Problems": [
        {{
        "Problem": "SPECIFIC KNOWN ISSUE TEXT - Not addressed",
        "hint": "Educational hint for finding this issue"
        }}
    ],
    "Identified Count": 1,
    "Total Problems": {problem_count},
    "Identified Percentage": 25.0,
    "Review Sufficient": false,
    "Feedback": "Overall assessment with specific improvement suggestions"
    }}
    ```

    CRITICAL REQUIREMENTS:
    - Each problem appears exactly once in either "Identified" or "Missed"
    - "Identified Count" equals the number of items in "Identified Problems"
    - Use only the specified JSON fields""".format(
        code=code,
        problem_count=problem_count,
        problems_text=problems_text,
        student_review=student_review,
        accuracy_score_threshold=accuracy_score_threshold,
        meaningful_score_threshold=meaningful_score_threshold
    )
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_feedback_prompt_template(
        self,
        iteration: int,
        max_iterations: int,
        identified: int,
        total: int,
        accuracy: float,
        remaining: int,
        identified_text: str,
        missed_text: str       
    ) -> str:
        """Function-based template for feedback prompt."""
        base_prompt = f"""You are a Java mentor providing targeted code review guidance to help a student improve their review skills.

    STUDENT CONTEXT:
    - Review attempt {iteration} of {max_iterations} 
    - Issues found: {identified}/{total} ({accuracy:.1f}%)
    - Remaining attempts: {remaining}

    CORRECTLY IDENTIFIED ISSUES:
    {identified_text}

    MISSED ISSUES:
    {missed_text}

    TASK:
    Create brief, actionable guidance (3-4 sentences maximum) to help the student find more issues in their next review attempt.

    GUIDANCE REQUIREMENTS:
    - Focus on 1-2 most important improvement areas
    - Provide specific strategies (what to look for, where to focus)
    - Be encouraging yet direct
    - Include example of meaningful vs vague commenting when relevant

    EFFECTIVE GUIDANCE EXAMPLE:
    "Look more carefully at method parameters and return types. Several issues involve type mismatches that can be spotted by comparing declared types with actual values. Also check for proper null handling before method calls."

    INEFFECTIVE GUIDANCE EXAMPLE:
    "Keep trying to find more issues. There are several problems in the code that you missed. Try to be more thorough in your next review attempt."

    OUTPUT:
    Provide only the guidance text - no introduction, headers, or explanations."""

        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_comparison_report_prompt_template(
        self,
        total_problems: int,
        identified_count: int,
        accuracy: float,
        missed_count: int,
        identified_text: str,
        missed_text: str       
    ) -> str:
        """Function-based template for comparison report prompt."""
        # Use format() for complex templates with JSON
        base_prompt = """You are an educational assessment expert creating a comprehensive code review feedback report for a Java programming student.

    STUDENT PERFORMANCE:
    - Total issues in code: {total_problems}
    - Issues correctly identified: {identified_count} ({accuracy:.1f}%)
    - Issues missed: {missed_count}

    CORRECTLY IDENTIFIED ISSUES:
    {identified_text}

    MISSED ISSUES:
    {missed_text}

    {progress_info}

    TASK:
    Create an educational JSON report that helps the student improve their Java code review skills.

    REPORT REQUIREMENTS:
    - Use encouraging, constructive tone while being honest about areas for improvement
    - Focus on systematic improvement patterns and actionable guidance
    - Include specific Java code review techniques relevant to their performance
    - Base all feedback on actual performance data provided
    - Keep individual text fields concise but informative (2-3 sentences maximum)

    OUTPUT FORMAT:
    Return only a valid JSON object with these exact fields:
    ```json
    {{
      "performance_summary": {{
        "total_issues": {total_problems},
        "identified_count": {identified_count},
        "accuracy_percentage": {accuracy:.1f},
        "missed_count": {missed_count},
        "overall_assessment": "Brief overall assessment of the student's performance",
        "completion_status": "Current status of the review (e.g., 'Excellent work', 'Good progress', 'Needs improvement')"
      }},
      "correctly_identified_issues": [
        {{
          "issue_description": "Description of the correctly identified issue",
          "praise_comment": "Specific praise for finding this issue and what it shows about their skills"
        }}
      ],
      "missed_issues": [
        {{
          "issue_description": "Description of the missed issue",
          "why_important": "Educational explanation of why this issue matters",
          "how_to_find": "Specific guidance on how to identify this type of issue in the future"
        }}
      ],
      "tips_for_improvement": [
        {{
          "category": "Area for improvement (e.g., 'Logic Analysis', 'Syntax Review', 'Code Quality')",
          "tip": "Specific, actionable advice",
          "example": "Brief example or technique to illustrate the tip"
        }}
      ],
      "java_specific_guidance": [
        {{
          "topic": "Java-specific area (e.g., 'Null Pointer Safety', 'Exception Handling', 'Type Safety')",
          "guidance": "Specific advice for Java code review in this area"
        }}
      ],
      "encouragement_and_next_steps": {{
        "positive_feedback": "Encouraging comments about their progress and strengths",
        "next_focus_areas": "What they should focus on in their next review attempt",
        "learning_objectives": "Key learning goals based on their current performance"
      }},
      "detailed_feedback": {{
        "strengths_identified": ["List of specific strengths shown in their review"],
        "improvement_patterns": ["Patterns in what they missed that suggest areas for focused learning"],
        "review_approach_feedback": "Feedback on their overall approach to code review"
      }}
    }}
    ```
    CRITICAL REQUIREMENTS:
    - Return ONLY the JSON object with no additional text or formatting
    - Use empty arrays [] if no correctly identified or missed issues exist
    - Ensure all JSON strings are properly escaped and valid
    - Base all feedback on provided performance data""".format(
        total_problems=total_problems,
        identified_count=identified_count,
        accuracy=accuracy,
        missed_count=missed_count,
        identified_text=identified_text,
        missed_text=missed_text
    )

        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt