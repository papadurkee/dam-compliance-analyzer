"""
Unit tests for the base processor class.

Tests the BaseProcessor abstract class functionality including common methods,
error handling, and validation logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from abc import ABC

from workflow.base_processor import (
    BaseProcessor,
    ProcessorResult,
    ProcessorError,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from services import GeminiClient, MultimodalRequest, AIResponse, GeminiAPIError


class ConcreteProcessor(BaseProcessor):
    """Concrete implementation of BaseProcessor for testing"""
    
    async def process(self, image_bytes: bytes, metadata=None, previous_step_result=None):
        """Test implementation of process method"""
        try:
            self._validate_inputs(image_bytes, metadata, previous_step_result)
            prompt = self._format_prompt(metadata, previous_step_result)
            response = await self._send_request(image_bytes, prompt)
            data = self._parse_response(response)
            
            return ProcessorResult(
                success=True,
                data=data,
                raw_response=response.text
            )
        except (ValidationError, ProcessingError, OutputParsingError) as e:
            return ProcessorResult(
                success=False,
                data={},
                error_message=str(e)
            )
    
    def _format_prompt(self, metadata=None, previous_step_result=None):
        """Test implementation of format_prompt method"""
        prompt = "Test prompt"
        if metadata:
            prompt += f" with metadata: {metadata}"
        if previous_step_result:
            prompt += f" with previous result: {previous_step_result}"
        return prompt
    
    def _parse_response(self, response: AIResponse):
        """Test implementation of parse_response method"""
        if not response.text:
            raise OutputParsingError("Empty response")
        return {"parsed_text": response.text}


class TestProcessorResult:
    """Test ProcessorResult dataclass"""
    
    def test_processor_result_success(self):
        """Test creating a successful ProcessorResult"""
        result = ProcessorResult(
            success=True,
            data={"key": "value"},
            raw_response="raw response text"
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error_message is None
        assert result.raw_response == "raw response text"
    
    def test_processor_result_failure(self):
        """Test creating a failed ProcessorResult"""
        result = ProcessorResult(
            success=False,
            data={},
            error_message="Test error"
        )
        
        assert result.success is False
        assert result.data == {}
        assert result.error_message == "Test error"
        assert result.raw_response is None
    
    def test_processor_result_defaults(self):
        """Test ProcessorResult with default values"""
        result = ProcessorResult(success=True, data={"test": "data"})
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error_message is None
        assert result.raw_response is None


class TestProcessorExceptions:
    """Test processor exception classes"""
    
    def test_processor_error(self):
        """Test ProcessorError base exception"""
        error = ProcessorError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    def test_validation_error(self):
        """Test ValidationError exception"""
        error = ValidationError("Validation failed")
        assert isinstance(error, ProcessorError)
        assert isinstance(error, Exception)
        assert str(error) == "Validation failed"
    
    def test_processing_error(self):
        """Test ProcessingError exception"""
        error = ProcessingError("Processing failed")
        assert isinstance(error, ProcessorError)
        assert isinstance(error, Exception)
        assert str(error) == "Processing failed"
    
    def test_output_parsing_error(self):
        """Test OutputParsingError exception"""
        error = OutputParsingError("Parsing failed")
        assert isinstance(error, ProcessorError)
        assert isinstance(error, Exception)
        assert str(error) == "Parsing failed"


class TestBaseProcessor:
    """Test BaseProcessor abstract class"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a concrete processor instance for testing"""
        return ConcreteProcessor(mock_ai_client)
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Sample image bytes for testing"""
        return b'test_image_data'
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return {"component_id": "test123", "component_name": "Test Component"}
    
    @pytest.fixture
    def sample_previous_result(self):
        """Sample previous step result for testing"""
        return {"notes": "Previous step completed", "status": "success"}
    
    def test_processor_initialization(self, mock_ai_client):
        """Test processor initialization"""
        processor = ConcreteProcessor(mock_ai_client)
        assert processor.ai_client == mock_ai_client
    
    def test_abstract_methods_exist(self):
        """Test that BaseProcessor defines abstract methods"""
        # Verify that BaseProcessor is abstract
        assert BaseProcessor.__abstractmethods__ == {
            'process', '_format_prompt', '_parse_response'
        }
        
        # Verify we cannot instantiate BaseProcessor directly
        with pytest.raises(TypeError):
            BaseProcessor(Mock())
    
    def test_validate_inputs_valid(self, processor, sample_image_bytes, sample_metadata):
        """Test input validation with valid inputs"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, sample_metadata)
    
    def test_validate_inputs_empty_image(self, processor, sample_metadata):
        """Test input validation with empty image bytes"""
        with pytest.raises(ValidationError, match="Image bytes cannot be empty"):
            processor._validate_inputs(b'', sample_metadata)
    
    def test_validate_inputs_none_image(self, processor, sample_metadata):
        """Test input validation with None image bytes"""
        with pytest.raises(ValidationError, match="Image bytes cannot be empty"):
            processor._validate_inputs(None, sample_metadata)
    
    def test_validate_inputs_invalid_metadata_type(self, processor, sample_image_bytes):
        """Test input validation with invalid metadata type"""
        with pytest.raises(ValidationError, match="Metadata must be a dictionary"):
            processor._validate_inputs(sample_image_bytes, "not a dictionary")
    
    def test_validate_inputs_none_metadata(self, processor, sample_image_bytes):
        """Test input validation with None metadata (should be allowed)"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, None)
    
    def test_validate_inputs_with_previous_result(self, processor, sample_image_bytes, 
                                                 sample_metadata, sample_previous_result):
        """Test input validation with previous step result"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, sample_metadata, sample_previous_result)
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, processor, mock_ai_client, sample_image_bytes):
        """Test successful AI request"""
        # Setup mock response
        mock_response = AIResponse(text="Test response")
        mock_ai_client.process_multimodal_request.return_value = mock_response
        
        # Test the method
        result = await processor._send_request(sample_image_bytes, "test prompt")
        
        # Verify results
        assert result == mock_response
        
        # Verify the request was made correctly
        mock_ai_client.process_multimodal_request.assert_called_once()
        call_args = mock_ai_client.process_multimodal_request.call_args[0][0]
        assert isinstance(call_args, MultimodalRequest)
        assert call_args.image_bytes == sample_image_bytes
        assert call_args.text_prompt == "test prompt"
    
    @pytest.mark.asyncio
    async def test_send_request_gemini_api_error(self, processor, mock_ai_client, sample_image_bytes):
        """Test AI request with GeminiAPIError"""
        # Setup mock to raise GeminiAPIError
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        # Test the method
        with pytest.raises(ProcessingError, match="AI request failed: API error"):
            await processor._send_request(sample_image_bytes, "test prompt")
    
    @pytest.mark.asyncio
    async def test_send_request_unexpected_error(self, processor, mock_ai_client, sample_image_bytes):
        """Test AI request with unexpected error"""
        # Setup mock to raise unexpected error
        mock_ai_client.process_multimodal_request.side_effect = Exception("Unexpected error")
        
        # Test the method
        with pytest.raises(ProcessingError, match="Unexpected error during AI request"):
            await processor._send_request(sample_image_bytes, "test prompt")
    
    def test_format_prompt_no_parameters(self, processor):
        """Test prompt formatting without parameters"""
        result = processor._format_prompt()
        assert result == "Test prompt"
    
    def test_format_prompt_with_metadata(self, processor, sample_metadata):
        """Test prompt formatting with metadata"""
        result = processor._format_prompt(metadata=sample_metadata)
        assert "Test prompt" in result
        assert str(sample_metadata) in result
    
    def test_format_prompt_with_previous_result(self, processor, sample_previous_result):
        """Test prompt formatting with previous step result"""
        result = processor._format_prompt(previous_step_result=sample_previous_result)
        assert "Test prompt" in result
        assert str(sample_previous_result) in result
    
    def test_format_prompt_with_both_parameters(self, processor, sample_metadata, sample_previous_result):
        """Test prompt formatting with both metadata and previous result"""
        result = processor._format_prompt(
            metadata=sample_metadata,
            previous_step_result=sample_previous_result
        )
        assert "Test prompt" in result
        assert str(sample_metadata) in result
        assert str(sample_previous_result) in result
    
    def test_parse_response_success(self, processor):
        """Test successful response parsing"""
        response = AIResponse(text="Test response text")
        result = processor._parse_response(response)
        
        assert result == {"parsed_text": "Test response text"}
    
    def test_parse_response_empty_text(self, processor):
        """Test response parsing with empty text"""
        response = AIResponse(text="")
        
        with pytest.raises(OutputParsingError, match="Empty response"):
            processor._parse_response(response)
    
    def test_parse_response_none_text(self, processor):
        """Test response parsing with None text"""
        response = AIResponse(text=None)
        
        with pytest.raises(OutputParsingError, match="Empty response"):
            processor._parse_response(response)
    
    @pytest.mark.asyncio
    async def test_process_success(self, processor, mock_ai_client, sample_image_bytes, sample_metadata):
        """Test successful processing"""
        # Setup mock response
        mock_response = AIResponse(text="Test response")
        mock_ai_client.process_multimodal_request.return_value = mock_response
        
        # Test the method
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        # Verify results
        assert result.success is True
        assert result.data == {"parsed_text": "Test response"}
        assert result.raw_response == "Test response"
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_validation_error(self, processor, sample_metadata):
        """Test processing with validation error"""
        # Test with empty image bytes
        result = await processor.process(b'', sample_metadata)
        
        # Verify results
        assert result.success is False
        assert result.data == {}
        assert "Image bytes cannot be empty" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_processing_error(self, processor, mock_ai_client, 
                                          sample_image_bytes, sample_metadata):
        """Test processing with processing error"""
        # Setup mock to raise error
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        # Test the method
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        # Verify results
        assert result.success is False
        assert result.data == {}
        assert "AI request failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_parsing_error(self, processor, mock_ai_client, 
                                       sample_image_bytes, sample_metadata):
        """Test processing with parsing error"""
        # Setup mock response with empty text
        mock_response = AIResponse(text="")
        mock_ai_client.process_multimodal_request.return_value = mock_response
        
        # Test the method
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        # Verify results
        assert result.success is False
        assert result.data == {}
        assert "Empty response" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_with_previous_result(self, processor, mock_ai_client, 
                                              sample_image_bytes, sample_metadata, 
                                              sample_previous_result):
        """Test processing with previous step result"""
        # Setup mock response
        mock_response = AIResponse(text="Test response")
        mock_ai_client.process_multimodal_request.return_value = mock_response
        
        # Test the method
        result = await processor.process(
            sample_image_bytes, 
            sample_metadata, 
            sample_previous_result
        )
        
        # Verify results
        assert result.success is True
        assert result.data == {"parsed_text": "Test response"}
        
        # Verify that the prompt included the previous result
        # (This would be verified by checking the actual prompt sent to AI,
        # but since we're using a mock, we can verify the method was called)
        mock_ai_client.process_multimodal_request.assert_called_once()


