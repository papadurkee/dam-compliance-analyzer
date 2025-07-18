"""
Step 1: DAM Analysis Processor

This module implements the processor for Step 1 of the DAM Compliance Analyzer
workflow. It handles the initial analysis of the digital asset against
compliance criteria.
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
from prompts import format_step1_prompt
from services import AIResponse

logger = logging.getLogger(__name__)


class Step1Processor(BaseProcessor):
    """
    Processor for Step 1: DAM Analysis.
    
    This processor handles the initial analysis of the digital asset,
    generating notes, job aid assessment, human-readable section, and next steps.
    """
    
    def _format_prompt(self, metadata: Optional[Dict[str, Any]] = None,
                      previous_step_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt for Step 1.
        
        Args:
            metadata: Optional metadata to include in the prompt
            previous_step_result: Not used in Step 1
            
        Returns:
            str: The formatted prompt
        """
        return format_step1_prompt(metadata)
    
    async def process(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                     previous_step_result: Optional[Dict[str, Any]] = None) -> ProcessorResult:
        """
        Process Step 1: DAM Analysis.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            previous_step_result: Not used in Step 1
            
        Returns:
            ProcessorResult: The result of processing
            
        Raises:
            ProcessorError: If processing fails
        """
        try:
            # Validate inputs
            self._validate_inputs(image_bytes, metadata)
            
            # Format prompt
            prompt = self._format_prompt(metadata)
            
            # Send request to AI model
            logger.info("Sending Step 1 DAM Analysis request to AI model")
            response = await self._send_request(image_bytes, prompt)
            
            # Parse response
            parsed_data = self._parse_response(response)
            
            # Create result
            result = ProcessorResult(
                success=True,
                data=parsed_data,
                raw_response=response.text
            )
            
            logger.info("Step 1 DAM Analysis completed successfully")
            return result
            
        except ValidationError as e:
            error_msg = f"Step 1 validation error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except ProcessingError as e:
            error_msg = f"Step 1 processing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except OutputParsingError as e:
            error_msg = f"Step 1 output parsing error: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error in Step 1: {str(e)}"
            logger.error(error_msg)
            return ProcessorResult(success=False, data={}, error_message=error_msg)
    
    def _parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse the AI response for Step 1.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: The parsed response data with notes, job aid assessment,
                           human-readable section, and next steps
            
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
            
            # Validate the parsed data has the required fields
            self._validate_step1_output(parsed_data)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Step 1 response as JSON: {str(e)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
            
        except Exception as e:
            error_msg = f"Error parsing Step 1 response: {str(e)}"
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
    
    def _validate_step1_output(self, data: Dict[str, Any]) -> None:
        """
        Validate the Step 1 output has the required fields.
        
        Args:
            data: The data to validate
            
        Raises:
            OutputParsingError: If validation fails
        """
        required_fields = ["notes", "job_aid_assessment", "human_readable_section", "next_steps"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            error_msg = f"Step 1 output missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            raise OutputParsingError(error_msg)
        
        # Validate job_aid_assessment structure
        job_aid = data["job_aid_assessment"]
        if not isinstance(job_aid, dict):
            raise OutputParsingError("job_aid_assessment must be a dictionary")
        
        # Validate next_steps is a list
        if not isinstance(data["next_steps"], list):
            raise OutputParsingError("next_steps must be a list")