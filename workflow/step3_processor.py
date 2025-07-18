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
        Parse the AI response for Step 3.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: The parsed response data with both JSON and human-readable outputs
            
        Raises:
            OutputParsingError: If parsing fails
        """
        try:
            # First try to parse as JSON directly from the AI client
            parsed_data = self.ai_client.parse_structured_response(response)
            
            # If we got text instead of structured data, try to extract both formats
            if "text" in parsed_data and isinstance(parsed_data["text"], str):
                return self._extract_dual_format_from_text(parsed_data["text"])
            
            # If we got structured data, validate and format it
            return self._process_structured_response(parsed_data)
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Step 3 response as JSON: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
            
        except Exception as e:
            error_msg = f"Error parsing Step 3 response: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
    
    def _extract_dual_format_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract both JSON and human-readable formats from text response.
        
        Args:
            text: The text response to parse
            
        Returns:
            Dict[str, Any]: Dictionary with json_output and human_readable_report
            
        Raises:
            OutputParsingError: If extraction fails
        """
        # Try to extract JSON first
        json_output = self._extract_json_from_text(text)
        if not json_output:
            raise OutputParsingError("Could not extract JSON output from response")
        
        try:
            json_data = json.loads(json_output)
            self._validate_findings_output(json_data)
        except (json.JSONDecodeError, Exception) as e:
            raise OutputParsingError(f"Invalid JSON output: {str(e)}")
        
        # Extract human-readable report
        human_readable = self._extract_human_readable_from_text(text)
        if not human_readable:
            # Generate human-readable report from JSON if not found
            human_readable = self._generate_human_readable_report(json_data)
        
        return {
            "json_output": json_data,
            "human_readable_report": human_readable
        }
    
    def _process_structured_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process structured response data.
        
        Args:
            data: The structured response data
            
        Returns:
            Dict[str, Any]: Dictionary with json_output and human_readable_report
            
        Raises:
            OutputParsingError: If processing fails
        """
        # Check if we have both formats in the response
        if "json_output" in data and "human_readable_report" in data:
            self._validate_findings_output(data["json_output"])
            return data
        
        # If we only have JSON, validate it and generate human-readable
        if self._is_findings_json(data):
            self._validate_findings_output(data)
            human_readable = self._generate_human_readable_report(data)
            return {
                "json_output": data,
                "human_readable_report": human_readable
            }
        
        raise OutputParsingError("Response does not contain valid findings format")
    
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
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return self._clean_json_string(json_match.group(1).strip())
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
        # This could be after "HUMAN-READABLE REPORT:" or similar headers
        patterns = [
            r'(?:HUMAN[- ]?READABLE[- ]?REPORT|PROFESSIONAL[- ]?COMMUNICATION|REPORT):\s*\n(.*?)(?:\n\n|\Z)',
            r'(?:## |# )?(?:Human[- ]?Readable|Professional|Report).*?\n(.*?)(?:\n\n|\Z)',
            r'(?:FINDINGS|SUMMARY|ASSESSMENT)[- ]?REPORT:\s*\n(.*?)(?:\n\n|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                report = match.group(1).strip()
                if len(report) > 50:  # Ensure it's substantial content
                    return report
        
        # If no specific section found, look for substantial text after JSON
        json_end = text.rfind('}')
        if json_end != -1:
            remaining_text = text[json_end + 1:].strip()
            if len(remaining_text) > 50:  # Substantial content (lowered threshold)
                return remaining_text
        
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
        Generate a human-readable report from JSON data.
        
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
            report_lines.append(f"DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT")
            report_lines.append("=" * 50)
            report_lines.append("")
            
            # Component Information
            report_lines.append(f"Component Name: {component_name}")
            report_lines.append(f"Component ID: {component_id}")
            report_lines.append(f"Assessment Date: {self._get_current_date()}")
            report_lines.append("")
            
            # Overall Status
            status_text = "PASSED" if check_status == "PASSED" else "FAILED"
            report_lines.append(f"OVERALL COMPLIANCE STATUS: {status_text}")
            report_lines.append("")
            
            if check_status == "PASSED":
                report_lines.append("The digital component has successfully passed all compliance checks.")
                report_lines.append("No critical issues were identified during the assessment.")
            else:
                report_lines.append("The digital component has failed one or more compliance checks.")
                report_lines.append("Please review the issues and recommendations below.")
            
            report_lines.append("")
            
            # Issues Detected
            if issues_detected:
                report_lines.append("ISSUES DETECTED:")
                report_lines.append("-" * 20)
                for i, issue in enumerate(issues_detected, 1):
                    category = issue.get("category", "General")
                    description = issue.get("description", "No description provided")
                    action = issue.get("action", "")
                    
                    report_lines.append(f"{i}. {category}: {description}")
                    if action:
                        report_lines.append(f"   Action Required: {action}")
                    report_lines.append("")
            
            # Missing Information
            if missing_information:
                report_lines.append("MISSING INFORMATION:")
                report_lines.append("-" * 20)
                for i, missing in enumerate(missing_information, 1):
                    field = missing.get("field", "Unknown field")
                    description = missing.get("description", "No description provided")
                    action = missing.get("action", "")
                    
                    report_lines.append(f"{i}. {field}: {description}")
                    if action:
                        report_lines.append(f"   Action Required: {action}")
                    report_lines.append("")
            
            # Recommendations
            if recommendations:
                report_lines.append("RECOMMENDATIONS:")
                report_lines.append("-" * 15)
                for i, recommendation in enumerate(recommendations, 1):
                    report_lines.append(f"{i}. {recommendation}")
                report_lines.append("")
            
            # Footer
            report_lines.append("=" * 50)
            report_lines.append("This report was generated by the DAM Compliance Analyzer.")
            report_lines.append("For questions or concerns, please contact your DAM administrator.")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating human-readable report: {str(e)}")
            return f"Error generating human-readable report: {str(e)}"
    
    def _get_current_date(self) -> str:
        """
        Get the current date as a string.
        
        Returns:
            str: Current date in YYYY-MM-DD format
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")