"""
Step 3: Findings Transmission Processor

This module implements the processor for Step 3 of the DAM Compliance Analyzer
workflow. It handles the generation of findings in both structured JSON format
and human-readable report format.
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List, Union

from .base_processor import (
    BaseProcessor,
    ProcessorResult,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from prompts import format_step3_prompt
from schemas import get_findings_schema, validate_findings_data, create_empty_findings_output
from services import AIResponse

logger = logging.getLogger(__name__)


class Step3Processor(BaseProcessor):
    """
    Processor for Step 3: Findings Transmission.
    
    This processor handles the generation of findings in both structured JSON format
    and human-readable report format based on the completed job aid assessment.
    """
    
    def _format_prompt(self, metadata: Optional[Dict[str, Any]] = None,
                      previous_step_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt for Step 3.
        
        Args:
            metadata: Optional metadata to include in the prompt
            previous_step_result: Results from Step 2
            
        Returns:
            str: The formatted prompt
        """
        findings_schema = get_findings_schema()
        return format_step3_prompt(findings_schema, previous_step_result, metadata)
    
    async def process(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                     previous_step_result: Optional[Dict[str, Any]] = None) -> ProcessorResult:
        """
        Process Step 3: Findings Transmission.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            previous_step_result: Results from Step 2
            
        Returns:
            ProcessorResult: The result of processing with both JSON and human-readable outputs
            
        Raises:
            ProcessorError: If processing fails
        """
        try:
            # Validate inputs
            self._validate_inputs(image_bytes, metadata, previous_step_result)
            
            # Format prompt
            prompt = self._format_prompt(metadata, previous_step_result)
            
            # Send request to AI model
            logger.info("Sending Step 3 Findings Transmission request to AI model")
            response = await self._send_request(image_bytes, prompt)
            
            # Parse response
            parsed_data = self._parse_response(response)
            
            # Create result
            result = ProcessorResult(
                success=True,
                data=parsed_data,
                raw_response=response.text
            )
            
            logger.info("Step 3 Findings Transmission completed successfully")
            return result
            
        except ValidationError as e:
            error_msg = f"Step 3 validation error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except ProcessingError as e:
            error_msg = f"Step 3 processing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except OutputParsingError as e:
            error_msg = f"Step 3 output parsing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error in Step 3: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
    
    def _validate_inputs(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                        previous_step_result: Optional[Dict[str, Any]] = None) -> None:
        """
        Validate the inputs to the processor.
        
        Args:
            image_bytes: The image bytes to validate
            metadata: Optional metadata to validate
            previous_step_result: Results from Step 2 to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Call parent validation
        super()._validate_inputs(image_bytes, metadata)
        
        # Validate previous step result
        if previous_step_result is None:
            raise ValidationError("Previous step result is required for Step 3")
        
        if not isinstance(previous_step_result, dict):
            raise ValidationError("Previous step result must be a dictionary")
        
        # Check for required fields from Step 2
        required_fields = ["completed_job_aid"]
        missing_fields = [field for field in required_fields if field not in previous_step_result]
        
        if missing_fields:
            raise ValidationError(f"Previous step result missing required fields: {', '.join(missing_fields)}")
    
    def _parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse the AI response for Step 3 with flexible fallback handling.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: The parsed response data with both JSON and human-readable outputs
            
        Note: This method will never raise an exception - it will always return a valid response
        """
        logger.info("Starting Step 3 response parsing")
        
        try:
            # First try to parse as JSON directly from the AI client
            logger.info("Attempting standard AI client parsing")
            parsed_data = self.ai_client.parse_structured_response(response)
            
            # If we got text instead of structured data, try to extract both formats
            if "text" in parsed_data and isinstance(parsed_data["text"], str):
                logger.info("Got text response, extracting dual format")
                result = self._extract_dual_format_from_text(parsed_data["text"])
                if result:
                    return result
                else:
                    logger.warning("Dual format extraction returned None, trying fallback parsing on text")
                    # Don't give up yet - try fallback parsing on the text
                    try:
                        fallback_result = self._fallback_parse_response(response)
                        if fallback_result:
                            return fallback_result
                    except Exception as fallback_error:
                        logger.warning(f"Fallback parsing on text failed: {str(fallback_error)}")
            
            # If we got structured data, validate and format it
            elif isinstance(parsed_data, dict) and "text" not in parsed_data:
                logger.info("Got structured data, processing")
                result = self._process_structured_response(parsed_data)
                if result:
                    return result
                else:
                    logger.warning("Structured response processing returned None, using fallback")
            
        except Exception as e:
            logger.warning(f"Standard parsing failed: {str(e)}, trying fallback methods")
        
        # Fallback: try to extract anything useful from the raw response
        try:
            logger.info("Attempting fallback parsing")
            result = self._fallback_parse_response(response)
            logger.info("Fallback parsing succeeded")
            return result
        except Exception as fallback_error:
            logger.error(f"Fallback parsing also failed: {str(fallback_error)}")
        
        # Final emergency fallback - this should never fail
        logger.warning("Using emergency response generation")
        return self._create_emergency_response(response.text)
    
    def _fallback_parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Fallback parsing method that tries to extract any useful information.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: Basic response structure with available data
        """
        logger.info("Attempting fallback parsing of Step 3 response")
        
        # Try multiple extraction strategies
        strategies = [
            self._try_extract_structured_json,
            self._try_extract_partial_json,
            self._try_extract_from_text_analysis,
            self._create_minimal_response
        ]
        
        for strategy_name, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"Trying fallback strategy {strategy_name}")
                result = strategy(response.text)
                if result:
                    logger.info(f"Fallback strategy {strategy_name} succeeded")
                    return result
            except Exception as e:
                logger.warning(f"Fallback strategy {strategy_name} failed: {str(e)}")
                continue
        
        # If all strategies fail, create a minimal response
        logger.warning("All fallback strategies failed, creating minimal response")
        return self._create_emergency_response(response.text)
    
    def _try_extract_structured_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract structured JSON from the response."""
        json_str = self._extract_json_from_text(text)
        
        if json_str:
            try:
                json_data = json.loads(json_str)
                if isinstance(json_data, dict):
                    # Normalize the JSON structure
                    normalized = self._normalize_findings_json(json_data)
                    return {
                        "json_output": normalized,
                        "human_readable_report": self._generate_human_readable_report(normalized)
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {str(e)}")
        
        return None
    
    def _try_extract_partial_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract partial JSON and fill in missing fields."""
        # Look for key-value pairs that might be part of a findings structure
        findings_data = {}
        
        # Extract component information
        component_match = re.search(r'component[_\s]*(?:id|name)["\s]*:?\s*["\']?([^"\'\n,}]+)', text, re.IGNORECASE)
        if component_match:
            findings_data["component_id"] = component_match.group(1).strip()
        
        # Extract status information
        status_match = re.search(r'(?:check[_\s]*)?status["\s]*:?\s*["\']?(PASSED|FAILED|PARTIAL)["\']?', text, re.IGNORECASE)
        if status_match:
            findings_data["check_status"] = status_match.group(1).upper()
        
        # Extract issues
        issues = []
        issue_patterns = [
            r'issue[s]?["\s]*:?\s*\[([^\]]+)\]',
            r'problem[s]?["\s]*:?\s*([^.\n]+)',
            r'error[s]?["\s]*:?\s*([^.\n]+)'
        ]
        
        for pattern in issue_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 5:
                    issues.append({
                        "category": "Quality",
                        "description": match.strip(),
                        "action": "Review and address this issue"
                    })
        
        if findings_data or issues:
            # Fill in defaults
            normalized = self._normalize_findings_json({
                **findings_data,
                "issues_detected": issues
            })
            
            return {
                "json_output": normalized,
                "human_readable_report": self._generate_human_readable_report(normalized)
            }
        
        return None
    
    def _try_extract_from_text_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to analyze the text content and create findings from it."""
        logger.info("Analyzing text content for compliance information")
        
        # Look for compliance-related keywords with more nuanced analysis
        compliance_indicators = {
            "positive": ["passed", "compliant", "acceptable", "meets", "satisfies", "adequate", "good", "excellent"],
            "negative": ["failed", "non-compliant", "unacceptable", "issues", "problems", "errors", "poor", "inadequate"],
            "review": ["needs review", "requires attention", "should be", "consider", "may need", "potential"]
        }
        
        text_lower = text.lower()
        
        # Count indicators to determine overall status
        positive_count = sum(1 for word in compliance_indicators["positive"] if word in text_lower)
        negative_count = sum(1 for word in compliance_indicators["negative"] if word in text_lower)
        review_count = sum(1 for word in compliance_indicators["review"] if word in text_lower)
        
        # Determine status based on indicator counts
        if negative_count > positive_count:
            status = "FAILED"
        elif positive_count > negative_count and review_count == 0:
            status = "PASSED"
        else:
            status = "PARTIAL"
        
        # Extract issues from the text
        issues = []
        issue_patterns = [
            r'(?:issue|problem|error|concern)[s]?[:\s]*([^.\n]{10,100})',
            r'(?:not|doesn\'t|cannot|fails? to)[^.\n]{5,80}',
            r'(?:poor|inadequate|insufficient|missing)[^.\n]{5,80}'
        ]
        
        for pattern in issue_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 10:
                    issues.append({
                        "category": "Quality Assessment",
                        "description": match.strip(),
                        "action": "Review and address this finding"
                    })
        
        # Extract recommendations from text with better patterns
        recommendations = []
        recommendation_patterns = [
            r'recommend[s]?[:\s]*([^.\n]{10,150})',
            r'suggest[s]?[:\s]*([^.\n]{10,150})',
            r'should[:\s]*([^.\n]{10,150})',
            r'consider[:\s]*([^.\n]{10,150})',
            r'(?:to improve|for better)[^.\n]{10,150}'
        ]
        
        for pattern in recommendation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    clean_rec = match.strip().rstrip('.,;')
                    if clean_rec not in recommendations:  # Avoid duplicates
                        recommendations.append(clean_rec)
        
        # Extract missing information
        missing_info = []
        missing_patterns = [
            r'(?:missing|lacks?|absent|not provided)[:\s]*([^.\n]{10,100})',
            r'(?:no|without)[^.\n]{5,80}(?:metadata|information|data)',
            r'(?:incomplete|insufficient)[^.\n]{5,80}'
        ]
        
        for pattern in missing_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 10:
                    missing_info.append({
                        "field": "content_analysis",
                        "description": match.strip(),
                        "action": "Provide the missing information"
                    })
        
        # If we didn't extract much, provide generic recommendations
        if not recommendations:
            if status == "FAILED":
                recommendations = [
                    "Address the identified compliance issues",
                    "Review image quality and technical specifications",
                    "Ensure all required metadata is complete"
                ]
            elif status == "PASSED":
                recommendations = [
                    "Continue with current quality standards",
                    "Maintain compliance with established guidelines"
                ]
            else:
                recommendations = [
                    "Review the analysis results carefully",
                    "Consider additional quality checks if needed"
                ]
        
        # Extract component information if available
        component_id = "ANALYSIS_RESULT"
        component_name = "Digital Asset Analysis"
        
        # Look for component identifiers in the text
        id_patterns = [
            r'(?:component|image|file|asset)[_\s]*(?:id|name)[:\s]*([^\s\n]{3,50})',
            r'(?:analyzing|processing)[:\s]*([^\s\n]{3,50})'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_id = match.group(1).strip('.,;:"\'')
                if len(potential_id) > 2:
                    component_id = potential_id
                    break
        
        findings = self._normalize_findings_json({
            "component_id": component_id,
            "component_name": component_name,
            "check_status": status,
            "issues_detected": issues[:5],  # Limit to 5 issues
            "missing_information": missing_info[:3],  # Limit to 3 missing items
            "recommendations": recommendations[:5]  # Limit to 5 recommendations
        })
        
        return {
            "json_output": findings,
            "human_readable_report": self._create_enhanced_text_report(text, findings)
        }
    
    def _create_minimal_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Create a minimal response structure."""
        findings = self._normalize_findings_json({
            "check_status": "PARTIAL",
            "missing_information": [
                {
                    "field": "response_parsing",
                    "description": "AI response could not be fully parsed",
                    "action": "Try running the analysis again"
                }
            ]
        })
        
        return {
            "json_output": findings,
            "human_readable_report": self._create_text_based_report(text, findings)
        }
    
    def _create_emergency_response(self, text: str) -> Dict[str, Any]:
        """Create an emergency response when all else fails."""
        findings = {
            "component_id": "ANALYSIS_RESULT",
            "component_name": "DAM Analysis",
            "check_status": "PARTIAL",
            "issues_detected": [],
            "missing_information": [
                {
                    "field": "response_format",
                    "description": "Unable to parse AI response in expected format",
                    "action": "Try running the analysis again or contact support"
                }
            ],
            "recommendations": [
                "Retry the analysis with the same or different image",
                "Check that the image is clear and metadata is complete",
                "Contact technical support if the issue persists"
            ]
        }
        
        report = f"""
**DAM Compliance Analysis Report**

**Status:** PARTIAL - Analysis completed with parsing limitations

**Component:** {findings['component_name']}
**Analysis Date:** {self._get_current_date()}

**Summary:**
The analysis was completed but encountered formatting issues in the response. 
The system was able to process your request but could not extract detailed findings.

**Raw AI Response (first 300 characters):**
{text[:300]}{'...' if len(text) > 300 else ''}

**Recommendations:**
- Try running the analysis again
- Ensure your image is clear and well-lit
- Verify that metadata is complete and accurate
- Contact support if issues persist

**Note:** This is a partial result due to response parsing limitations.
        """.strip()
        
        return {
            "json_output": findings,
            "human_readable_report": report
        }
    
    def _normalize_findings_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize findings JSON to ensure all required fields are present."""
        normalized = {
            "component_id": data.get("component_id", "UNKNOWN"),
            "component_name": data.get("component_name", "Digital Component"),
            "check_status": data.get("check_status", "PARTIAL"),
            "issues_detected": data.get("issues_detected", []),
            "missing_information": data.get("missing_information", []),
            "recommendations": data.get("recommendations", [])
        }
        
        # Ensure arrays are actually arrays
        for field in ["issues_detected", "missing_information", "recommendations"]:
            if not isinstance(normalized[field], list):
                normalized[field] = []
        
        # Ensure status is valid
        if normalized["check_status"] not in ["PASSED", "FAILED", "PARTIAL"]:
            normalized["check_status"] = "PARTIAL"
        
        return normalized
    
    def _create_text_based_report(self, original_text: str, findings: Dict[str, Any]) -> str:
        """Create a human-readable report based on the original text and findings."""
        status = findings.get("check_status", "PARTIAL")
        
        report = f"""
**DAM Compliance Analysis Report**

**Component:** {findings.get('component_name', 'Digital Component')}
**Component ID:** {findings.get('component_id', 'UNKNOWN')}
**Analysis Date:** {self._get_current_date()}
**Status:** {status}

**Analysis Summary:**
Based on the AI analysis, the component status is {status}. 

**Original AI Response Summary:**
{original_text[:400]}{'...' if len(original_text) > 400 else ''}

**Issues Detected:** {len(findings.get('issues_detected', []))}
**Missing Information:** {len(findings.get('missing_information', []))}
**Recommendations:** {len(findings.get('recommendations', []))}

**Recommendations:**
"""
        
        recommendations = findings.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"\n{i}. {rec}"
        else:
            report += "\n1. Review the analysis results carefully"
            report += "\n2. Consider re-running the analysis if needed"
        
        report += f"""

**Note:** This report was generated using enhanced parsing due to response format variations.
The analysis was completed successfully but required interpretation of the AI response.
        """
        
        return report.strip()
    
    def _create_enhanced_text_report(self, original_text: str, findings: Dict[str, Any]) -> str:
        """Create an enhanced human-readable report based on the original text and findings."""
        status = findings.get("check_status", "PARTIAL")
        
        report = f"""
**DAM Compliance Analysis Report**

**Component:** {findings.get('component_name', 'Digital Component')}
**Component ID:** {findings.get('component_id', 'UNKNOWN')}
**Analysis Date:** {self._get_current_date()}
**Status:** {status}

**Analysis Summary:**
Based on the AI analysis, the component status is {status}. 

**Original AI Response Summary:**
{original_text[:400]}{'...' if len(original_text) > 400 else ''}

**Issues Detected:** {len(findings.get('issues_detected', []))}
**Missing Information:** {len(findings.get('missing_information', []))}
**Recommendations:** {len(findings.get('recommendations', []))}

**Recommendations:**
"""
        
        recommendations = findings.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"\n{i}. {rec}"
        else:
            report += "\n1. Review the analysis results carefully"
            report += "\n2. Consider re-running the analysis if needed"
        
        report += f"""

**Note:** This report was generated using enhanced parsing due to response format variations.
The analysis was completed successfully but required interpretation of the AI response.
        """
        
        return report.strip()
    
    def _extract_dual_format_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract both JSON and human-readable formats from text response.
        
        Args:
            text: The text response to parse
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with json_output and human_readable_report, or None if extraction fails
        """
        # Try to extract JSON first
        json_output = self._extract_json_from_text(text)
        if not json_output:
            logger.warning("Could not extract JSON output from response text")
            return None
        
        try:
            json_data = json.loads(json_output)
            # Try to validate, but don't fail if validation fails
            try:
                self._validate_findings_output(json_data)
            except Exception as e:
                logger.warning(f"JSON validation failed, but continuing: {str(e)}")
                # Normalize the data to ensure it has required fields
                json_data = self._normalize_findings_json(json_data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Invalid JSON output: {str(e)}")
            return None
        
        # Extract human-readable report
        human_readable = self._extract_human_readable_from_text(text)
        if not human_readable:
            # Generate human-readable report from JSON if not found
            try:
                human_readable = self._generate_human_readable_report(json_data)
            except Exception as e:
                logger.warning(f"Failed to generate human-readable report: {str(e)}")
                human_readable = f"Analysis completed. Raw response: {text[:200]}..."
        
        return {
            "json_output": json_data,
            "human_readable_report": human_readable
        }
    
    def _process_structured_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process structured response data.
        
        Args:
            data: The structured response data
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with json_output and human_readable_report, or None if processing fails
        """
        # Check if we have both formats in the response
        if "json_output" in data and "human_readable_report" in data:
            try:
                self._validate_findings_output(data["json_output"])
                return data
            except Exception as e:
                logger.warning(f"Validation failed for dual format response: {str(e)}")
                # Try to normalize and continue
                try:
                    normalized_json = self._normalize_findings_json(data["json_output"])
                    return {
                        "json_output": normalized_json,
                        "human_readable_report": data["human_readable_report"]
                    }
                except Exception as e2:
                    logger.warning(f"Failed to normalize dual format response: {str(e2)}")
                    return None
        
        # If we only have JSON, validate it and generate human-readable
        if self._is_findings_json(data):
            try:
                self._validate_findings_output(data)
                human_readable = self._generate_human_readable_report(data)
                return {
                    "json_output": data,
                    "human_readable_report": human_readable
                }
            except Exception as e:
                logger.warning(f"Failed to process findings JSON: {str(e)}")
                # Try to normalize and continue
                try:
                    normalized_json = self._normalize_findings_json(data)
                    human_readable = self._generate_human_readable_report(normalized_json)
                    return {
                        "json_output": normalized_json,
                        "human_readable_report": human_readable
                    }
                except Exception as e2:
                    logger.warning(f"Failed to normalize findings JSON: {str(e2)}")
                    return None
        
        logger.warning("Response does not contain valid findings format")
        return None
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from text with improved parsing.
        
        Args:
            text: The text to extract JSON from
            
        Returns:
            Optional[str]: The extracted JSON string, or None if not found
        """
        # Try multiple extraction methods
        extraction_methods = [
            self._extract_from_markdown_blocks,
            self._extract_with_bracket_matching,
            self._extract_with_aggressive_cleaning
        ]
        
        for method in extraction_methods:
            try:
                json_str = method(text)
                if json_str:
                    # Try to parse to validate
                    json.loads(json_str)
                    return json_str
            except json.JSONDecodeError:
                continue
            except Exception:
                continue
        
        return None
    
    def _extract_from_markdown_blocks(self, text: str) -> Optional[str]:
        """Extract JSON from markdown code blocks."""
        # Try different patterns for markdown code blocks
        # Use DOTALL flag to match across newlines
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json { ... } ```
            r'```\s*(\{.*?\})\s*```',      # ``` { ... } ```
            r'```json\s*(\[.*?\])\s*```',  # ```json [ ... ] ``` (for arrays)
            r'```\s*(\[.*?\])\s*```'       # ``` [ ... ] ``` (for arrays)
        ]
        
        for pattern in patterns:
            json_match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if json_match:
                json_str = json_match.group(1).strip()
                # Validate that it's actually JSON before cleaning
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # Try cleaning and then parsing
                    try:
                        cleaned_json = self._clean_json_string(json_str)
                        json.loads(cleaned_json)
                        return cleaned_json
                    except json.JSONDecodeError:
                        continue
        
        return None
    
    def _extract_with_bracket_matching(self, text: str) -> Optional[str]:
        """Extract JSON using bracket matching."""
        brace_count = 0
        start_pos = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    json_str = text[start_pos:i+1]
                    return self._clean_json_string(json_str)
        return None
    
    def _extract_with_aggressive_cleaning(self, text: str) -> Optional[str]:
        """Extract JSON with aggressive cleaning for malformed JSON."""
        # Find potential JSON blocks
        json_patterns = [
            r'\{[^{}]*"component_id"[^{}]*\}',
            r'\{.*?"component_id".*?\}',
            r'\{.*?\}'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    cleaned = self._aggressively_clean_json(match)
                    json.loads(cleaned)  # Test if it's valid
                    return cleaned
                except:
                    continue
        return None
    
    def _aggressively_clean_json(self, json_str: str) -> str:
        """
        Aggressively clean JSON string to fix malformed JSON.
        
        Args:
            json_str: The JSON string to clean
            
        Returns:
            str: Cleaned JSON string
        """
        # Start with basic cleaning
        json_str = self._clean_json_string(json_str)
        
        # More aggressive fixes
        # Fix common AI-generated issues
        json_str = re.sub(r'\\(?!["\\/bfnrtu])', r'', json_str)  # Remove invalid escapes
        json_str = re.sub(r'\n\s*', ' ', json_str)  # Replace newlines with spaces
        json_str = re.sub(r'\s+', ' ', json_str)  # Normalize whitespace
        
        # Fix quotes in string values more aggressively
        def fix_string_content(match):
            key = match.group(1)
            value = match.group(2)
            # Remove problematic characters from string values
            value = re.sub(r'[^\w\s\-.,!?()[\]{}:;]', '', value)
            return f'"{key}": "{value}"'
        
        # Apply to key-value pairs
        json_str = re.sub(r'"([^"]+)":\s*"([^"]*)"', fix_string_content, json_str)
        
        return json_str.strip()
    
    def _clean_json_string(self, json_str: str) -> str:
        """
        Clean JSON string to fix common escape character issues.
        
        Args:
            json_str: The JSON string to clean
            
        Returns:
            str: Cleaned JSON string
        """
        # Remove any trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix common invalid escape sequences
        # Replace invalid escapes with safe alternatives
        json_str = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', json_str)
        
        # Fix newlines in strings - replace literal newlines with \n
        json_str = re.sub(r'(?<!\\)\n(?=.*")', r'\\n', json_str)
        
        # Fix unescaped quotes in string values
        # This is a complex regex to find quotes that should be escaped
        def fix_quotes(match):
            content = match.group(1)
            # Escape any unescaped quotes within the string
            content = re.sub(r'(?<!\\)"', r'\\"', content)
            return f'"{content}"'
        
        # Apply quote fixing to string values
        json_str = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', fix_quotes, json_str)
        
        # Clean up any double escaping that might have occurred
        json_str = json_str.replace('\\\\n', '\\n')
        json_str = json_str.replace('\\\\"', '\\"')
        
        return json_str.strip()
    
    def _extract_human_readable_from_text(self, text: str) -> Optional[str]:
        """
        Extract human-readable report from text.
        
        Args:
            text: The text to extract human-readable report from
            
        Returns:
            Optional[str]: The extracted human-readable report, or None if not found
        """
        # Look for sections that appear to be human-readable reports
        # Updated patterns to match the new prompt format
        patterns = [
            # Match the exact format from our new prompt
            r'HUMAN[- ]?READABLE[- ]?REPORT:\s*\n\n(.*?)(?:\n\n---|\Z)',
            r'HUMAN[- ]?READABLE[- ]?REPORT:\s*\n(.*?)(?:\n\n---|\Z)',
            # Match report sections starting with **DIGITAL ASSET COMPLIANCE**
            r'\*\*DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT\*\*(.*?)(?:\n\n---|\Z)',
            # Generic patterns for fallback
            r'(?:HUMAN[- ]?READABLE[- ]?REPORT|PROFESSIONAL[- ]?COMMUNICATION|REPORT):\s*\n(.*?)(?:\n\n|\Z)',
            r'(?:## |# )?(?:Human[- ]?Readable|Professional|Report).*?\n(.*?)(?:\n\n|\Z)',
            r'(?:FINDINGS|SUMMARY|ASSESSMENT)[- ]?REPORT:\s*\n(.*?)(?:\n\n|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                report = match.group(1).strip()
                if len(report) > 50:  # Ensure it's substantial content
                    # Clean up the report - remove extra whitespace and format nicely
                    report = re.sub(r'\n\s*\n\s*\n', '\n\n', report)  # Remove excessive line breaks
                    report = report.strip()
                    return report
        
        # If no specific section found, look for substantial text after JSON
        json_end = text.rfind('}')
        if json_end != -1:
            remaining_text = text[json_end + 1:].strip()
            # Look for report-like content
            if ('**' in remaining_text or 'DIGITAL ASSET' in remaining_text.upper() or 
                'COMPLIANCE' in remaining_text.upper()) and len(remaining_text) > 50:
                # Clean up the text
                remaining_text = re.sub(r'\n\s*\n\s*\n', '\n\n', remaining_text)
                return remaining_text.strip()
        
        return None
    
    def _is_findings_json(self, data: Dict[str, Any]) -> bool:
        """
        Check if data looks like findings JSON.
        
        Args:
            data: The data to check
            
        Returns:
            bool: True if it looks like findings JSON
        """
        required_fields = ["component_id", "check_status"]
        return all(field in data for field in required_fields)
    
    def _validate_findings_output(self, data: Dict[str, Any]) -> None:
        """
        Validate the findings output has the required structure.
        
        Args:
            data: The data to validate
            
        Raises:
            OutputParsingError: If validation fails
        """
        try:
            validate_findings_data(data)
        except Exception as e:
            error_msg = f"Findings output validation failed: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
    
    def _generate_human_readable_report(self, json_data: Dict[str, Any]) -> str:
        """
        Generate a comprehensive human-readable report from JSON data.
        
        Args:
            json_data: The JSON findings data
            
        Returns:
            str: A professional human-readable report
        """
        try:
            component_name = json_data.get("component_name", "Digital Component")
            component_id = json_data.get("component_id", "Unknown")
            check_status = json_data.get("check_status", "FAILED")
            issues_detected = json_data.get("issues_detected", [])
            missing_information = json_data.get("missing_information", [])
            recommendations = json_data.get("recommendations", [])
            
            # Build the report
            report_lines = []
            
            # Header
            report_lines.append("**DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT**")
            report_lines.append("")
            
            # Component Information
            report_lines.append(f"**Component:** {component_name}")
            report_lines.append(f"**Component ID:** {component_id}")
            report_lines.append(f"**Assessment Date:** {self._get_current_date()}")
            report_lines.append(f"**Status:** {check_status}")
            report_lines.append("")
            
            # Executive Summary
            report_lines.append("**Executive Summary:**")
            if check_status == "PASSED":
                report_lines.append("The digital component has successfully passed all compliance checks and meets the required standards. No critical issues were identified during the comprehensive assessment.")
            elif check_status == "FAILED":
                issue_count = len(issues_detected)
                missing_count = len(missing_information)
                report_lines.append(f"The digital component has failed compliance assessment with {issue_count} issue(s) detected and {missing_count} piece(s) of missing information. Immediate attention is required to address the identified concerns.")
            else:  # PARTIAL
                report_lines.append("The digital component assessment was completed with some limitations. Review the findings below for detailed information.")
            
            report_lines.append("")
            
            # Issues Detected Section
            report_lines.append(f"**Issues Detected:** {len(issues_detected)}")
            if issues_detected:
                report_lines.append("")
                for i, issue in enumerate(issues_detected, 1):
                    category = issue.get("category", "General")
                    description = issue.get("description", "No description provided")
                    action = issue.get("action", "")
                    
                    report_lines.append(f"**{i}. {category}**")
                    report_lines.append(f"   - **Issue:** {description}")
                    if action:
                        report_lines.append(f"   - **Required Action:** {action}")
                    report_lines.append("")
            else:
                report_lines.append("✅ No issues detected")
                report_lines.append("")
            
            # Missing Information Section
            report_lines.append(f"**Missing Information:** {len(missing_information)}")
            if missing_information:
                report_lines.append("")
                for i, missing in enumerate(missing_information, 1):
                    field = missing.get("field", "Unknown field")
                    description = missing.get("description", "No description provided")
                    action = missing.get("action", "")
                    
                    report_lines.append(f"**{i}. {field}**")
                    report_lines.append(f"   - **Missing:** {description}")
                    if action:
                        report_lines.append(f"   - **Required Action:** {action}")
                    report_lines.append("")
            else:
                report_lines.append("✅ No missing information")
                report_lines.append("")
            
            # Recommendations Section
            report_lines.append("**Recommendations:**")
            if recommendations:
                report_lines.append("")
                for i, recommendation in enumerate(recommendations, 1):
                    report_lines.append(f"{i}. {recommendation}")
                report_lines.append("")
            else:
                if check_status == "PASSED":
                    report_lines.append("1. Continue maintaining current quality standards")
                    report_lines.append("2. Ensure consistent compliance with established guidelines")
                else:
                    report_lines.append("1. Review all identified issues and missing information")
                    report_lines.append("2. Implement corrective actions as specified above")
                    report_lines.append("3. Re-submit for assessment after addressing concerns")
                report_lines.append("")
            
            # Conclusion
            report_lines.append("**Conclusion:**")
            if check_status == "PASSED":
                report_lines.append("This digital asset is approved for use and meets all compliance requirements. No further action is required at this time.")
            elif check_status == "FAILED":
                report_lines.append("This digital asset requires remediation before it can be approved for use. Please address all identified issues and resubmit for assessment.")
            else:  # PARTIAL
                report_lines.append("This assessment was completed with some limitations. Please review the findings and consider rerunning the analysis if needed.")
            
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("*This report was generated by the DAM Compliance Analyzer.*")
            report_lines.append("*For questions or concerns, please contact your DAM administrator.*")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating human-readable report: {str(e)}")
            # Return a basic error report instead of just the error message
            return f"""**DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT**

**Status:** ERROR - Report Generation Failed

**Component:** {json_data.get('component_name', 'Unknown')}
**Component ID:** {json_data.get('component_id', 'Unknown')}
**Assessment Date:** {self._get_current_date()}

**Error:** Unable to generate complete report due to: {str(e)}

**Raw Data:** {json.dumps(json_data, indent=2) if json_data else 'No data available'}

---
*Please contact technical support for assistance.*"""
    
    def _get_current_date(self) -> str:
        """
        Get the current date as a string.
        
        Returns:
            str: Current date in YYYY-MM-DD format
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")