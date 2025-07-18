"""
Step 2: Job Aid Assessment Processor

This module implements the processor for Step 2 of the DAM Compliance Analyzer
workflow. It handles the detailed job aid assessment using the complete job aid schema.
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
from prompts import format_step2_prompt
from schemas import get_job_aid_schema, validate_job_aid_data, create_empty_job_aid
from services import AIResponse

logger = logging.getLogger(__name__)


class Step2Processor(BaseProcessor):
    """
    Processor for Step 2: Job Aid Assessment.
    
    This processor handles the detailed job aid assessment using the complete
    job aid schema, analyzing the image against each field in the job aid.
    """
    
    def _format_prompt(self, metadata: Optional[Dict[str, Any]] = None,
                      previous_step_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt for Step 2.
        
        Args:
            metadata: Optional metadata to include in the prompt
            previous_step_result: Results from Step 1
            
        Returns:
            str: The formatted prompt
        """
        job_aid_schema = get_job_aid_schema()
        return format_step2_prompt(job_aid_schema, previous_step_result, metadata)
    
    async def process(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                     previous_step_result: Optional[Dict[str, Any]] = None) -> ProcessorResult:
        """
        Process Step 2: Job Aid Assessment.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            previous_step_result: Results from Step 1
            
        Returns:
            ProcessorResult: The result of processing
            
        Raises:
            ProcessorError: If processing fails
        """
        try:
            # Validate inputs
            self._validate_inputs(image_bytes, metadata, previous_step_result)
            
            # Format prompt
            prompt = self._format_prompt(metadata, previous_step_result)
            
            # Send request to AI model
            logger.info("Sending Step 2 Job Aid Assessment request to AI model")
            response = await self._send_request(image_bytes, prompt)
            
            # Parse response
            parsed_data = self._parse_response(response)
            
            # Create result
            result = ProcessorResult(
                success=True,
                data=parsed_data,
                raw_response=response.text
            )
            
            logger.info("Step 2 Job Aid Assessment completed successfully")
            return result
            
        except ValidationError as e:
            error_msg = f"Step 2 validation error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except ProcessingError as e:
            error_msg = f"Step 2 processing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except OutputParsingError as e:
            error_msg = f"Step 2 output parsing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error in Step 2: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
    
    def _validate_inputs(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                        previous_step_result: Optional[Dict[str, Any]] = None) -> None:
        """
        Validate the inputs to the processor.
        
        Args:
            image_bytes: The image bytes to validate
            metadata: Optional metadata to validate
            previous_step_result: Results from Step 1 to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Call parent validation
        super()._validate_inputs(image_bytes, metadata)
        
        # Validate previous step result
        if previous_step_result is None:
            raise ValidationError("Previous step result is required for Step 2")
        
        if not isinstance(previous_step_result, dict):
            raise ValidationError("Previous step result must be a dictionary")
        
        # Check for required fields from Step 1
        required_fields = ["notes", "job_aid_assessment", "human_readable_section"]
        missing_fields = [field for field in required_fields if field not in previous_step_result]
        
        if missing_fields:
            raise ValidationError(f"Previous step result missing required fields: {', '.join(missing_fields)}")
    
    def _parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse the AI response for Step 2.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: The parsed response data with completed job aid assessment
            
        Raises:
            OutputParsingError: If parsing fails
        """
        try:
            # First try to parse as JSON directly from the AI client
            parsed_data = self.ai_client.parse_structured_response(response)
            
            # If we got text instead of structured data, try to extract JSON
            if "text" in parsed_data and isinstance(parsed_data["text"], str):
                # Try to extract JSON from the text
                json_match = self._extract_json_from_text(parsed_data["text"])
                if json_match:
                    parsed_data = json.loads(json_match)
            
            # Validate the parsed data has the required structure
            self._validate_job_aid_output(parsed_data)
            
            # Extract assessment summary
            assessment_summary = self._extract_assessment_summary(parsed_data)
            
            # Return the completed job aid with assessment summary
            return {
                "completed_job_aid": parsed_data,
                "assessment_summary": assessment_summary
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Step 2 response as JSON: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
            
        except Exception as e:
            error_msg = f"Error parsing Step 2 response: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from text.
        
        Args:
            text: The text to extract JSON from
            
        Returns:
            Optional[str]: The extracted JSON string, or None if not found
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find JSON directly
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return None
    
    def _validate_job_aid_output(self, data: Dict[str, Any]) -> None:
        """
        Validate the job aid output has the required structure.
        
        Args:
            data: The data to validate
            
        Raises:
            OutputParsingError: If validation fails
        """
        # First check if we have a valid structure at all
        if not data or not isinstance(data, dict):
            raise OutputParsingError("Job aid output must be a dictionary")
            
        try:
            # Check if the data has the digital_component_analysis key
            if "digital_component_analysis" not in data:
                # Check if this might be a direct component analysis object
                # Look for key fields that would indicate this is the inner object
                inner_object_keys = ["component_specifications", "component_qc", "overall_assessment"]
                if any(key in data for key in inner_object_keys):
                    # Create a wrapper with the expected structure
                    wrapped_data = {"digital_component_analysis": data}
                    validate_job_aid_data(wrapped_data)
                    return
                else:
                    # This is not a valid job aid structure
                    raise OutputParsingError("Job aid output missing 'digital_component_analysis' key and does not appear to be a valid inner object")
            
            # Validate against the schema
            validate_job_aid_data(data)
            
        except Exception as e:
            error_msg = f"Job aid validation failed: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
    
    def _extract_assessment_summary(self, job_aid_data: Dict[str, Any]) -> str:
        """
        Extract an assessment summary from job aid data.
        
        Args:
            job_aid_data: The completed job aid data
            
        Returns:
            str: A summary of the assessment
        """
        try:
            # Get the digital_component_analysis object
            if "digital_component_analysis" in job_aid_data:
                digital_component = job_aid_data["digital_component_analysis"]
            else:
                # If the AI returned just the inner object
                digital_component = job_aid_data
            
            # Get the overall assessment
            overall = digital_component.get("overall_assessment", {})
            
            status = overall.get("status", "NEEDS_REVIEW")
            summary = overall.get("summary", "")
            critical_issues = overall.get("critical_issues", [])
            recommendations = overall.get("recommendations", [])
            
            # Generate a summary if none provided
            if not summary:
                if status == "PASS":
                    summary = "The digital component meets all compliance requirements."
                elif status == "FAIL":
                    summary = "The digital component has compliance issues that need to be addressed."
                else:
                    summary = "The digital component requires further review."
            
            # Build the assessment summary
            result = f"Assessment Status: {status}\n\n{summary}"
            
            # Add critical issues if any
            if critical_issues:
                result += "\n\nCritical Issues:\n"
                for i, issue in enumerate(critical_issues, 1):
                    result += f"{i}. {issue}\n"
            
            # Add recommendations if any
            if recommendations:
                result += "\n\nRecommendations:\n"
                for i, rec in enumerate(recommendations, 1):
                    result += f"{i}. {rec}\n"
            
            return result
            
        except Exception as e:
            logger.warning(f"Error extracting assessment summary: {str(e)}")
            return "Assessment summary could not be generated due to an error."