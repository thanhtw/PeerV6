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
        """Function-based template for evaluation prompt - FIXED: Use f-string instead of .format()"""
        # FIXED: Use f-string consistently to avoid brace escaping issues
        base_prompt = f"""You are a Java code quality expert analyzing code to verify correct implementation of specific requested errors.

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
              "Code Segment": "if (obj != null & obj.getValue() > 0)",
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
          """
        
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
      """Function-based template for review analysis prompt with strict evaluation."""
      # Use f-string consistently
      base_prompt = f"""You are an educational assessment specialist analyzing a student's Java code review skills. You must be extremely strict and precise in your evaluation.

  TASK:
  Analyze how effectively the student identified known issues during their code review. You must be very strict and accurate in scoring.

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
  - Accuracy threshold: {accuracy_score_threshold} (must correctly identify error type and location)
  - Meaningfulness threshold: {meaningful_score_threshold} (must clearly explain why it's a problem)

  ⚠️ EXTREMELY STRICT SCORING AND CLASSIFICATION RULES (ABSOLUTELY NO VIOLATIONS):

  A. Core Identification Requirements
    1. A student comment can only be considered "specifically identified" if it meets ALL of the following:
        a) Explicitly mentions error type keywords (e.g., "uses == to compare strings", "null pointer", "logic error")
        b) Correctly points out the error location (method name, line number, or specific code segment)
        c) Comment content substantially matches the known problem
        
    2. If a student comment fails ANY of these conditions, you MUST:
        - Accuracy score: <= 0.3 (maximum 0.3, no higher)
        - Meaningfulness score: <= 0.3 (maximum 0.3, no higher)
        - Classification: MUST be placed in "Missed Problems"
        - Must NOT be counted in "Identified Count"

  B. Scoring Strictness (Extremely Rigorous)
    1. Accuracy Scoring Scale (be very strict):
        - 1.0: Perfectly identifies error type, location, and cause
        - 0.8-0.9: Correctly identifies error type and location, but explanation slightly lacking
        - 0.6-0.7: Error type correct, but location imprecise
        - 0.4-0.5: Partially relevant but with obvious errors or omissions
        - 0.1-0.3: Almost irrelevant or completely wrong
        - 0.0: Completely irrelevant or blank
    
    2. Meaningfulness Scoring Scale (be very strict):
        - 1.0: Clearly explains why it's a problem, describes potential impact or risks
        - 0.8-0.9: Explains why it's a problem, but lacks depth
        - 0.6-0.7: Simply states it's a problem, but lacks depth
        - 0.4-0.5: Only points out location, no explanation of cause
        - 0.1-0.3: Vague or repetitive comment
        - 0.0: Completely meaningless or blank

    3. Strictly Prohibit "Generous Scoring":
        - Absolutely do NOT give "benefit of the doubt" scores
        - When in doubt, give the lower score
        - Better to underestimate than overestimate student capability

  C. Threshold Protection
    1. Scores can only meet or exceed thresholds if the student comment meets ALL of:
        - Explicitly states error type (e.g., "uses == instead of equals()")
        - Clearly explains why it's a problem (e.g., "== compares memory addresses, not content")
        - Accurately identifies location (method name or line number)
    
    2. If the student comment lacks ANY of these elements:
        - BOTH scores MUST be < threshold
        - MUST be placed in "Missed Problems"

  D. Invalid Comment Detection
    A student comment is considered "not identified" if it falls into ANY of these categories:
    - Repetitive words or exclamations (e.g., "there's a problem here", "wrong")
    - Incorrect line number or method name
    - Description completely unrelated to the known problem
    - Vague generalities (e.g., "code quality is poor")
    - Only says "there's an error" without specifying what error
    
    Handling:
    - Accuracy: <= 0.2
    - Meaningfulness: <= 0.2
    - Classification: "Missed Problems"
    - "Student Comment" field: Record as "Not specifically identified" or "Comment irrelevant"

  E. Mandatory Classification Rules (Absolute Rules, Non-Negotiable)
    1. Classification Determination (absolute rule, cannot be violated):
        IF (Accuracy >= {accuracy_score_threshold} AND Meaningfulness >= {meaningful_score_threshold}):
          → MUST be placed in "Identified Problems"
          → MUST be counted in "Identified Count"
        ELSE:
          → MUST be placed in "Missed Problems"
          → Must NOT be counted in "Identified Count"
    
    2. Mutual Exclusivity Principle:
        - Each known problem must appear in exactly one list
        - Absolutely cannot appear in both "Identified Problems" and "Missed Problems"
        - Absolutely cannot omit any known problem

  F. Position and Logic Consistency
    1. If the student comment's claimed location doesn't match the actual error location:
        - Accuracy: <= 0.3
        - Classification: "Missed Problems"
    
    2. If the student comment's logic contradicts the known problem's error logic:
        - Accuracy: <= 0.4
        - Meaningfulness: <= 0.4
        - Classification: "Missed Problems"

  G. Pre-Output Validation (Self-Check Before Submitting)
    Before outputting JSON, you MUST perform these checks:
    1. Confirm every "Identified Problem" has scores >= threshold
    2. Confirm every "Missed Problem" has at least one score < threshold
    3. Confirm "Identified Count" = length of "Identified Problems" array
    4. Confirm all {problem_count} known problems are classified
    5. Confirm no problem appears in both lists

  RESPONSE FORMAT (only these JSON fields and structure allowed):
  {{
    "Identified Problems": [
      {{
        "Problem": "Complete description of the known issue",
        "Student Comment": "Student's relevant comment (must substantially match)",
        "Accuracy": <MUST be >= {accuracy_score_threshold}>,
        "Meaningfulness": <MUST be >= {meaningful_score_threshold}>,
        "Feedback": "Specifically explain how the student's comment correctly identified this issue, citing keywords and location clues they used"
      }}
    ],
    "Missed Problems": [
      {{
        "Problem": "Complete description of the known issue",
        "Student Comment": "Student's attempt (if any) or 'Not mentioned' or 'Comment irrelevant'",
        "Accuracy": <Actual score (MUST be < {accuracy_score_threshold} OR Meaningfulness < {meaningful_score_threshold})>,
        "Meaningfulness": <Actual score>,
        "hint": "Specific guidance: Tell the student which method/code segment to look at for this issue and what error pattern to watch for"
      }}
    ],
    "Identified Count": <MUST equal the length of "Identified Problems" array, NOT the total number of student comments>,
    "Total Problems": {problem_count},
    "Identified Percentage": <(Identified Count / Total Problems) * 100>,
    "Review Sufficient": <Identified Count == Total Problems>,
    "Feedback": "Overall assessment: Specifically point out which types of errors the student did well on and which types need improvement. Avoid empty words, give actionable suggestions."
  }}

  ⚠️ FINAL REMINDERS (Critical):
  1. Better to be strict than lenient
  2. If student comment is vague or unclear, give low scores
  3. If student comment has wrong location, give low scores
  4. If student comment doesn't explain the reason, Meaningfulness MUST be < threshold
  5. "Identified Count" can ONLY count truly correctly identified problems
  6. Scores below threshold MUST be placed in "Missed Problems"
  7. Each known problem must be classified exactly once
  8. You MUST validate all rules are followed before outputting
  """
      
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
        # Use f-string consistently
        base_prompt = f"""You are an educational assessment expert creating a comprehensive code review feedback report for a Java programming student.

    STUDENT PERFORMANCE:
    - Total issues in code: {total_problems}
    - Issues correctly identified: {identified_count} ({accuracy:.1f}%)
    - Issues missed: {missed_count}

    CORRECTLY IDENTIFIED ISSUES:
    {identified_text}

    MISSED ISSUES:
    {missed_text}

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
      "Performance Summary": {{
        "Total Issues": {total_problems},
        "Identified Count": {identified_count},
        "Accuracy Percentage": {accuracy:.1f},
        "Missed Count": {missed_count},
        "Overall Assessment": "Brief overall assessment of the student's performance",
        "Completion Status": "Current status of the review (e.g., 'Excellent work', 'Good progress', 'Needs improvement')"
      }},
      "Correctly Identified Issues": [
        {{
          "Issue Description": "Description of the correctly identified issue",
          "Praise Comment": "Specific praise for finding this issue and what it shows about their skills"
        }}
      ],
      "Missed Issues": [
        {{
          "Issue Description": "Description of the missed issue",
          "Why This Error Is Important": "Educational explanation of why this issue matters",
          "How to Find This Error": "Specific guidance on how to identify this type of issue in the future"
        }}
      ],
      "Tips for Improvement": [
        {{
          "Category": "Area for improvement (e.g., 'Logic Analysis', 'Syntax Review', 'Code Quality')",
          "Tip": "Specific, actionable advice",
          "example": "Brief example or technique to illustrate the tip"
        }}
      ],
      "Java-Specific Guidance": [
        {{
          "Topic": "Java-specific area (e.g., 'Null Pointer Safety', 'Exception Handling', 'Type Safety')",
          "Guidance": "Specific advice for Java code review in this area"
        }}
      ],
      "Encouragement & Next Steps": {{
        "Positive Feedback": "Encouraging comments about their progress and strengths",
        "Next Focus Areas": "What they should focus on in their next review attempt",
        "Learning Objectives": "Key learning goals based on their current performance"
      }},
      "Detailed Feedback": {{
        "Strengths Identified": ["List of specific strengths shown in their review"],
        "Improvement Patterns": ["Patterns in what they missed that suggest areas for focused learning"],
        "Review Approach Feedback": "Feedback on their overall approach to code review"
      }}
    }}
    ```
    CRITICAL REQUIREMENTS:
    - Return ONLY the JSON object with no additional text or formatting
    - Use empty arrays [] if no correctly identified or missed issues exist
    - Ensure all JSON strings are properly escaped and valid
    - Base all feedback on provided performance data"""

        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt