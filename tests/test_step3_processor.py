"""
Unit tests for Step 3 Findings Transmission processor.

Tests the Step3Processor class functionality including prompt formatting,
response parsing, dual-format output generation, and error handling.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from workflow import (
    Step3Processor,
    ProcessorResult,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from services import GeminiClient, AIResponse
from schemas import get_findings_schema


class TestStep3Processor:
    """Test cases for Step3Processor class"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        client.parse_structured_response = Mock()
        return client
    
    @pytest.fixture
    def processor(self, mock_ai_client):
        """Create a Step3Processor instance for testing"""
        return Step3Processor(mock_ai_client)
    
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
    def sample_step2_result(self):
        """Sample Step 2 result for testing"""
        return {
            "completed_job_aid": {
                "digital_component_analysis": {
                    "component_specifications": {
                        "file_format_requirements": {
                            "assessment": "PASS",
                            "notes": "Image is in JPG format which is allowed"
                        },
                        "assessment": "PASS",
                        "notes": "All specifications are met"
                    },
                    "component_qc": {
                        "visual_quality_checks": {
                            "clarity": {
                                "assessment": "PASS",
                                "notes": "Image is clear"
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
            },
            "assessment_summary": "Assessment Status: PASS\n\nThe image meets all requirements"
        }
    
    @pytest.fixture
    def sample_step2_result_with_issues(self):
        """Sample Step 2 result with issues for testing"""
        return {
            "completed_job_aid": {
                "digital_component_analysis": {
                    "component_specifications": {
                        "file_format_requirements": {
                            "assessment": "FAIL",
                            "notes": "Image format is not supported"
                        },
                        "assessment": "FAIL",
                        "notes": "Format requirements not met"
                    },
                    "component_qc": {
                        "visual_quality_checks": {
                            "clarity": {
                                "assessment": "FAIL",
                                "notes": "Image is blurry"
                            }
                        },
                        "assessment": "FAIL",
                        "notes": "Visual quality issues detected"
                    },
                    "overall_assessment": {
                        "status": "FAIL",
                        "summary": "The image has multiple compliance issues",
                        "critical_issues": ["Unsupported format", "Poor image quality"],
                        "recommendations": ["Convert to JPG format", "Improve image clarity"]
                    }
                }
            },
            "assessment_summary": "Assessment Status: FAIL\n\nThe image has multiple compliance issues"
        }
    
    @pytest.fixture
    def sample_findings_json(self):
        """Sample findings JSON output for testing"""
        return {
            "component_id": "IMG_12345",
            "component_name": "Product Hero Image",
            "check_status": "PASSED",
            "issues_detected": [],
            "missing_information": [],
            "recommendations": ["No changes needed"]
        }
    
    @pytest.fixture
    def sample_findings_json_with_issues(self):
        """Sample findings JSON output with issues for testing"""
        return {
            "component_id": "IMG_12345",
            "component_name": "Product Hero Image",
            "check_status": "FAILED",
            "issues_detected": [
                {
                    "category": "File Format",
                    "description": "Image format is not supported",
                    "action": "Convert to JPG format"
                },
                {
                    "category": "Visual Quality",
                    "description": "Image is blurry",
                    "action": "Improve image clarity"
                }
            ],
            "missing_information": [
                {
                    "field": "color_profile",
                    "description": "Color profile information is missing",
                    "action": "Provide color profile metadata"
                }
            ],
            "recommendations": [
                "Convert to JPG format",
                "Improve image clarity",
                "Add color profile information"
            ]
        }
    
    @pytest.fixture
    def sample_human_readable_report(self):
        """Sample human-readable report for testing"""
        return """DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT
==================================================

Component Name: Product Hero Image
Component ID: IMG_12345
Assessment Date: 2024-01-15

OVERALL COMPLIANCE STATUS: PASSED

The digital component has successfully passed all compliance checks.
No critical issues were identified during the assessment.

RECOMMENDATIONS:
1. No changes needed

==================================================
This report was generated by the DAM Compliance Analyzer.
For questions or concerns, please contact your DAM administrator."""
    
    @pytest.fixture
    def sample_dual_format_response(self, sample_findings_json, sample_human_readable_report):
        """Sample AI response with dual format output"""
        json_str = json.dumps(sample_findings_json, indent=2)
        return AIResponse(
            text=f"""
            Here is the structured JSON output:
            
            ```json
            {json_str}
            ```
            
            HUMAN-READABLE REPORT:
            
            {sample_human_readable_report}
            """
        )
    
    @pytest.fixture
    def sample_json_only_response(self, sample_findings_json):
        """Sample AI response with only JSON output"""
        json_str = json.dumps(sample_findings_json, indent=2)
        return AIResponse(
            text=f"""
            ```json
            {json_str}
            ```
            """
        )
    
    def test_format_prompt(self, processor, sample_metadata, sample_step2_result):
        """Test formatting prompt for Step 3"""
        prompt = processor._format_prompt(sample_metadata, sample_step2_result)
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "STEP 2 RESULTS:" in prompt
        assert "STRUCTURED JSON OUTPUT" in prompt
        assert "HUMAN-READABLE REPORT" in prompt
        
        # Check that metadata is included
        assert "METADATA:" in prompt
        assert "IMG_12345" in prompt
        
        # Check that Step 2 results are included
        assert "completed_job_aid" in prompt
    
    def test_format_prompt_without_metadata(self, processor, sample_step2_result):
        """Test formatting prompt without metadata"""
        prompt = processor._format_prompt(None, sample_step2_result)
        
        # Check that the prompt contains key elements
        assert "Digital Asset Management (DAM) analyst" in prompt
        assert "STEP 2 RESULTS:" in prompt
        assert "STRUCTURED JSON OUTPUT" in prompt
        
        # Check that metadata is not included
        assert "METADATA:" not in prompt
    
    def test_validate_inputs_valid(self, processor, sample_image_bytes, sample_metadata, sample_step2_result):
        """Test validating valid inputs"""
        # Should not raise any exceptions
        processor._validate_inputs(sample_image_bytes, sample_metadata, sample_step2_result)
    
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
        incomplete_result = {"assessment_summary": "Test summary"}  # Missing completed_job_aid
        
        with pytest.raises(ValidationError, match="missing required fields"):
            processor._validate_inputs(sample_image_bytes, sample_metadata, incomplete_result)
    
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
    
    def test_extract_json_from_text_complex(self, processor):
        """Test extracting complex JSON from text"""
        text = 'Some text {"key": {"nested": "value"}, "array": [1, 2]} more text'
        result = processor._extract_json_from_text(text)
        assert result == '{"key": {"nested": "value"}, "array": [1, 2]}'
    
    def test_extract_json_from_text_not_found(self, processor):
        """Test extracting JSON when not found"""
        text = 'No JSON here'
        result = processor._extract_json_from_text(text)
        assert result is None
    
    def test_extract_human_readable_from_text_header(self, processor):
        """Test extracting human-readable report with header"""
        text = """
        Some JSON here
        
        HUMAN-READABLE REPORT:
        
        This is a professional report about the assessment.
        It contains multiple lines and detailed information.
        """
        result = processor._extract_human_readable_from_text(text)
        assert "professional report" in result
        assert "multiple lines" in result
    
    def test_extract_human_readable_from_text_after_json(self, processor):
        """Test extracting human-readable report after JSON"""
        text = """
        {"key": "value"}
        
        This is a substantial human-readable report that comes after the JSON.
        It should be extracted as the human-readable portion of the response.
        This text is long enough to be considered substantial content.
        """
        result = processor._extract_human_readable_from_text(text)
        assert "should be extracted" in result
        assert "substantial content" in result
    
    def test_extract_human_readable_from_text_not_found(self, processor):
        """Test extracting human-readable report when not found"""
        text = 'Just some short text'
        result = processor._extract_human_readable_from_text(text)
        assert result is None
    
    def test_is_findings_json_valid(self, processor, sample_findings_json):
        """Test identifying valid findings JSON"""
        result = processor._is_findings_json(sample_findings_json)
        assert result is True
    
    def test_is_findings_json_invalid(self, processor):
        """Test identifying invalid findings JSON"""
        invalid_data = {"some_field": "value"}  # Missing required fields
        result = processor._is_findings_json(invalid_data)
        assert result is False
    
    def test_validate_findings_output_valid(self, processor, sample_findings_json):
        """Test validating valid findings output"""
        # Should not raise any exceptions
        processor._validate_findings_output(sample_findings_json)
    
    def test_validate_findings_output_invalid(self, processor):
        """Test validating invalid findings output"""
        invalid_data = {"component_id": "test"}  # Missing check_status
        
        with pytest.raises(OutputParsingError, match="Findings output validation failed"):
            processor._validate_findings_output(invalid_data)
    
    def test_generate_human_readable_report_passed(self, processor, sample_findings_json):
        """Test generating human-readable report for passed status"""
        report = processor._generate_human_readable_report(sample_findings_json)
        
        assert "**DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT**" in report
        assert "Product Hero Image" in report
        assert "IMG_12345" in report
        assert "**Status:** PASSED" in report
        assert "successfully passed all compliance checks" in report
        assert "No changes needed" in report
    
    def test_generate_human_readable_report_failed(self, processor, sample_findings_json_with_issues):
        """Test generating human-readable report for failed status"""
        report = processor._generate_human_readable_report(sample_findings_json_with_issues)
        
        assert "**DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT**" in report
        assert "Product Hero Image" in report
        assert "IMG_12345" in report
        assert "**Status:** FAILED" in report
        assert "failed compliance assessment" in report
        
        # Check issues section
        assert "**Issues Detected:** 2" in report
        assert "**1. File Format**" in report
        assert "Image format is not supported" in report
        assert "**2. Visual Quality**" in report
        assert "Image is blurry" in report
        
        # Check missing information section
        assert "**Missing Information:** 1" in report
        assert "**1. color_profile**" in report
        assert "Color profile information is missing" in report
        
        # Check recommendations section
        assert "**Recommendations:**" in report
        assert "1. Convert to JPG format" in report
        assert "2. Improve image clarity" in report
        assert "3. Add color profile information" in report
    
    def test_generate_human_readable_report_minimal_data(self, processor):
        """Test generating human-readable report with minimal data"""
        minimal_data = {
            "component_id": "TEST_123",
            "check_status": "FAILED"
        }
        
        report = processor._generate_human_readable_report(minimal_data)
        
        assert "**DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT**" in report
        assert "TEST_123" in report
        assert "**Status:** FAILED" in report
        assert "failed compliance assessment" in report
    
    def test_extract_dual_format_from_text_complete(self, processor, sample_dual_format_response, 
                                                   sample_findings_json, sample_human_readable_report):
        """Test extracting dual format from complete response"""
        result = processor._extract_dual_format_from_text(sample_dual_format_response.text)
        
        assert "json_output" in result
        assert "human_readable_report" in result
        
        # Check JSON output
        json_output = result["json_output"]
        assert json_output["component_id"] == "IMG_12345"
        assert json_output["check_status"] == "PASSED"
        
        # Check human-readable report
        human_readable = result["human_readable_report"]
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in human_readable
    
    def test_extract_dual_format_from_text_json_only(self, processor, sample_json_only_response):
        """Test extracting dual format from JSON-only response"""
        result = processor._extract_dual_format_from_text(sample_json_only_response.text)
        
        assert "json_output" in result
        assert "human_readable_report" in result
        
        # Check JSON output
        json_output = result["json_output"]
        assert json_output["component_id"] == "IMG_12345"
        assert json_output["check_status"] == "PASSED"
        
        # Check that human-readable report was generated
        human_readable = result["human_readable_report"]
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in human_readable
        assert "Product Hero Image" in human_readable
    
    def test_extract_dual_format_from_text_no_json(self, processor):
        """Test extracting dual format when no JSON is found"""
        text = "This is just plain text without any JSON"
        
        with pytest.raises(OutputParsingError, match="Could not extract JSON output"):
            processor._extract_dual_format_from_text(text)
    
    def test_extract_dual_format_from_text_invalid_json(self, processor):
        """Test extracting dual format with invalid JSON"""
        text = """
        ```json
        {"invalid": json, "missing": quotes}
        ```
        """
        
        with pytest.raises(OutputParsingError, match="Invalid JSON output"):
            processor._extract_dual_format_from_text(text)
    
    def test_process_structured_response_complete(self, processor, sample_findings_json, sample_human_readable_report):
        """Test processing structured response with both formats"""
        data = {
            "json_output": sample_findings_json,
            "human_readable_report": sample_human_readable_report
        }
        
        result = processor._process_structured_response(data)
        
        assert result == data
        assert "json_output" in result
        assert "human_readable_report" in result
    
    def test_process_structured_response_json_only(self, processor, sample_findings_json):
        """Test processing structured response with JSON only"""
        result = processor._process_structured_response(sample_findings_json)
        
        assert "json_output" in result
        assert "human_readable_report" in result
        assert result["json_output"] == sample_findings_json
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in result["human_readable_report"]
    
    def test_process_structured_response_invalid(self, processor):
        """Test processing invalid structured response"""
        invalid_data = {"some_field": "value"}
        
        with pytest.raises(OutputParsingError, match="Response does not contain valid findings format"):
            processor._process_structured_response(invalid_data)
    
    def test_parse_response_structured_complete(self, processor, mock_ai_client, 
                                              sample_dual_format_response, sample_findings_json, 
                                              sample_human_readable_report):
        """Test parsing response with complete structured data"""
        structured_data = {
            "json_output": sample_findings_json,
            "human_readable_report": sample_human_readable_report
        }
        mock_ai_client.parse_structured_response.return_value = structured_data
        
        result = processor._parse_response(sample_dual_format_response)
        
        assert result == structured_data
        mock_ai_client.parse_structured_response.assert_called_once()
    
    def test_parse_response_text_format(self, processor, mock_ai_client, sample_dual_format_response):
        """Test parsing response with text format"""
        mock_ai_client.parse_structured_response.return_value = {"text": sample_dual_format_response.text}
        
        result = processor._parse_response(sample_dual_format_response)
        
        assert "json_output" in result
        assert "human_readable_report" in result
        assert result["json_output"]["component_id"] == "IMG_12345"
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in result["human_readable_report"]
    
    def test_parse_response_json_only_structured(self, processor, mock_ai_client, 
                                               sample_dual_format_response, sample_findings_json):
        """Test parsing response with JSON-only structured data"""
        mock_ai_client.parse_structured_response.return_value = sample_findings_json
        
        result = processor._parse_response(sample_dual_format_response)
        
        assert "json_output" in result
        assert "human_readable_report" in result
        assert result["json_output"] == sample_findings_json
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in result["human_readable_report"]
    
    @pytest.mark.asyncio
    async def test_process_success_dual_format(self, processor, mock_ai_client, sample_image_bytes,
                                             sample_metadata, sample_step2_result,
                                             sample_dual_format_response, sample_findings_json,
                                             sample_human_readable_report):
        """Test successful processing with dual format output"""
        mock_ai_client.process_multimodal_request.return_value = sample_dual_format_response
        structured_data = {
            "json_output": sample_findings_json,
            "human_readable_report": sample_human_readable_report
        }
        mock_ai_client.parse_structured_response.return_value = structured_data
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step2_result)
        
        assert result.success is True
        assert "json_output" in result.data
        assert "human_readable_report" in result.data
        assert result.data["json_output"]["component_id"] == "IMG_12345"
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in result.data["human_readable_report"]
        assert result.raw_response == sample_dual_format_response.text
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_success_json_only(self, processor, mock_ai_client, sample_image_bytes,
                                           sample_metadata, sample_step2_result,
                                           sample_json_only_response, sample_findings_json):
        """Test successful processing with JSON-only output"""
        mock_ai_client.process_multimodal_request.return_value = sample_json_only_response
        mock_ai_client.parse_structured_response.return_value = {"text": sample_json_only_response.text}
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step2_result)
        
        assert result.success is True
        assert "json_output" in result.data
        assert "human_readable_report" in result.data
        assert result.data["json_output"]["component_id"] == "IMG_12345"
        assert "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT" in result.data["human_readable_report"]
    
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
                                          sample_image_bytes, sample_metadata, sample_step2_result):
        """Test processing with processing error"""
        from services import GeminiAPIError
        mock_ai_client.process_multimodal_request.side_effect = GeminiAPIError("API error")
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step2_result)
        
        assert result.success is False
        assert "processing error" in result.error_message
        assert "AI request failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_parsing_error(self, processor, mock_ai_client,
                                       sample_image_bytes, sample_metadata,
                                       sample_step2_result):
        """Test processing with parsing error"""
        invalid_response = AIResponse(text="Invalid response without JSON")
        mock_ai_client.process_multimodal_request.return_value = invalid_response
        mock_ai_client.parse_structured_response.return_value = {"text": "Invalid response without JSON"}
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step2_result)
        
        assert result.success is False
        assert "output parsing error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_with_issues(self, processor, mock_ai_client, sample_image_bytes,
                                     sample_metadata, sample_step2_result_with_issues,
                                     sample_findings_json_with_issues):
        """Test processing with issues detected"""
        response_text = f"""
        ```json
        {json.dumps(sample_findings_json_with_issues, indent=2)}
        ```
        """
        response = AIResponse(text=response_text)
        mock_ai_client.process_multimodal_request.return_value = response
        mock_ai_client.parse_structured_response.return_value = {"text": response_text}
        
        result = await processor.process(sample_image_bytes, sample_metadata, sample_step2_result_with_issues)
        
        assert result.success is True
        assert result.data["json_output"]["check_status"] == "FAILED"
        assert len(result.data["json_output"]["issues_detected"]) == 2
        assert len(result.data["json_output"]["missing_information"]) == 1
        assert "**Status:** FAILED" in result.data["human_readable_report"]
        assert "**Issues Detected:** 2" in result.data["human_readable_report"]
        assert "**Missing Information:** 1" in result.data["human_readable_report"]


if __name__ == "__main__":
    pytest.main([__file__])