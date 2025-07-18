"""
Unit tests for Google Gemini API client integration.

Tests the GeminiClient class functionality including initialization,
multimodal request processing, error handling, and retry logic.
"""

import pytest
import asyncio
import base64
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import BytesIO

from services.vertex_ai_client import (
    GeminiClient,
    GeminiAPIError,
    MultimodalRequest,
    AIResponse,
    create_gemini_client
)
import google.generativeai as genai


class TestGeminiClient:
    """Test cases for GeminiClient class"""
    
    @pytest.fixture
    def gemini_client(self):
        """Create a Gemini client instance for testing"""
        return GeminiClient()
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing"""
        # Create a minimal JPEG-like byte sequence
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'
    
    @pytest.fixture
    def sample_request(self, sample_image_bytes):
        """Create a sample multimodal request"""
        return MultimodalRequest(
            image_bytes=sample_image_bytes,
            text_prompt="Analyze this image for compliance issues.",
            mime_type="image/jpeg"
        )
    
    def test_client_initialization(self, gemini_client):
        """Test client initialization"""
        assert gemini_client.model_name == "gemini-2.0-flash-exp"
        assert not gemini_client._initialized
    
    @patch('services.vertex_ai_client.genai')
    @patch('services.vertex_ai_client.st')
    async def test_initialize_client_success(self, mock_st, mock_genai, gemini_client):
        """Test successful client initialization"""
        # Setup
        mock_st.secrets = {"gemini_api_key": "test_api_key"}
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        await gemini_client.initialize_client()
        
        assert gemini_client._initialized
        assert gemini_client._model == mock_model
        mock_genai.configure.assert_called_once_with(api_key="test_api_key")
        mock_genai.GenerativeModel.assert_called_once()
    
    @patch('services.vertex_ai_client.st')
    async def test_initialize_client_missing_api_key(self, mock_st, gemini_client):
        """Test client initialization with missing API key"""
        # Setup
        mock_st.secrets = {}
        
        with pytest.raises(GeminiAPIError, match="Gemini API key not found"):
            await gemini_client.initialize_client()
    
    def test_ensure_initialized_not_initialized(self, gemini_client):
        """Test _ensure_initialized when client is not initialized"""
        with pytest.raises(GeminiAPIError, match="Client not initialized"):
            gemini_client._ensure_initialized()
    
    def test_create_image_data_success(self, gemini_client, sample_image_bytes):
        """Test successful image data creation"""
        result = gemini_client._create_image_data(sample_image_bytes, "image/jpeg")
        
        assert isinstance(result, dict)
        assert "mime_type" in result
        assert "data" in result
        assert result["mime_type"] == "image/jpeg"
        assert isinstance(result["data"], str)
        # Verify it's base64 encoded
        try:
            decoded = base64.b64decode(result["data"])
            assert decoded == sample_image_bytes
        except Exception:
            pytest.fail("Failed to decode base64 data")
    
    def test_get_default_generation_config(self, gemini_client):
        """Test default generation configuration"""
        config = gemini_client._get_default_generation_config()
        
        assert isinstance(config, dict)
        assert "max_output_tokens" in config
        assert "temperature" in config
        assert "top_p" in config
        assert "top_k" in config
    
    def test_get_default_safety_settings(self, gemini_client):
        """Test default safety settings"""
        settings = gemini_client._get_default_safety_settings()
        
        assert isinstance(settings, list)
        assert len(settings) == 4
        for setting in settings:
            assert "category" in setting
            assert "threshold" in setting
    
    @patch('services.vertex_ai_client.asyncio.to_thread')
    async def test_process_multimodal_request_success(self, mock_to_thread, gemini_client, sample_request):
        """Test successful multimodal request processing"""
        # Setup
        gemini_client._initialized = True
        gemini_client._model = Mock()
        
        mock_response = Mock()
        mock_response.text = "Analysis complete: No issues found."
        mock_response.usage_metadata = {"tokens": 100}
        mock_response.safety_ratings = []
        mock_response.finish_reason = "STOP"
        
        mock_to_thread.return_value = mock_response
        
        with patch.object(gemini_client, '_create_image_data') as mock_create_image:
            mock_create_image.return_value = {"mime_type": "image/jpeg", "data": "base64data"}
            
            result = await gemini_client.process_multimodal_request(sample_request)
            
            assert isinstance(result, AIResponse)
            assert result.text == "Analysis complete: No issues found."
            assert result.usage_metadata == {"tokens": 100}
    
    async def test_process_multimodal_request_not_initialized(self, gemini_client, sample_request):
        """Test multimodal request when client is not initialized"""
        with pytest.raises(GeminiAPIError, match="Client not initialized"):
            await gemini_client.process_multimodal_request(sample_request)
    
    @patch('services.vertex_ai_client.asyncio.to_thread')
    @patch('services.vertex_ai_client.asyncio.sleep')
    async def test_process_multimodal_request_retry_logic(self, mock_sleep, mock_to_thread, gemini_client, sample_request):
        """Test retry logic in multimodal request processing"""
        # Setup
        gemini_client._initialized = True
        gemini_client._model = Mock()
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = "Success after retry"
        
        mock_to_thread.side_effect = [Exception("Temporary failure"), mock_response]
        
        with patch.object(gemini_client, '_create_image_data') as mock_create_image:
            mock_create_image.return_value = {"mime_type": "image/jpeg", "data": "base64data"}
            
            result = await gemini_client.process_multimodal_request(sample_request, max_retries=1)
            
            assert result.text == "Success after retry"
            assert mock_to_thread.call_count == 2
            mock_sleep.assert_called_once()
    
    @patch('services.vertex_ai_client.asyncio.to_thread')
    async def test_process_multimodal_request_max_retries_exceeded(self, mock_to_thread, gemini_client, sample_request):
        """Test multimodal request when max retries are exceeded"""
        # Setup
        gemini_client._initialized = True
        gemini_client._model = Mock()
        
        mock_to_thread.side_effect = Exception("Persistent failure")
        
        with patch.object(gemini_client, '_create_image_data') as mock_create_image:
            mock_create_image.return_value = {"mime_type": "image/jpeg", "data": "base64data"}
            
            with pytest.raises(GeminiAPIError, match="Request failed after .* retries"):
                await gemini_client.process_multimodal_request(sample_request, max_retries=2)
    
    def test_parse_structured_response_json_in_markdown(self, gemini_client):
        """Test parsing structured response with JSON in markdown"""
        response = AIResponse(
            text='Here is the analysis:\n```json\n{"status": "passed", "issues": []}\n```\nEnd of analysis.'
        )
        
        result = gemini_client.parse_structured_response(response)
        
        assert result == {"status": "passed", "issues": []}
    
    def test_parse_structured_response_direct_json(self, gemini_client):
        """Test parsing structured response with direct JSON"""
        response = AIResponse(
            text='Analysis result: {"status": "failed", "issues": ["Issue 1", "Issue 2"]}'
        )
        
        result = gemini_client.parse_structured_response(response)
        
        assert result == {"status": "failed", "issues": ["Issue 1", "Issue 2"]}
    
    def test_parse_structured_response_no_json(self, gemini_client):
        """Test parsing structured response with no JSON"""
        response = AIResponse(text="This is plain text without JSON.")
        
        result = gemini_client.parse_structured_response(response)
        
        assert result == {"text": "This is plain text without JSON."}
    
    def test_parse_structured_response_invalid_json(self, gemini_client):
        """Test parsing structured response with invalid JSON"""
        response = AIResponse(text='{"invalid": json}')
        
        result = gemini_client.parse_structured_response(response)
        
        assert result == {"text": '{"invalid": json}'}
    
    @patch.object(GeminiClient, 'process_multimodal_request')
    async def test_health_check_success(self, mock_process, gemini_client):
        """Test successful health check"""
        gemini_client._initialized = True
        gemini_client._model = Mock()
        
        mock_process.return_value = AIResponse(text="Test response")
        
        result = await gemini_client.health_check()
        
        assert result is True
        mock_process.assert_called_once()
    
    @patch.object(GeminiClient, 'process_multimodal_request')
    async def test_health_check_failure(self, mock_process, gemini_client):
        """Test health check failure"""
        gemini_client._initialized = True
        gemini_client._model = Mock()
        
        mock_process.side_effect = GeminiAPIError("Health check failed")
        
        result = await gemini_client.health_check()
        
        assert result is False
    
    def test_create_test_image(self, gemini_client):
        """Test test image creation"""
        result = gemini_client._create_test_image()
        
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestCreateGeminiClient:
    """Test cases for create_gemini_client factory function"""
    
    @patch('services.vertex_ai_client.GeminiClient')
    async def test_create_gemini_client_success(self, mock_client_class):
        """Test successful client creation"""
        mock_client = Mock()
        mock_client.initialize_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        result = await create_gemini_client()
        
        assert result == mock_client
        mock_client_class.assert_called_once()
        mock_client.initialize_client.assert_called_once()
    
    @patch('services.vertex_ai_client.GeminiClient')
    async def test_create_gemini_client_initialization_error(self, mock_client_class):
        """Test client creation with initialization error"""
        mock_client = Mock()
        mock_client.initialize_client = AsyncMock(side_effect=GeminiAPIError("Init failed"))
        mock_client_class.return_value = mock_client
        
        with pytest.raises(GeminiAPIError, match="Init failed"):
            await create_gemini_client()


class TestMultimodalRequest:
    """Test cases for MultimodalRequest dataclass"""
    
    def test_multimodal_request_creation(self):
        """Test MultimodalRequest creation with required fields"""
        request = MultimodalRequest(
            image_bytes=b"test_image_data",
            text_prompt="Test prompt"
        )
        
        assert request.image_bytes == b"test_image_data"
        assert request.text_prompt == "Test prompt"
        assert request.mime_type == "image/jpeg"  # default value
        assert request.generation_config is None
        assert request.safety_settings is None
    
    def test_multimodal_request_with_optional_fields(self):
        """Test MultimodalRequest creation with optional fields"""
        config = {"temperature": 0.5}
        safety = [{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
        
        request = MultimodalRequest(
            image_bytes=b"test_image_data",
            text_prompt="Test prompt",
            mime_type="image/png",
            generation_config=config,
            safety_settings=safety
        )
        
        assert request.mime_type == "image/png"
        assert request.generation_config == config
        assert request.safety_settings == safety


class TestAIResponse:
    """Test cases for AIResponse dataclass"""
    
    def test_ai_response_creation(self):
        """Test AIResponse creation with required fields"""
        response = AIResponse(text="Test response text")
        
        assert response.text == "Test response text"
        assert response.usage_metadata is None
        assert response.safety_ratings is None
        assert response.finish_reason is None
    
    def test_ai_response_with_optional_fields(self):
        """Test AIResponse creation with optional fields"""
        usage = {"tokens": 100}
        safety = [{"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"}]
        
        response = AIResponse(
            text="Test response text",
            usage_metadata=usage,
            safety_ratings=safety,
            finish_reason="STOP"
        )
        
        assert response.usage_metadata == usage
        assert response.safety_ratings == safety
        assert response.finish_reason == "STOP"


if __name__ == "__main__":
    pytest.main([__file__])