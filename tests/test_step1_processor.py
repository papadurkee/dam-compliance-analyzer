"""
Unit tests for Step 1 DAM Analysis processor.

Tests the Step1Processor class functionality including prompt formatting,
response parsing, and error handling.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from workflow import (
    Step1Processor,
    ProcessorResult,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from services import GeminiClient, AIResponse


class TestStep1Processor:
    """Test cases for Step1Processor class"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        client.parse_structured_response = Mock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a Step1Processor instance for testing"""
        return Step1Processor(mock_ai_client)
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Sample image bytes for testing"""
        return b'test_image_data'
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return {
            "component_id": "IMG_12345",
            "component_name": "Product Hero Image"
        }
    
    @pytest.fixture
    def sample_response(self):
        """Sample AI response for testing"""
        return AIResponse(
            text="""
            ```json
            {
                "notes": "The image appears to be a high-quality product photo with good lighting and composition.",
                "job_aid_assessment": {
                    "visual_quality": {
                        "assessment": "PASS",
                        "issues": []
                    },
                    "technical_specifications": {
                        "assessment": "PASS",
                        "issues": []
                    }
                },
                "human_readable_section": "This product image meets all quality standards.",
                "next_steps": ["Proceed to Step 2"]
            }
            ```
            """
        )
    
    @pytest.fixture
    def sample_parsed_data(self):
        """Sample parsed data for testing"""
        return {
            "notes": "The image appears to be a high-quality product photo with good lighting and composition.",
            "job_aid_assessment": {
                "visual_quality": {
                    "assessment": "PASS",
                    "issues": []
                },
                "technical_specifications": {
                    "assessment": "PASS",
                    "issues": []
                }
            },
            "human_readable_section": "This product image meets all quality standards.",
            "next_steps": ["Proceed to Step 2"]
        }
    
    def test_format_prompt(self, processor, sample_metadata):
        """Test formatting prompt for Step 1"""
        prompt = processor._format_prompt(sample_metadata)
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "TASK:" in prompt
        assert "OUTPUT INSTRUCTIONS:" in prompt
        
        # Check that metadata is included
        assert "METADATA:" in prompt
        assert "IMG_12345" in prompt
    
    def test_format_prompt_without_metadata(self, processor):
        """Test formatting prompt without metadata"""
        prompt = processor._format_prompt()
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "TASK:" in prompt
        assert "OUTPUT INSTRUCTIONS:" in prompt
        
        # Check that metadata is not included
        assert "METADATA:" not in prompt
    
    def test_validate_inputs_valid(self, processor, sample_image_bytes, sample_metadata):
        """Test validating valid inputs"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, sample_metadata)
    
    def test_validate_inputs_empty_image(self, processor, sample_metadata):
        """Test validating empty image bytes"""
        with pytest.raises(ValidationError, match="Image bytes cannot be empty"):
            processor._validate_inputs(b'', sample_metadata)
    
    def test_validate_inputs_invalid_metadata(self, processor, sample_image_bytes):
        """Test validating invalid metadata"""
        with pytest.raises(ValidationError, match="Metadata must be a dictionary"):
            processor._validate_inputs(sample_image_bytes, "not a dictionary")
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, processor, mock_ai_client, sample_image_bytes, sample_response):
        """Test successful request to AI model"""
        mock_ai_client.process_multimodal_request.return_value = sample_response
        
        response = await processor._send_request(sample_image_bytes, "test prompt")
        
        assert response == sample_response
        mock_ai_client.process_multimodal_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_request_error(self, processor, mock_ai_client, sample_image_bytes):
        """Test request to AI model with error"""
        from services import GeminiAPIError
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        with pytest.raises(ProcessingError, match="AI request failed"):
            await processor._send_request(sample_image_bytes, "test prompt")
    
    def test_parse_response_success(self, processor, mock_ai_client, sample_response, sample_parsed_data):
        """Test successful response parsing"""
        mock_ai_client.parse_structured_response.return_value = sample_parsed_data
        
        result = processor._parse_response(sample_response)
        
        assert result == sample_parsed_data
        mock_ai_client.parse_structured_response.assert_called_once_with(sample_response)
    
    def test_parse_response_with_text(self, processor, mock_ai_client, sample_response):
        """Test response parsing with text response"""
        mock_ai_client.parse_structured_response.return_value = {"text": sample_response.text}
        
        result = processor._parse_response(sample_response)
        
        assert "notes" in result
        assert "job_aid_assessment" in result
        assert "human_readable_section" in result
        assert "next_steps" in result
    
    def test_parse_response_missing_fields(self, processor, mock_ai_client, sample_response):
        """Test response parsing with missing fields"""
        mock_ai_client.parse_structured_response.return_value = {
            "notes": "Test notes",
            # Missing job_aid_assessment
            "human_readable_section": "Test summary",
            "next_steps": []
        }
        
        with pytest.raises(OutputParsingError, match="missing required fields"):
            processor._parse_response(sample_response)
    
    def test_parse_response_invalid_job_aid(self, processor, mock_ai_client, sample_response):
        """Test response parsing with invalid job aid"""
        mock_ai_client.parse_structured_response.return_value = {
            "notes": "Test notes",
            "job_aid_assessment": "not a dictionary",  # Should be a dictionary
            "human_readable_section": "Test summary",
            "next_steps": []
        }
        
        with pytest.raises(OutputParsingError, match="job_aid_assessment must be a dictionary"):
            processor._parse_response(sample_response)
    
    def test_parse_response_invalid_next_steps(self, processor, mock_ai_client, sample_response):
        """Test response parsing with invalid next steps"""
        mock_ai_client.parse_structured_response.return_value = {
            "notes": "Test notes",
            "job_aid_assessment": {},
            "human_readable_section": "Test summary",
            "next_steps": "not a list"  # Should be a list
        }
        
        with pytest.raises(OutputParsingError, match="next_steps must be a list"):
            processor._parse_response(sample_response)
    
    def test_extract_json_from_text_markdown(self, processor):
        """Test extracting JSON from markdown code block"""
        text = '```json\n{"key": "value"}\n```'
        result = processor._extract_json_from_text(text)
        assert result == '{"key": "value"}'
    
    def test_extract_json_from_text_direct(self, processor):
        """Test extracting JSON directly from text"""
        text = 'Some text {"key": "value"} more text'
        result = processor._extract_json_from_text(text)
        assert result == '{"key": "value"}'
    
    def test_extract_json_from_text_not_found(self, processor):
        """Test extracting JSON when not found"""
        text = 'No JSON here'
        result = processor._extract_json_from_text(text)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_success(self, processor, mock_ai_client, sample_image_bytes, 
                                 sample_metadata, sample_response, sample_parsed_data):
        """Test successful processing"""
        mock_ai_client.process_multimodal_request.return_value = sample_response
        mock_ai_client.parse_structured_response.return_value = sample_parsed_data
        
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        assert result.success is True
        assert result.data == sample_parsed_data
        assert result.raw_response == sample_response.text
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_validation_error(self, processor, sample_metadata):
        """Test processing with validation error"""
        result = await processor.process(b'', sample_metadata)
        
        assert result.success is False
        assert "validation error" in result.error_message
        assert "Image bytes cannot be empty" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_processing_error(self, processor, mock_ai_client, 
                                          sample_image_bytes, sample_metadata):
        """Test processing with processing error"""
        from services import GeminiAPIError
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        assert result.success is False
        assert "processing error" in result.error_message
        assert "AI request failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_parsing_error(self, processor, mock_ai_client, 
                                       sample_image_bytes, sample_metadata, sample_response):
        """Test processing with parsing error"""
        mock_ai_client.process_multimodal_request.return_value = sample_response
        mock_ai_client.parse_structured_response.return_value = {"notes": "Test notes"}  # Missing required fields
        
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        assert result.success is False
        assert "output parsing error" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__])