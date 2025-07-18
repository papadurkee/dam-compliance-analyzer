"""
Full Integration Tests for DAM Compliance Analyzer

This module contains comprehensive integration tests that verify the complete
workflow from image upload through final results generation.
"""

import pytest
import asyncio
import json
import os
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image as PILImage
import io

# Import the modules we're testing
from workflow.engine import create_workflow_engine, WorkflowEngine, WorkflowStep
from services.vertex_ai_client import GeminiClient, MultimodalRequest, AIResponse
from utils.image_processing import convert_to_bytes, validate_image_format
from utils.metadata_handler import validate_json_metadata_enhanced, format_for_ai_prompt
from utils.error_handler import ErrorContext


class TestFullIntegration:
    """Test class for full integration testing"""
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing"""
        # Create a simple test image
        img = PILImage.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing"""
        return {
            "component_id": "TEST_001",
            "component_name": "Test Image",
            "description": "Test image for integration testing",
            "usage_rights": {
                "commercial_use": True,
                "editorial_use": True
            },
            "file_specifications": {
                "format": "JPEG",
                "resolution": "100x100"
            }
        }
    
    @pytest.fixture
    def mock_ai_responses(self):
        """Mock AI responses for each workflow step"""
        return {
            "step1": AIResponse(
                text="""
                **Analysis Notes:**
                The uploaded image is a simple red square with dimensions 100x100 pixels in JPEG format.
                
                **Job Aid Assessment:**
                {
                    "file_format": "Acceptable - JPEG format",
                    "resolution": "Low resolution - 100x100",
                    "color_profile": "Standard RGB"
                }
                
                **Human-Readable Section:**
                The image meets basic format requirements but has low resolution.
                
                **Next Steps:**
                1. Proceed to detailed job aid assessment
                2. Check resolution requirements
                3. Validate metadata completeness
                """
            ),
            "step2": AIResponse(
                text="""
                {
                    "component_specifications": {
                        "file_format_requirements": "PASSED",
                        "resolution_requirements": "FAILED",
                        "color_profile_requirements": "PASSED"
                    },
                    "component_metadata": {
                        "required_fields": "PASSED",
                        "validation_rules": "PASSED"
                    },
                    "component_qc": {
                        "visual_quality_checks": "PASSED",
                        "technical_quality_checks": "PARTIAL"
                    }
                }
                
                **Assessment Summary:**
                Component meets most requirements but fails resolution standards.
                """
            ),
            "step3": AIResponse(
                text="""
                {
                    "component_id": "TEST_001",
                    "component_name": "Test Image",
                    "check_status": "FAILED",
                    "issues_detected": [
                        {
                            "category": "Resolution",
                            "description": "Image resolution is below minimum requirements",
                            "action": "Provide higher resolution image"
                        }
                    ],
                    "missing_information": [],
                    "recommendations": [
                        "Upload image with minimum 300x300 resolution",
                        "Ensure image quality meets standards"
                    ]
                }
                
                **Human-Readable Report:**
                
                # DAM Compliance Analysis Report
                
                **Component:** Test Image (TEST_001)
                **Status:** FAILED
                
                ## Issues Detected
                
                1. **Resolution Issue**: Image resolution is below minimum requirements
                   - Action: Provide higher resolution image
                
                ## Recommendations
                
                - Upload image with minimum 300x300 resolution
                - Ensure image quality meets standards
                
                The component requires resolution improvements before approval.
                """
            )
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, sample_image_bytes, sample_metadata, mock_ai_responses):
        """Test the complete workflow integration from start to finish"""
        
        # Mock Streamlit secrets
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.__contains__.return_value = True
            mock_secrets.__getitem__.return_value = "fake_api_key"
            
            # Mock the Gemini client
            with patch('services.vertex_ai_client.create_gemini_client') as mock_create_client:
                mock_client = AsyncMock(spec=GeminiClient)
                
                # Configure mock responses for each step
                mock_client.process_multimodal_request.side_effect = [
                    mock_ai_responses["step1"],
                    mock_ai_responses["step2"],
                    mock_ai_responses["step3"]
                ]
                
                mock_create_client.return_value = mock_client
                
                # Create workflow engine
                engine = await create_workflow_engine()
                
                # Execute complete workflow
                final_state = await engine.execute_workflow(sample_image_bytes, sample_metadata)
                
                # Verify workflow completed
                assert final_state.is_complete()
                assert final_state.error is None
                
                # Verify all steps were executed
                assert WorkflowStep.STEP1_DAM_ANALYSIS in final_state.completed_steps
                assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT in final_state.completed_steps
                assert WorkflowStep.STEP3_FINDINGS_TRANSMISSION in final_state.completed_steps
                
                # Get workflow results
                results = engine.get_workflow_results()
                
                # Verify results structure
                assert results["workflow_complete"] is True
                assert results["error"] is None
                assert "step1_result" in results
                assert "step2_result" in results
                assert "step3_result" in results
                
                # Verify Step 1 results
                step1_result = results["step1_result"]
                assert "notes" in step1_result
                assert "job_aid_assessment" in step1_result
                assert "human_readable_section" in step1_result
                assert "next_steps" in step1_result
                
                # Verify Step 2 results
                step2_result = results["step2_result"]
                assert "completed_job_aid" in step2_result
                assert "assessment_summary" in step2_result
                
                # Verify Step 3 results
                step3_result = results["step3_result"]
                assert "json_output" in step3_result
                assert "human_readable_report" in step3_result
                
                # Verify final JSON output structure
                json_output = step3_result["json_output"]
                assert json_output["component_id"] == "TEST_001"
                assert json_output["component_name"] == "Test Image"
                assert json_output["check_status"] == "FAILED"
                assert len(json_output["issues_detected"]) > 0
                assert len(json_output["recommendations"]) > 0
                
                # Verify AI client was called correctly
                assert mock_client.process_multimodal_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, sample_image_bytes, sample_metadata):
        """Test workflow error handling and recovery"""
        
        # Mock Streamlit secrets
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.__contains__.return_value = True
            mock_secrets.__getitem__.return_value = "fake_api_key"
            
            # Mock the Gemini client to fail on Step 2
            with patch('services.vertex_ai_client.create_gemini_client') as mock_create_client:
                mock_client = AsyncMock(spec=GeminiClient)
                
                # Step 1 succeeds
                mock_client.process_multimodal_request.side_effect = [
                    AIResponse(text="Step 1 success"),
                    Exception("Step 2 API failure"),  # Step 2 fails
                ]
                
                mock_create_client.return_value = mock_client
                
                # Create workflow engine
                engine = await create_workflow_engine()
                
                # Execute workflow (should fail at Step 2)
                final_state = await engine.execute_workflow(sample_image_bytes, sample_metadata)
                
                # Verify workflow failed appropriately
                assert not final_state.is_complete()
                assert final_state.error is not None
                assert final_state.error_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT
                
                # Verify Step 1 completed but Step 2 and 3 did not
                assert WorkflowStep.STEP1_DAM_ANALYSIS in final_state.completed_steps
                assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT not in final_state.completed_steps
                assert WorkflowStep.STEP3_FINDINGS_TRANSMISSION not in final_state.completed_steps
                
                # Get workflow results
                results = engine.get_workflow_results()
                
                # Verify error propagation
                assert results["workflow_complete"] is False
                assert results["error"] is not None
                assert "step1_result" in results  # Step 1 should have results
                assert "step2_result" not in results  # Step 2 should not have results
                assert "step3_result" not in results  # Step 3 should not have results
    
    @pytest.mark.asyncio
    async def test_workflow_resume_functionality(self, sample_image_bytes, sample_metadata, mock_ai_responses):
        """Test workflow resume functionality after failure"""
        
        # Mock Streamlit secrets
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.__contains__.return_value = True
            mock_secrets.__getitem__.return_value = "fake_api_key"
            
            # Mock the Gemini client
            with patch('services.vertex_ai_client.create_gemini_client') as mock_create_client:
                mock_client = AsyncMock(spec=GeminiClient)
                mock_create_client.return_value = mock_client
                
                # First execution: Step 1 succeeds, Step 2 fails
                mock_client.process_multimodal_request.side_effect = [
                    mock_ai_responses["step1"],
                    Exception("Temporary failure")
                ]
                
                # Create workflow engine
                engine = await create_workflow_engine()
                
                # Execute workflow (should fail at Step 2)
                failed_state = await engine.execute_workflow(sample_image_bytes, sample_metadata)
                
                # Verify failure
                assert not failed_state.is_complete()
                assert WorkflowStep.STEP1_DAM_ANALYSIS in failed_state.completed_steps
                
                # Now resume from Step 2 with successful responses
                mock_client.process_multimodal_request.side_effect = [
                    mock_ai_responses["step2"],
                    mock_ai_responses["step3"]
                ]
                
                # Resume workflow from Step 2
                resumed_state = await engine.execute_workflow(
                    sample_image_bytes, 
                    sample_metadata,
                    start_step=WorkflowStep.STEP2_JOB_AID_ASSESSMENT,
                    previous_state=failed_state
                )
                
                # Verify successful completion
                assert resumed_state.is_complete()
                assert resumed_state.error is None
                assert len(resumed_state.completed_steps) == 3
    
    def test_image_processing_integration(self, sample_image_bytes):
        """Test image processing utilities integration"""
        
        # Create a mock uploaded file
        class MockUploadedFile:
            def __init__(self, bytes_data, name, size):
                self.name = name
                self.size = size
                self._bytes = bytes_data
                self._io = io.BytesIO(bytes_data)
            
            def read(self):
                return self._bytes
            
            def seek(self, pos):
                self._io.seek(pos)
            
            def getvalue(self):
                return self._bytes
        
        mock_file = MockUploadedFile(sample_image_bytes, "test.jpg", len(sample_image_bytes))
        
        # Test image format validation - it returns a tuple (bool, str)
        is_valid, error_msg = validate_image_format(mock_file)
        assert is_valid is True
        assert error_msg == ""
        
        # Test image conversion
        converted_bytes = convert_to_bytes(mock_file)
        assert converted_bytes == sample_image_bytes
        assert len(converted_bytes) > 0
    
    def test_metadata_processing_integration(self, sample_metadata):
        """Test metadata processing utilities integration"""
        
        # Convert metadata to JSON string
        metadata_json = json.dumps(sample_metadata)
        
        # Test JSON validation
        context = ErrorContext(operation="test", step="validation", component="test")
        validation_result = validate_json_metadata_enhanced(metadata_json, context)
        
        assert validation_result.is_valid is True
        assert validation_result.error_details is None
        
        # Test metadata formatting for AI prompt
        formatted_metadata = format_for_ai_prompt(sample_metadata)
        # Check for the actual format used by the formatter
        assert "Component ID: TEST_001" in formatted_metadata
        assert "Component Name: Test Image" in formatted_metadata
        assert "Usage Rights" in formatted_metadata
    
    def test_error_context_integration(self):
        """Test error context and handling integration"""
        
        # Create error context
        context = ErrorContext(
            operation="integration_test",
            step="validation",
            component="test_component"
        )
        
        # Verify context properties
        assert context.operation == "integration_test"
        assert context.step == "validation"
        assert context.component == "test_component"
        assert context.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_sample_data(self):
        """Test end-to-end workflow with actual sample data files"""
        
        # Load sample data if available
        sample_data_dir = "sample_data"
        if not os.path.exists(sample_data_dir):
            pytest.skip("Sample data directory not found")
        
        # Try to load sample metadata
        metadata_file = os.path.join(sample_data_dir, "complete_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                sample_metadata = json.load(f)
        else:
            sample_metadata = {
                "component_id": "SAMPLE_001",
                "component_name": "Sample Test Image"
            }
        
        # Create sample image
        img = PILImage.new('RGB', (300, 300), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        sample_image_bytes = img_bytes.getvalue()
        
        # Mock successful AI responses
        mock_responses = {
            "step1": AIResponse(text="Step 1 analysis complete"),
            "step2": AIResponse(text='{"component_specifications": {"file_format_requirements": "PASSED"}}'),
            "step3": AIResponse(text='{"component_id": "SAMPLE_001", "check_status": "PASSED", "issues_detected": [], "missing_information": [], "recommendations": []}')
        }
        
        # Mock Streamlit secrets
        with patch('streamlit.secrets') as mock_secrets:
            mock_secrets.__contains__.return_value = True
            mock_secrets.__getitem__.return_value = "fake_api_key"
            
            # Execute workflow with mocked AI
            with patch('services.vertex_ai_client.create_gemini_client') as mock_create_client:
                mock_client = AsyncMock(spec=GeminiClient)
                mock_client.process_multimodal_request.side_effect = [
                    mock_responses["step1"],
                    mock_responses["step2"],
                    mock_responses["step3"]
                ]
                mock_create_client.return_value = mock_client
                
                # Create and execute workflow
                engine = await create_workflow_engine()
                final_state = await engine.execute_workflow(sample_image_bytes, sample_metadata)
                
                # Verify successful completion
                assert final_state.is_complete()
                assert final_state.error is None
                
                # Get and verify results
                results = engine.get_workflow_results()
                assert results["workflow_complete"] is True
                assert "step1_result" in results
                assert "step2_result" in results
                assert "step3_result" in results


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v"])