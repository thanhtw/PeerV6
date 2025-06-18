import re
import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel

from utils.code_utils import create_review_analysis_prompt, create_feedback_prompt, create_comparison_report_prompt, process_llm_response
from utils.llm_logger import LLMInteractionLogger
from utils.language_utils import t
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StudentResponseEvaluator:
    """
    Evaluates student code reviews against known problems in the code.
    
    This class analyzes how thoroughly and accurately a student identified 
    issues in a code snippet, providing detailed feedback and metrics.
    """    
    def __init__(self, llm: BaseLanguageModel = None,                 
                 llm_logger: LLMInteractionLogger = None):
        """
        Initialize the StudentResponseEvaluator.
        
        Args:
            llm: Language model to use for evaluation           
            llm_logger: Logger for tracking LLM interactions
        """
        self.llm = llm
        self.llm_logger = llm_logger or LLMInteractionLogger()

        # Load meaningful score threshold from environment variable with default fallback to 0.6
        try:
            self.meaningful_score_threshold = float(os.getenv("MEANINGFUL_SCORE", "0.6"))
            self.accuracy_score_threshold = float(os.getenv("ACCURACY_SCORE", "0.7"))
            logger.debug(f"Using meaningful score threshold: {self.meaningful_score_threshold}")
            logger.debug(f"Using accuracy score threshold: {self.accuracy_score_threshold}")
        except (ValueError, TypeError):
            logger.warning("Invalid MEANINGFUL_SCORE in environment, defaulting to 0.6")
            logger.warning("Invalid ACCURACY_SCORE in environment, defaulting to 0.7")
            self.meaningful_score_threshold = 0.6
            self.accuracy_score_threshold = 0.7
    
    def evaluate_review(self, code_snippet: str, known_problems: List[str], student_review: str) -> Dict[str, Any]:
        """
        Evaluate a student's review against known problems.
        Uses the create_review_analysis_prompt function from code_utils.
        
        Args:
            code_snippet: The original code snippet with injected errors
            known_problems: List of known problems in the code
            student_review: The student's review comments
            
        Returns:
            Dictionary with detailed analysis results
        """
        if not self.llm:
            logger.warning("No LLM available for review evaluation, using fallback evaluation")
            return "// Error: No LLM available for code generation"

        try:
            logger.debug("Evaluating student review with code_utils prompt")
            
            if not self.llm:
                logger.warning(t("no_llm_provided_for_evaluation"))
                return ""
            
            # Create a review analysis prompt using the utility function
            prompt = create_review_analysis_prompt(
                code=code_snippet,
                known_problems=known_problems,
                student_review=student_review
            )
            
            try:
                # Metadata for logging
                metadata = {
                    t("code_length"): len(code_snippet.splitlines()),
                    t("known_problems_count"): len(known_problems),
                    t("student_review_length"): len(student_review.splitlines())
                }
                # Get the evaluation from the LLM
                logger.debug("Sending student review to LLM for evaluation")
                response = self.llm.invoke(prompt)
                processed_response = process_llm_response(response)
               
                # Log the interaction
                self.llm_logger.log_review_analysis(prompt, processed_response, metadata)
                
                # Make sure we have a response
                if not response:
                    logger.error(t("empty_response_from_llm"))
                    return ""
                
                # Extract JSON data from the response
                analysis_data = self._extract_json_from_text(processed_response)       
                         
                # Process the analysis data
                enhanced_analysis = self._process_enhanced_analysis(analysis_data, known_problems)   
                       
                return enhanced_analysis
                
            except Exception as e:
                logger.error(f"{t('error')} {t('evaluating_review_with_llm')}: {str(e)}")                
                # Log the error
                error_metadata = {**metadata, "error": str(e)}
                self.llm_logger.log_review_analysis(prompt, f"{t('error')}: {str(e)}", error_metadata)                
                return ""
            
        except Exception as e:
            logger.error(f"{t('exception_in_evaluate_review')}: {str(e)}")
            return ""
            
    def _process_enhanced_analysis(self, analysis_data: Dict[str, Any], known_problems: List[str]) -> Dict[str, Any]:
        """
        Process and enhance the analysis data from the LLM.
        
        Args:
            analysis_data: Raw analysis data from LLM
            known_problems: List of known problems for reference
            
        Returns:
            Enhanced analysis data
        """

        if not analysis_data:
            return ""
        
        # Extract core metrics with defaults
        identified_count = analysis_data.get(f"{t('identified_count')}",0)
        total_problems = analysis_data.get(f"{t('total_problems')}",len(known_problems))

        # Track meaningful comments separately
        identified_problems = analysis_data.get(f"{t('identified_problems')}", [])

        # Calculate percentages
        if total_problems > 0:
            identified_percentage = (identified_count / total_problems) * 100
        else:
            identified_percentage = 100.0

        # Calculate percentages
        if total_problems > 0:
            identified_percentage = (identified_count / total_problems) * 100
        else:
            identified_percentage = 100.0

        # Check if review is sufficient based on meaningful comments
        review_sufficient = analysis_data.get(f"{'review_sufficient'}", False)
        identified_problems =  analysis_data.get(f"{t('identified_problems')}", False)
        missed_problems = analysis_data.get(f"{t('missed_problems')}", False)
        
        # Construct enhanced result using t() function for keys
        enhanced_result = {
            t("identified_problems"): identified_problems,
            t("missed_problems"): missed_problems,
            t("identified_count"): identified_count,
            t("total_problems"): total_problems,
            t("identified_percentage"): identified_percentage,
            t("review_sufficient"): review_sufficient
        }
        
        return enhanced_result
         
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON data from LLM response text with improved robustness for malformed responses.
        
        Args:
            text: Text containing JSON data
            
        Returns:
            Extracted JSON data
        """
        # Handle None or empty text
        if not text:
            return {t("error"): t("empty_response_from_llm")}
        
        try:
            # First try direct JSON parsing if the response looks like JSON
            if text.strip().startswith('{') and text.strip().endswith('}'):
                try:
                    # Clean the response to fix common JSON issues
                    json_str = text.strip()
                    # Fix trailing commas which are invalid in JSON
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Try to parse as JSON directly
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # If direct parsing fails, continue with regex extraction
                    pass
                    
            # For the specific broken format in the example
            # Look for key JSON fields and try to reconstruct a valid JSON
            identified_problems_match = re.search(r'"(已識別問題|Identified Problems)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            
            # Fallback manual extraction when JSON is severely malformed
            analysis = {}
            
            # Extract identified problems with either Chinese or English field names
            if identified_problems_match:
                identified_problems_text = identified_problems_match.group(2)
                # Try to extract individual problem objects
                problem_objects = []
                current_problem = {}
                lines = identified_problems_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Skip empty lines or just containing brackets/braces
                    if not line or line in ['{', '}', '[', ']']:
                        continue
                    
                    # Check for key-value pairs
                    key_value_match = re.search(r'"([^"]+)"\s*:\s*(.+)', line)
                    if key_value_match:
                        key = key_value_match.group(1)
                        value = key_value_match.group(2).strip()
                        
                        # Remove trailing comma if present
                        if value.endswith(','):
                            value = value[:-1].strip()
                        
                        # Handle string values (quoted)
                        if value.startswith('"') and value.endswith('"'):
                            current_problem[key] = value[1:-1]
                        # Handle numeric values
                        elif value.replace('.', '', 1).isdigit():
                            current_problem[key] = float(value) if '.' in value else int(value)
                        # Handle boolean values
                        elif value.lower() in ['true', 'false']:
                            current_problem[key] = value.lower() == 'true'
                        else:
                            current_problem[key] = value
                    
                    # If we see a closing brace, add the current problem to the list
                    if '}' in line and current_problem:
                        problem_objects.append(current_problem)
                        current_problem = {}
                
                # Add any remaining problem
                if current_problem:
                    problem_objects.append(current_problem)
                    
                # Add the extracted problems to the analysis
                analysis[t("identified_problems")] = problem_objects
            
            # Extract other fields similarly (missed problems, counts, etc.)
            # Example for identified count
            identified_count_match = re.search(r'"(識別數量|Identified Count)"\s*:\s*(\d+)', text)
            if identified_count_match:
                analysis[t("identified_count")] = int(identified_count_match.group(2))
                
            # Example for total problems
            total_problems_match = re.search(r'"(問題總數|Total Problems)"\s*:\s*(\d+)', text)
            if total_problems_match:
                analysis[t("total_problems")] = int(total_problems_match.group(2))
                
            # Example for identified percentage
            percentage_match = re.search(r'"(識別百分比|Identified Percentage)"\s*:\s*([0-9.]+)', text)
            if percentage_match:
                analysis[t("identified_percentage")] = float(percentage_match.group(2))
                
            # Example for review sufficient
            sufficient_match = re.search(r'"(審查充分性|Review Sufficient)"\s*:\s*(true|false)', text, re.IGNORECASE)            
            if sufficient_match:
                analysis[t("review_sufficient")] = bool(sufficient_match.group(2))
            
            # Try to extract missed problems array separately
            missed_problems_match = re.search(r'"(遺漏問題|Missed Problems)"\s*:\s*\[(.*?)\]', text, re.DOTALL)

            if missed_problems_match:
                # Parse the missed_text to extract problem objects
                #analysis[t("missed_problems")] = missed_problems
                missed_text = missed_problems_match.group(2).strip()
                missed_problems = []
                current_problem = {}
                lines = missed_text.strip().split('\n')

                for line in lines:
                    line = line.strip()
                    # Skip empty lines or just containing brackets/braces
                    if not line or line in ['{', '}', '[', ']']:
                        continue
                    
                    # Check for key-value pairs
                    key_value_match = re.search(r'"([^"]+)"\s*:\s*(.+)', line)
                    if key_value_match:
                        key = key_value_match.group(1)
                        value = key_value_match.group(2).strip()
                        
                        # Remove trailing comma if present
                        if value.endswith(','):
                            value = value[:-1].strip()
                        
                        # Handle string values (quoted)
                        if value.startswith('"') and value.endswith('"'):
                            current_problem[key] = value[1:-1]
                        # Handle numeric values
                        elif value.replace('.', '', 1).isdigit():
                            current_problem[key] = float(value) if '.' in value else int(value)
                        # Handle boolean values
                        elif value.lower() in ['true', 'false']:
                            current_problem[key] = value.lower() == 'true'
                        else:
                            current_problem[key] = value
                    
                    # If we see a closing brace, add the current problem to the list
                    if '}' in line and current_problem:
                        missed_problems.append(current_problem)
                        current_problem = {}

                # Add any remaining problem
                if current_problem:
                    missed_problems.append(current_problem)
                
                # Add the parsed missed problems to the analysis
                analysis[t("missed_problems")] = missed_problems
            else:
                analysis[t("missed_problems")] = []
            
            # If we extracted enough fields to form a valid analysis, return it
            if t("identified_problems") in analysis or t("missed_problems") in analysis:
                return analysis
                
            # If all else fails, return a minimal valid structure
            logger.warning(t("could_not_extract_json_from_response"))
            return []
            
        except Exception as e:
            logger.error(f"{t('error_extracting_json')}: {str(e)}")
            return {
                t("error"): f"{t('error_extracting_json')}: {str(e)}",
                t("raw_text"): text[:500] + ("..." if len(text) > 500 else "")
            }

    def generate_targeted_guidance(self, code_snippet: str, known_problems: List[str], student_review: str, review_analysis: Dict[str, Any], iteration_count: int, max_iterations: int) -> str:
        """
        Generate targeted guidance for the student to improve their review.
        Ensures guidance is concise and focused with proper language support.
        
        Args:
            code_snippet: The original code snippet with injected errors
            known_problems: List of known problems in the code
            student_review: The student's review comments
            review_analysis: Analysis of the student review
            iteration_count: Current iteration number
            max_iterations: Maximum number of iterations
            
        Returns:
            Targeted guidance text
        """        
        if not self.llm:
            logger.warning(t("no_llm_provided_for_guidance"))
            return ""
        
        try:
            # Get iteration information to add to review_analysis for context
            review_context = review_analysis.copy()
            review_context.update({
                t("iteration_count"): iteration_count,
                t("max_iterations"): max_iterations,
                t("remaining_attempts"): max_iterations - iteration_count
            })

            # Use the utility function to create the prompt
            prompt = create_feedback_prompt(
                review_analysis=review_context,
                iteration= iteration_count,
                max_iterations=max_iterations
            )

            #prompt += "\n\nIMPORTANT: Focus on helping the student make more meaningful comments. A good comment should clearly explain WHAT the issue is and WHY it's a problem, not just identify where it is. For example, instead of just 'Line 11: null issue', guide them to write 'Line 11: Object is accessed before null check, which could cause NullPointerException'."

            metadata = {
                t("iteration_count"): iteration_count,
                t("max_iterations"): max_iterations,
                t("identified_count"):  review_analysis[t('identified_count')],
                t("total_problems"): review_analysis[t('total_problems')],
                t("accuracy_percentage"): review_analysis[t('accuracy_percentage')]
            }

            logger.info(t("generating_concise_targeted_guidance").format(iteration_count=iteration_count))
            response = self.llm.invoke(prompt)
            guidance = process_llm_response(response)
            
            
            # Ensure response is concise - trim if needed
            if len(guidance.split()) > 100:
                # Split into sentences and take the first 3-4
                sentences = re.split(r'(?<=[.!?])\s+', guidance)
                guidance = ' '.join(sentences[:4])
                logger.info(t("trimmed_guidance_words").format(
                    before=len(guidance.split()), 
                    after=len(guidance.split())
                ))
            
            # Log the interaction
            self.llm_logger.log_summary_generation(prompt, guidance, metadata)            
            return guidance
            
        except Exception as e:
            logger.error(f"{t('error_generating_guidance')}: {str(e)}")            
            
            # Create error metadata with translated keys
            error_metadata = {
                t("iteration_count"): iteration_count,
                t("max_iterations"): max_iterations,
                t("identified_count"): review_analysis[t('identified_count')],
                t("total_problems"): review_analysis[t('total_problems')],
                t("error"): str(e)
            }            
            
            # Log the error
            self.llm_logger.log_interaction(
                t('targeted_guidance'), 
                prompt,
                f"{t('error')}: {str(e)}", 
                error_metadata
            )
                
            # Fallback to concise guidance
            return ""
        
    def validate_review_format(self, student_review: str) -> Tuple[bool, str]:
        """
        Validate the format of a student review.
        
        Args:
            student_review: The student's review text
            
        Returns:
            Tuple[bool, str]: (is_valid, reason) where is_valid is True if the review
                            format is valid, and reason explains any validation errors
        """
        if not student_review or not student_review.strip():
            return False, t("review_cannot_be_empty")
        
        # Check if the review has at least one line that follows the expected format
        # Expected format: "Line X: Description of issue"
        valid_line_pattern = re.compile(r'(?:Line|行)\s*\d+\s*[:：]')
        
        # Split the review into lines and check each line
        lines = student_review.strip().split('\n')
        valid_lines = [i+1 for i, line in enumerate(lines) if valid_line_pattern.search(line)]
        
        # If we have at least one valid line, the review is valid
        if valid_lines:
            return True, ""
        
        # Otherwise, return a validation error
        return False, t("please_use_format_line_description")
   
    def generate_comparison_report(self, evaluation_errors: List[str], review_analysis: Dict[str, Any], 
                              review_history: List[Dict[str, Any]] = None) -> str:
        """
        Generate a comparison report showing progress across review attempts.
        Uses the LLM instance that's already available in the class.
        
        Args:
            evaluation_errors: List of errors found by the evaluation
            review_analysis: Analysis of the latest student review
            review_history: History of all review attempts
            
        Returns:
            Formatted comparison report
        """
        try:
            # Check if LLM is available
            if not self.llm:
                logger.error(f"{t('error')} generating comparison report: No LLM available")
                return ""
                
            # Create the prompt for the LLM
            prompt = create_comparison_report_prompt(review_analysis)
            
            # Generate the report with the LLM
            response = self.llm.invoke(prompt)
           
            # Process the response
            if hasattr(response, 'content'):
                report = response.content
            elif isinstance(response, dict) and 'content' in response:
                report = response['content']
            else:
                report = str(response)
            
            # Clean up the report
            report = report.replace('\\n', '\n')
            
           
            try:
                # First try to parse as direct JSON
                formatted_report = self._extract_and_format_comparison_data(report, review_analysis, evaluation_errors)
                
                # Log the report generation
                self.llm_logger.log_interaction("comparison_report", prompt, formatted_report, {
                    t("evaluation_errors_count"): len(evaluation_errors),
                    t("review_analysis"): review_analysis,
                    t("review_history_count"): len(review_history) if review_history else 0
                })               
                
                return formatted_report
                
            except Exception as extraction_error:
                logger.warning(f"Error extracting and formatting comparison data: {extraction_error}")
                # Fall back to original processing logic
                return self._process_original_report_format(report, review_analysis, evaluation_errors)
            
        except Exception as e:
            # Log the error
            logger.error(f"Error generating comparison report with LLM: {str(e)}")
            # Return a fallback report
            return self._generate_fallback_comparison_report(review_analysis, review_history)
    
    def _extract_and_format_comparison_data(self, raw_content: str, review_analysis: Dict[str, Any], 
                                       evaluation_errors: List[str]) -> str:
        """
        Extract data from LLM response content and format according to provided JSON structure.
        
        Args:
            raw_content: Raw content from LLM response
            review_analysis: Analysis of the latest student review
            evaluation_errors: List of errors found by evaluation
            
        Returns:
            Formatted comparison report as JSON string
        """
        try:
            # Try to parse existing JSON structure from raw content
            parsed_data = None
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    # Clean up common JSON issues
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
                    json_str = re.sub(r'(\w+):', r'"\1":', json_str)    # Quote unquoted keys
                    parsed_data = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.debug("Could not parse JSON from raw content, extracting manually")
            
            # Initialize the report structure
            formatted_report = {}
            print("\n\nParsed Data:", parsed_data)
            print("\n\nRaw Content:", raw_content)
            # Extract each required section from parsed_data or raw_content
            if parsed_data and isinstance(parsed_data, dict):
                # Extract from parsed JSON
                formatted_report[t("performance_summary")] = parsed_data.get(t("performance_summary"), {})
                formatted_report[t("correctly_identified_issues")] = parsed_data.get(t("correctly_identified_issues"), [])
                formatted_report[t("missed_issues")] = parsed_data.get(t("missed_issues"), [])
                formatted_report[t("tips_for_improvement")] = parsed_data.get(t("tips_for_improvement"), [])
                formatted_report[t("java_specific_guidance")] = parsed_data.get(t("java_specific_guidance"), [])
                formatted_report[t("encouragement_and_next_steps")] = parsed_data.get(t("encouragement_and_next_steps"), {})
                formatted_report[t("detailed_feedback")] = parsed_data.get(t("detailed_feedback"), {})
            else:
                # Extract from raw text using regex patterns
                formatted_report[t("performance_summary")] = self._extract_performance_summary(raw_content)
                formatted_report[t("correctly_identified_issues")] = self._extract_identified_issues(raw_content)
                formatted_report[t("missed_issues")] = self._extract_missed_issues(raw_content)
                formatted_report[t("tips_for_improvement")] = self._extract_tips_for_improvement(raw_content)
                formatted_report[t("java_specific_guidance")] = self._extract_java_specific_guidance(raw_content)
                formatted_report[t("encouragement_and_next_steps")] = self._extract_encouragement_and_next_steps(raw_content)
                formatted_report[t("detailed_feedback")] = self._extract_detailed_feedback(raw_content)
            
            # Return as formatted JSON string
            return json.dumps(formatted_report, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error in _extract_and_format_comparison_data: {str(e)}")
            raise

    def _extract_performance_summary(self, content: str) -> Dict[str, Any]:
        """Extract performance_summary section from raw content."""
        try:
            # Look for performance_summary section
            pattern = r'"?"Performance Summary"?\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                summary_content = '{' + match.group(1) + '}'
                try:
                    return json.loads(summary_content)
                except json.JSONDecodeError:
                    pass
            return {}
        except Exception:
            return {}

    def _extract_identified_issues(self, content: str) -> List[Dict[str, Any]]:
        """Extract correctly_identified_issues section from raw content."""
        try:
            pattern = r'"?correctly_identified_issues"?\s*:\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                issues_content = '[' + match.group(1) + ']'
                try:
                    return json.loads(issues_content)
                except json.JSONDecodeError:
                    pass
            return []
        except Exception:
            return []

    def _extract_missed_issues(self, content: str) -> List[Dict[str, Any]]:
        """Extract missed_issues section from raw content."""
        try:
            pattern = r'"?missed_issues"?\s*:\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                issues_content = '[' + match.group(1) + ']'
                try:
                    return json.loads(issues_content)
                except json.JSONDecodeError:
                    pass
            return []
        except Exception:
            return []

    def _extract_tips_for_improvement(self, content: str) -> List[Dict[str, Any]]:
        """Extract tips_for_improvement section from raw content."""
        try:
            pattern = r'"?tips_for_improvement"?\s*:\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                tips_content = '[' + match.group(1) + ']'
                try:
                    return json.loads(tips_content)
                except json.JSONDecodeError:
                    pass
            return []
        except Exception:
            return []

    def _extract_java_specific_guidance(self, content: str) -> List[Dict[str, Any]]:
        """Extract java_specific_guidance section from raw content."""
        try:
            pattern = r'"?java_specific_guidance"?\s*:\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                guidance_content = '[' + match.group(1) + ']'
                try:
                    return json.loads(guidance_content)
                except json.JSONDecodeError:
                    pass
            return []
        except Exception:
            return []

    def _extract_encouragement_and_next_steps(self, content: str) -> Dict[str, Any]:
        """Extract encouragement_and_next_steps section from raw content."""
        try:
            pattern = r'"?encouragement_and_next_steps"?\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                encouragement_content = '{' + match.group(1) + '}'
                try:
                    return json.loads(encouragement_content)
                except json.JSONDecodeError:
                    pass
            return {}
        except Exception:
            return {}

    def _extract_detailed_feedback(self, content: str) -> Dict[str, Any]:
        """Extract detailed_feedback section from raw content."""
        try:
            pattern = r'"?detailed_feedback"?\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                feedback_content = '{' + match.group(1) + '}'
                try:
                    return json.loads(feedback_content)
                except json.JSONDecodeError:
                    pass
            return {}
        except Exception:
            return {}
    
    def _generate_fallback_comparison_report(self, review_analysis: Dict[str, Any], review_history: List[Dict[str, Any]] = None) -> str:
        """
        Generate a basic comparison report when LLM fails.
        
        Args:
            review_analysis: Analysis data
            review_history: History of reviews
            
        Returns:
            Basic JSON comparison report
        """
        try:
            total_issues = review_analysis.get(t("total_problems"), 0)
            identified_count = review_analysis.get(t("identified_count"), 0)
            missed_count = total_issues - identified_count
            accuracy = review_analysis.get(t("identified_percentage"), 0.0)
            
            # Determine completion status
            if identified_count == total_issues:
                status = "Excellent work"
            elif identified_count > total_issues * 0.7:
                status = "Good progress"
            else:
                status = "Needs improvement"
            
            report = {
                "performance_summary": {
                    "total_issues": total_issues,
                    "identified_count": identified_count,
                    "accuracy_percentage": accuracy,
                    "missed_count": missed_count,
                    "overall_assessment": f"You identified {identified_count} out of {total_issues} issues",
                    "completion_status": status
                },
                "correctly_identified_issues": [
                    {
                        "issue_description": "Code issues were identified in your review",
                        "praise_comment": "Good effort in analyzing the code"
                    }
                ] if identified_count > 0 else [],
                "missed_issues": [
                    {
                        "issue_description": "Some issues were not identified",
                        "why_important": "Identifying all issues helps improve code quality",
                        "how_to_find": "Review code more systematically line by line"
                    }
                ] if missed_count > 0 else [],
                "tips_for_improvement": [
                    {
                        "category": "Code Review Skills",
                        "tip": "Practice systematic code analysis",
                        "example": "Check syntax, logic, and best practices in order"
                    }
                ],
                "java_specific_guidance": [
                    {
                        "topic": "Common Java Errors",
                        "guidance": "Focus on null checks, string comparisons, and array bounds"
                    }
                ],
                "encouragement_and_next_steps": {
                    "positive_feedback": "Keep practicing to improve your skills",
                    "next_focus_areas": "Focus on areas where you missed issues",
                    "learning_objectives": "Develop more comprehensive review approach"
                },
                "detailed_feedback": {
                    "strengths_identified": ["Engaged in code review process"],
                    "improvement_patterns": ["Could benefit from more systematic approach"],
                    "review_approach_feedback": "Continue practicing with different error types"
                }
            }
            
            return json.dumps(report, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error generating fallback report: {e}")
            # Return minimal valid JSON
            return json.dumps({
                "performance_summary": {
                    "total_issues": 0,
                    "identified_count": 0,
                    "accuracy_percentage": 0.0,
                    "missed_count": 0,
                    "overall_assessment": "Review analysis unavailable",
                    "completion_status": "Error"
                },
                "correctly_identified_issues": [],
                "missed_issues": [],
                "tips_for_improvement": [],
                "java_specific_guidance": [],
                "encouragement_and_next_steps": {
                    "positive_feedback": "System error occurred",
                    "next_focus_areas": "Please try again",
                    "learning_objectives": "Continue practicing"
                },
                "detailed_feedback": {
                    "strengths_identified": [],
                    "improvement_patterns": [],
                    "review_approach_feedback": "Please try again"
                }
            }, indent=2)
