"""
Base Processor for DAM Compliance Analyzer Workflow

This module defines the base processor class that all workflow step processors
will extend. It provides common functionality for processing requests and
handling errors.
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass

from services import GeminiClient, MultimodalRequest, AIResponse, GeminiAPIError

logger = logging.getLogger(__name__)


class ProcessorError(Exception):
    """Base exception for processor errors"""
    pass


class ValidationError(ProcessorError):
    """Exception for validation errors"""
    pass


class ProcessingError(ProcessorError):
    """Exception for processing errors"""
    pass


class OutputParsingError(ProcessorError):
    """Exception for output parsing errors"""
    pass


@dataclass
class ProcessorResult:
    """Base class for processor results"""
    success: bool
    data: Dict[str, Any]
    error_message: Optional[str] = None
    raw_response: Optional[str] = None


class BaseProcessor(ABC):
    """
    Base processor class for workflow steps.
    
    This abstract class defines the interface and common functionality
    for all workflow step processors.
    """
    
    def __init__(self, ai_client: GeminiClient):
        """
        Initialize the processor.
        
        Args:
            ai_client: The AI client to use for processing
        """
        self.ai_client = ai_client
    
    @abstractmethod
    async def process(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None, 
                     previous_step_result: Optional[Dict[str, Any]] = None) -> ProcessorResult:
        """
        Process the workflow step.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            previous_step_result: Optional result from the previous step
            
        Returns:
            ProcessorResult: The result of processing
            
        Raises:
            ProcessorError: If processing fails
        """
        pass
    
    @abstractmethod
    def _format_prompt(self, metadata: Optional[Dict[str, Any]] = None,
                      previous_step_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt for the AI model.
        
        Args:
            metadata: Optional metadata to include in the prompt
            previous_step_result: Optional result from the previous step
            
        Returns:
            str: The formatted prompt
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse the AI response into structured data.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: The parsed response data
            
        Raises:
            OutputParsingError: If parsing fails
        """
        pass
    
    def _validate_inputs(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None,
                        previous_step_result: Optional[Dict[str, Any]] = None) -> None:
        """
        Validate the inputs to the processor.
        
        Args:
            image_bytes: The image bytes to validate
            metadata: Optional metadata to validate
            previous_step_result: Optional previous step result to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not image_bytes:
            raise ValidationError("Image bytes cannot be empty")
        
        if metadata is not None and not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")
    
    async def _send_request(self, image_bytes: bytes, prompt: str) -> AIResponse:
        """
        Send a request to the AI model.
        
        Args:
            image_bytes: The image bytes to send
            prompt: The prompt to send
            
        Returns:
            AIResponse: The AI response
            
        Raises:
            ProcessingError: If the request fails
        """
        try:
            request = MultimodalRequest(
                image_bytes=image_bytes,
                text_prompt=prompt
            )
            
            response = await self.ai_client.process_multimodal_request(request)
            return response
            
        except GeminiAPIError as e:
            error_msg = f"AI request failed: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during AI request: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)