"""
Google Gemini API Client Integration

This module provides a wrapper for Google's Gemini API,
handling multimodal requests (image + text) with comprehensive error handling
and retry logic.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
import base64
from io import BytesIO
import json
import re

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import streamlit as st

logger = logging.getLogger(__name__)


@dataclass
class MultimodalRequest:
    """Data class for multimodal requests to Gemini API"""
    image_bytes: bytes
    text_prompt: str
    mime_type: str = "image/jpeg"
    generation_config: Optional[Dict[str, Any]] = None
    safety_settings: Optional[List[Dict[str, Any]]] = None


@dataclass
class AIResponse:
    """Data class for AI model responses"""
    text: str
    usage_metadata: Optional[Dict[str, Any]] = None
    safety_ratings: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None


class GeminiAPIError(Exception):
    """Custom exception for Gemini API related errors"""
    pass


class GeminiClient:
    """
    Google Gemini API client wrapper for multimodal requests.
    
    Provides multimodal request handling with comprehensive error handling,
    retry logic with exponential backoff, and response parsing.
    """
    
    def __init__(self):
        """Initialize the Gemini API client."""
        self.model_name = "gemini-2.0-flash-exp"
        self._model: Optional[genai.GenerativeModel] = None
        self._initialized = False
    
    async def initialize_client(self) -> None:
        """
        Initialize the Gemini API client with authentication.
        
        Raises:
            GeminiAPIError: If client initialization fails
        """
        try:
            # Get API key from Streamlit secrets
            if "gemini_api_key" not in st.secrets:
                raise GeminiAPIError(
                    "Gemini API key not found in Streamlit secrets. "
                    "Please configure 'gemini_api_key' in your secrets."
                )
            
            api_key = st.secrets["gemini_api_key"]
            
            # Configure the API
            genai.configure(api_key=api_key)
            
            # Initialize the generative model
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction="You are a professional Digital Asset Management (DAM) analyst with expertise in compliance assessment and quality control."
            )
            
            self._initialized = True
            logger.info(f"Successfully initialized Gemini API client with model: {self.model_name}")
            
        except Exception as e:
            error_msg = f"Failed to initialize Gemini API client: {str(e)}"
            logger.error(error_msg)
            raise GeminiAPIError(error_msg)
    
    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized before making requests"""
        if not self._initialized or not self._model:
            raise GeminiAPIError("Client not initialized. Call initialize_client() first.")
    
    def _create_image_data(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Create image data for multimodal requests.
        
        Args:
            image_bytes: Raw image bytes
            mime_type: MIME type of the image
            
        Returns:
            Dict: Image data for the request
        """
        try:
            # Convert bytes to base64 for Gemini API
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            return {
                "mime_type": mime_type,
                "data": image_b64
            }
            
        except Exception as e:
            error_msg = f"Failed to create image data: {str(e)}"
            logger.error(error_msg)
            raise GeminiAPIError(error_msg)
    
    def _get_default_generation_config(self) -> Dict[str, Any]:
        """Get default generation configuration"""
        return {
            "max_output_tokens": 8192,
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40
        }
    
    def _get_default_safety_settings(self) -> List[Dict[str, Any]]:
        """Get default safety settings"""
        return [
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT", 
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    
    def _create_test_image(self) -> bytes:
        """Create a simple test image for health checks"""
        try:
            from PIL import Image as PILImage
            import io
            
            # Create a simple 100x100 white image
            img = PILImage.new('RGB', (100, 100), color='white')
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            return img_bytes.getvalue()
            
        except Exception:
            # Fallback: return a minimal JPEG header (won't work but won't crash)
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'
    
    async def process_multimodal_request(
        self,
        request: MultimodalRequest,
        max_retries: int = 3
    ) -> AIResponse:
        """
        Process a multimodal request (image + text) with retry logic.
        
        Args:
            request: The multimodal request to process
            max_retries: Maximum number of retry attempts
            
        Returns:
            AIResponse: The processed response from the AI model
            
        Raises:
            GeminiAPIError: If the request fails after all retries
        """
        self._ensure_initialized()
        
        for attempt in range(max_retries + 1):
            try:
                # Create image data
                image_data = self._create_image_data(request.image_bytes, request.mime_type)
                
                # Prepare generation config
                generation_config = request.generation_config or self._get_default_generation_config()
                safety_settings = request.safety_settings or self._get_default_safety_settings()
                
                # Convert safety settings to Gemini format
                gemini_safety_settings = {}
                for setting in safety_settings:
                    category = getattr(HarmCategory, setting["category"], None)
                    threshold = getattr(HarmBlockThreshold, setting["threshold"], None)
                    if category and threshold:
                        gemini_safety_settings[category] = threshold
                
                # Create the content parts in the correct format
                contents = [
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": request.mime_type,
                                    "data": base64.b64encode(request.image_bytes).decode('utf-8')
                                }
                            },
                            {
                                "text": request.text_prompt
                            }
                        ]
                    }
                ]
                
                # Generate response
                logger.info(f"Sending multimodal request to {self.model_name} (attempt {attempt + 1})")
                
                response = await asyncio.to_thread(
                    self._model.generate_content,
                    contents,
                    generation_config=generation_config,
                    safety_settings=gemini_safety_settings
                )
                
                # Parse response
                if not response.text:
                    raise GeminiAPIError("Empty response from AI model")
                
                ai_response = AIResponse(
                    text=response.text,
                    usage_metadata=getattr(response, 'usage_metadata', None),
                    safety_ratings=getattr(response, 'safety_ratings', None),
                    finish_reason=getattr(response, 'finish_reason', None)
                )
                
                logger.info("Successfully processed multimodal request")
                return ai_response
                
            except genai.types.BlockedPromptException as e:
                # Content filtered - don't retry
                error_msg = f"Content blocked by safety filters: {str(e)}"
                logger.error(error_msg)
                raise GeminiAPIError(error_msg)
                
            except genai.types.StopCandidateException as e:
                # Generation stopped - don't retry
                error_msg = f"Generation stopped: {str(e)}"
                logger.error(error_msg)
                raise GeminiAPIError(error_msg)
                
            except Exception as e:
                # Check if it's a response stopped exception by string matching
                if "response stopped" in str(e).lower() or "stopped" in str(e).lower():
                    error_msg = f"Response stopped: {str(e)}"
                    logger.error(error_msg)
                    raise GeminiAPIError(error_msg)
                
                # Other errors - retry with exponential backoff
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed, waiting {wait_time}s before retry {attempt + 1}: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_msg = f"Request failed after {max_retries} retries: {str(e)}"
                    logger.error(error_msg)
                    raise GeminiAPIError(error_msg)
        
        # This should never be reached, but just in case
        raise GeminiAPIError("Unexpected error in retry logic")
    
    def parse_structured_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse structured response from AI model.
        
        Args:
            response: The AI response to parse
            
        Returns:
            Dict[str, Any]: Parsed structured data
            
        Raises:
            GeminiAPIError: If response parsing fails
        """
        try:
            # Try to extract JSON from the response
            text = response.text.strip()
            
            # Look for JSON blocks in markdown format
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Look for JSON objects directly
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # If no JSON found, return the text as-is
                    return {"text": text}
            
            # Parse the JSON
            parsed_data = json.loads(json_str)
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {str(e)}")
            # Return the raw text if JSON parsing fails
            return {"text": response.text}
        
        except Exception as e:
            error_msg = f"Error parsing structured response: {str(e)}"
            logger.error(error_msg)
            raise GeminiAPIError(error_msg)
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the Gemini API client.
        
        Returns:
            bool: True if the client is healthy, False otherwise
        """
        try:
            self._ensure_initialized()
            
            # Create a simple test request
            test_image = self._create_test_image()
            test_request = MultimodalRequest(
                image_bytes=test_image,
                text_prompt="Describe this image in one word.",
                generation_config={"max_output_tokens": 10}
            )
            
            # Try to process the request
            response = await self.process_multimodal_request(test_request, max_retries=1)
            
            return bool(response.text)
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Factory function for creating client instances
async def create_gemini_client() -> GeminiClient:
    """
    Create and initialize a Gemini API client.
    
    Returns:
        GeminiClient: Initialized Gemini API client
        
    Raises:
        GeminiAPIError: If client creation or initialization fails
    """
    client = GeminiClient()
    await client.initialize_client()
    return client