class TestConcreteProcessorImplementation:
    """Test the concrete processor implementation used for testing"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a concrete processor instance for testing"""
        return ConcreteProcessor(mock_ai_client)
    
    def test_concrete_processor_inherits_from_base(self, processor):
        """Test that ConcreteProcessor properly inherits from BaseProcessor"""
        assert isinstance(processor, BaseProcessor)
        assert isinstance(processor, ConcreteProcessor)
    
    def test_concrete_processor_implements_abstract_methods(self, processor):
        """Test that ConcreteProcessor implements all abstract methods"""
        # These methods should exist and be callable
        assert hasattr(processor, 'process')
        assert hasattr(processor, '_format_prompt')
        assert hasattr(processor, '_parse_response')
        
        # They should be callable
        assert callable(processor.process)
        assert callable(processor._format_prompt)
        assert callable(processor._parse_response)


class TestProcessorIntegration:
    """Test integration aspects of the processor"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a concrete processor instance for testing"""
        return ConcreteProcessor(mock_ai_client)
    
    @pytest.mark.asyncio
    async def test_full_processing_workflow(self, processor, mock_ai_client):
        """Test the complete processing workflow"""
        # Setup test data
        image_bytes = b'test_image_data'
        metadata = {"component_id": "test123"}
        previous_result = {"status": "completed"}
        
        # Setup mock response
        mock_response = AIResponse(text="Complete workflow response")
        mock_ai_client.process_multimodal_request.return_value = mock_response
        
        # Test the complete workflow
        result = await processor.process(image_bytes, metadata, previous_result)
        
        # Verify the complete workflow executed successfully
        assert result.success is True
        assert result.data == {"parsed_text": "Complete workflow response"}
        assert result.raw_response == "Complete workflow response"
        assert result.error_message is None
        
        # Verify AI client was called with correct request
        mock_ai_client.process_multimodal_request.assert_called_once()
        call_args = mock_ai_client.process_multimodal_request.call_args[0][0]
        assert isinstance(call_args, MultimodalRequest)
        assert call_args.image_bytes == image_bytes
        
        # Verify the prompt included all provided data
        expected_prompt_parts = [
            "Test prompt",
            str(metadata),
            str(previous_result)
        ]
        for part in expected_prompt_parts:
            assert part in call_args.text_prompt
    
    def test_multimodal_request_creation(self, processor):
        """Test that MultimodalRequest is created correctly"""
        image_bytes = b'test_image_data'
        prompt = "test prompt"
        
        # Create a MultimodalRequest like the processor does
        request = MultimodalRequest(
            image_bytes=image_bytes,
            text_prompt=prompt
        )
        
        # Verify the request structure
        assert request.image_bytes == image_bytes
        assert request.text_prompt == prompt
        assert request.mime_type == "image/jpeg"  # default value


if __name__ == "__main__":
    pytest.main([__file__])