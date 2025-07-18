"""
Unit tests for Step 2 Job Aid Assessment processor.

Tests the Step2Processor class functionality including prompt formatting,
response parsing, and error handling.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from workflow import (
    Step2Processor,
    ProcessorResult,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from services import GeminiClient, AIResponse
from schemas import get_job_aid_schema


class TestStep2Processor:
    """Test cases for Step2Processor class"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        client.parse_structured_response = Mock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a Step2Processor instance for testing"""
        return Step2Processor(mock_ai_client)
    
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
    def sample_step1_result(self):
        """Sample Step 1 result for testing"""
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
    
    @pytest.fixture
    def sample_job_aid_response(self):
        """Sample AI response with job aid for testing"""
        return AIResponse(
            text="""
            ```json
            {
                "digital_component_analysis": {
                    "instructions": "Complete all sections of this job aid to assess the digital component.",
                    "component_specifications": {
                        "file_format_requirements": {
                            "allowed_formats": ["JPG", "PNG"],
                            "format_restrictions": "None",
                            "assessment": "PASS",
                            "notes": "Image is in JPG format which is allowed"
                        },
                        "resolution_requirements": {
                            "minimum_resolution": "1200x800",
                            "optimal_resolution": "1920x1080",
                            "assessment": "PASS",
                            "notes": "Image meets resolution requirements"
                        },
                        "assessment": "PASS",
                        "notes": "All specifications are met"
                    },
                    "component_qc": {
                        "visual_quality_checks": {
                            "clarity": {
                                "assessment": "PASS",
                                "notes": "Image is clear"
                            },
                            "lighting": {
                                "assessment": "PASS",
                                "notes": "Lighting is good"
                            }
                        },
                        "assessment": "PASS",
                        "notes": "Visual quality is good"
                    },
                    "overall_assessment": {
                        "status": "PASS",
                        "summary": "The image meets all requirements",
                        "critical_issues": [],
                        "recommendations": ["No changes needed"]
                    }
                }
            }
            ```
            """
        )
    
    @pytest.fixture
    def sample_parsed_job_aid(self):
        """Sample parsed job aid data for testing"""
        return {
            "digital_component_analysis": {
                "instructions": "Complete all sections of this job aid to assess the digital component.",
                "component_specifications": {
                    "file_format_requirements": {
                        "allowed_formats": ["JPG", "PNG"],
                        "format_restrictions": "None",
                        "assessment": "PASS",
                        "notes": "Image is in JPG format which is allowed"
                    },
                    "resolution_requirements": {
                        "minimum_resolution": "1200x800",
                        "optimal_resolution": "1920x1080",
                        "assessment": "PASS",
                        "notes": "Image meets resolution requirements"
                    },
                    "assessment": "PASS",
                    "notes": "All specifications are met"
                },
                "component_qc": {
                    "visual_quality_checks": {
                        "clarity": {
                            "assessment": "PASS",
                            "notes": "Image is clear"
                        },
                        "lighting": {
                            "assessment": "PASS",
                            "notes": "Lighting is good"
                        }
                    },
                    "assessment": "PASS",
                    "notes": "Visual quality is good"
                },
                "overall_assessment": {
                    "status": "PASS",
                    "summary": "The image meets all requirements",
                    "critical_issues": [],
                    "recommendations": ["No changes needed"]
                }
            }
        }
    
    def test_format_prompt(self, processor, sample_metadata, sample_step1_result):
        """Test formatting prompt for Step 2"""
        prompt = processor._format_prompt(sample_metadata, sample_step1_result)
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "STEP 1 RESULTS:" in prompt
        assert "DIGITAL COMPONENT ANALYSIS JOB AID:" in prompt
        
        # Check that metadata is included
        assert "METADATA:" in prompt
        assert "IMG_12345" in prompt
        
        # Check that Step 1 results are included
        assert "high-quality product photo" in prompt
    
    def test_format_prompt_without_metadata(self, processor, sample_step1_result):
        """Test formatting prompt without metadata"""
        prompt = processor._format_prompt(None, sample_step1_result)
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "STEP 1 RESULTS:" in prompt
        assert "DIGITAL COMPONENT ANALYSIS JOB AID:" in prompt
        
        # Check that metadata is not included
        assert "METADATA:" not in prompt
    
    def test_validate_inputs_valid(self, processor, sample_image_bytes, sample_metadata, sample_step1_result):
        """Test validating valid inputs"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, sample_metadata, sample_step1_result)
    
    def test_validate_inputs_missing_previous_result(self, processor, sample_image_bytes, sample_metadata):
        """Test validating without previous step result"""
        with pytest.raises(ValidationError, match="Previous step result is required"):
            processor._validate_inputs(sample_image_bytes, sample_metadata, None)
    
    def test_validate_inputs_invalid_previous_result(self, processor, sample_image_bytes, sample_metadata):
        """Test validating with invalid previous step result"""
        with pytest.raises(ValidationError, match="Previous step result must be a dictionary"):
            processor._validate_inputs(sample_image_bytes, sample_metadata, "not a dictionary")
    
    def test_validate_inputs_missing_fields(self, processor, sample_image_bytes, sample_metadata):
        """Test validating previous step result with missing fields"""
        incomplete_result = {"notes": "Test notes"}  # Missing required fields
        
        with pytest.raises(ValidationError, match="missing required fields"):
            processor._validate_inputs(sample_image_bytes, sample_metadata, incomplete_result)
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, processor, mock_ai_client, sample_image_bytes, sample_job_aid_response):
        """Test successful request to AI model"""
        mock_ai_client.process_multimodal_request.return_value = sample_job_aid_response
        
        response = await processor._send_request(sample_image_bytes, "test prompt")
        
        assert response == sample_job_aid_response
        mock_ai_client.process_multimodal_request.assert_called_once()
    
    def test_parse_response_success(self, processor, mock_ai_client, sample_job_aid_response, sample_parsed_job_aid):
        """Test successful response parsing"""
        mock_ai_client.parse_structured_response.return_value = sample_parsed_job_aid
        
        result = processor._parse_response(sample_job_aid_response)
        
        assert "completed_job_aid" in result
        assert "assessment_summary" in result
        assert result["completed_job_aid"] == sample_parsed_job_aid
        assert "Assessment Status: PASS" in result["assessment_summary"]
        mock_ai_client.parse_structured_response.assert_called_once_with(sample_job_aid_response)
    
    def test_parse_response_with_text(self, processor, mock_ai_client, sample_job_aid_response):
        """Test response parsing with text response"""
        mock_ai_client.parse_structured_response.return_value = {"text": sample_job_aid_response.text}
        
        result = processor._parse_response(sample_job_aid_response)
        
        assert "completed_job_aid" in result
        assert "assessment_summary" in result
        assert "digital_component_analysis" in result["completed_job_aid"]
        assert "Assessment Status: PASS" in result["assessment_summary"]
    
    def test_parse_response_missing_structure(self, processor, mock_ai_client, sample_job_aid_response):
        """Test response parsing with missing structure"""
        mock_ai_client.parse_structured_response.return_value = {
            "some_field": "Some value"
            # Missing digital_component_analysis structure
        }
        
        with pytest.raises(OutputParsingError, match="Job aid validation failed"):
            processor._parse_response(sample_job_aid_response)
    
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
    
    def test_extract_assessment_summary_complete(self, processor, sample_parsed_job_aid):
        """Test extracting assessment summary with complete data"""
        summary = processor._extract_assessment_summary(sample_parsed_job_aid)
        
        assert "Assessment Status: PASS" in summary
        assert "The image meets all requirements" in summary
        assert "No changes needed" in summary
    
    def test_extract_assessment_summary_missing_fields(self, processor):
        """Test extracting assessment summary with missing fields"""
        incomplete_data = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "FAIL"
                    # Missing summary, critical_issues, recommendations
                }
            }
        }
        
        summary = processor._extract_assessment_summary(incomplete_data)
        
        assert "Assessment Status: FAIL" in summary
        assert "compliance issues" in summary  # Default text
    
    def test_extract_assessment_summary_with_issues(self, processor):
        """Test extracting assessment summary with critical issues"""
        data_with_issues = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "FAIL",
                    "summary": "There are issues with the image",
                    "critical_issues": ["Low resolution", "Wrong format"],
                    "recommendations": ["Increase resolution", "Convert to JPG"]
                }
            }
        }
        
        summary = processor._extract_assessment_summary(data_with_issues)
        
        assert "Assessment Status: FAIL" in summary
        assert "There are issues with the image" in summary
        assert "Critical Issues:" in summary
        assert "1. Low resolution" in summary
        assert "2. Wrong format" in summary
        assert "Recommendations:" in summary
        assert "1. Increase resolution" in summary
        assert "2. Convert to JPG" in summary
    
    def test_extract_assessment_summary_inner_object(self, processor):
        """Test extracting assessment summary when AI returns just the inner object"""
        inner_object = {
            "overall_assessment": {
                "status": "PASS",
                "summary": "All good"
            }
        }
        
        summary = processor._extract_assessment_summary(inner_object)
        
        assert "Assessment Status: PASS" in summary
        assert "All good" in summary
    
    @pytest.mark.asyncio
    async def test_process_success(self, processor, mock_ai_client, sample_image_bytes, 
                                 sample_metadata, sample_step1_result, 
                                 sample_job_aid_response, sample_parsed_job_aid):
        """Test successful processing"""
        mock_ai_client.process_multimodal_request.return_value = sample_job_aid_response
        mock_ai_client.parse_structured_response.return_value = sample_parsed_job_aid
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step1_result)
        
        assert result.success is True
        assert "completed_job_aid" in result.data
        assert "assessment_summary" in result.data
        assert result.data["completed_job_aid"] == sample_parsed_job_aid
        assert "Assessment Status: PASS" in result.data["assessment_summary"]
        assert result.raw_response == sample_job_aid_response.text
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_validation_error(self, processor, sample_image_bytes, sample_metadata):
        """Test processing with validation error"""
        # Missing previous_step_result
        result = await processor.process(sample_image_bytes, sample_metadata)
        
        assert result.success is False
        assert "validation error" in result.error_message
        assert "Previous step result is required" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_processing_error(self, processor, mock_ai_client, 
                                          sample_image_bytes, sample_metadata, sample_step1_result):
        """Test processing with processing error"""
        from services import GeminiAPIError
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step1_result)
        
        assert result.success is False
        assert "processing error" in result.error_message
        assert "AI request failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_parsing_error(self, processor, mock_ai_client, 
                                       sample_image_bytes, sample_metadata, 
                                       sample_step1_result, sample_job_aid_response):
        """Test processing with parsing error"""
        mock_ai_client.process_multimodal_request.return_value = sample_job_aid_response
        mock_ai_client.parse_structured_response.return_value = {"some_field": "Some value"}  # Invalid structure
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step1_result)
        
        assert result.success is False
        assert "output parsing error" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__])