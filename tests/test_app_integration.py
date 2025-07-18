"""
Application Integration Tests for DAM Compliance Analyzer

This module contains integration tests that verify the main application
components work together properly.
"""

import pytest
import asyncio
import json
import os
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image as PILImage
import io

# Import the main app functions
from app import (
    execute_workflow_analysis,
    create_image_upload_section,
    create_metadata_input_section,
    display_workflow_results
)
from utils.image_processing import convert_to_bytes, validate_image_format
from utils.metadata_handler import validate_json_metadata_enhanced, format_for_ai_prompt
from utils.error_handler import ErrorContext


class TestAppIntegration:
    """Test class for application integration testing"""
    
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
            "description": "Test image for integration testing"
        }
    
    def test_image_processing_utilities(self, sample_image_bytes):
        """Test image processing utilities work correctly"""
        
        # Create a mock uploaded file
        class MockUploadedFile:
            def __init__(self, bytes_data, name, size):
                self.name = name
                self.size = size
                self._bytes = bytes_data
            
            def read(self):
                return self._bytes
            
            def seek(self, pos):
                pass
            
            def getvalue(self):
                return self._bytes
        
        mock_file = MockUploadedFile(sample_image_bytes, "test.jpg", len(sample_image_bytes))
        
        # Test image format validation
        is_valid, error_msg = validate_image_format(mock_file)
        assert is_valid is True
        assert error_msg == ""
        
        # Test image conversion
        converted_bytes = convert_to_bytes(mock_file)
        assert converted_bytes == sample_image_bytes
        assert len(converted_bytes) > 0
    
    def test_metadata_processing_utilities(self, sample_metadata):
        """Test metadata processing utilities work correctly"""
        
        # Convert metadata to JSON string
        metadata_json = json.dumps(sample_metadata)
        
        # Test JSON validation
        context = ErrorContext(operation="test", step="validation", component="test")
        validation_result = validate_json_metadata_enhanced(metadata_json, context)
        
        assert validation_result.is_valid is True
        assert validation_result.error_details is None
        
        # Test metadata formatting for AI prompt
        formatted_metadata = format_for_ai_prompt(sample_metadata)
        assert "Component ID: TEST_001" in formatted_metadata
        assert "Component Name: Test Image" in formatted_metadata
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_mocks(self, sample_image_bytes, sample_metadata):
        """Test workflow execution with properly mocked dependencies"""
        
        # Mock the entire workflow engine to return success
        mock_results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {
                "notes": "Test analysis completed",
                "job_aid_assessment": {"format": "PASSED"},
                "human_readable_section": "Test summary",
                "next_steps": ["Test next step"]
            },
            "step2_result": {
                "completed_job_aid": {"component_specifications": {"file_format_requirements": "PASSED"}},
                "assessment_summary": "Test assessment"
            },
            "step3_result": {
                "json_output": {
                    "component_id": "TEST_001",
                    "component_name": "Test Image",
                    "check_status": "PASSED",
                    "issues_detected": [],
                    "missing_information": [],
                    "recommendations": []
                },
                "human_readable_report": "Test report"
            }
        }
        
        # Mock the workflow engine creation and execution
        with patch('app.create_workflow_engine') as mock_create_engine:
            mock_engine = Mock()
            
            # Create a mock workflow state
            mock_state = Mock()
            mock_state.is_complete.return_value = True
            mock_state.error = None
            
            # Set up the mock engine
            mock_engine.execute_workflow = AsyncMock(return_value=mock_state)
            mock_engine.get_workflow_results = Mock(return_value=mock_results)
            
            # Set up the async factory function
            async def mock_create():
                return mock_engine
            
            mock_create_engine.side_effect = mock_create
            
            # Execute workflow
            results = await execute_workflow_analysis(sample_image_bytes, sample_metadata)
            
            # Verify results
            assert results["workflow_complete"] is True
            assert results["error"] is None
            assert "step1_result" in results
            assert "step2_result" in results
            assert "step3_result" in results
            
            # Verify engine was called correctly
            mock_create_engine.assert_called_once()
            mock_engine.execute_workflow.assert_called_once_with(sample_image_bytes, sample_metadata)
            mock_engine.get_workflow_results.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, sample_image_bytes, sample_metadata):
        """Test workflow error handling"""
        
        # Mock the workflow engine to raise an exception
        with patch('app.create_workflow_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Test workflow error")
            
            # Execute workflow
            results = await execute_workflow_analysis(sample_image_bytes, sample_metadata)
            
            # Verify error handling
            assert results["workflow_complete"] is False
            assert "Test workflow error" in results["error"]
    
    def test_error_context_creation(self):
        """Test error context creation and properties"""
        
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
    
    def test_sample_data_availability(self):
        """Test that sample data files are available for testing"""
        
        sample_data_dir = "sample_data"
        
        # Check if sample data directory exists
        if os.path.exists(sample_data_dir):
            # List available sample files
            sample_files = os.listdir(sample_data_dir)
            print(f"Available sample files: {sample_files}")
            
            # Check for expected sample files
            expected_files = [
                "complete_metadata.json",
                "minimal_metadata.json", 
                "problematic_metadata.json"
            ]
            
            for expected_file in expected_files:
                if expected_file in sample_files:
                    file_path = os.path.join(sample_data_dir, expected_file)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        assert isinstance(data, dict)
                        print(f"✅ {expected_file} is valid JSON")
                else:
                    print(f"⚠️ {expected_file} not found")
        else:
            print("⚠️ Sample data directory not found")
    
    def test_component_integration_readiness(self):
        """Test that all components are ready for integration"""
        
        # Test that all required modules can be imported
        try:
            from workflow.engine import create_workflow_engine, WorkflowEngine
            from services.vertex_ai_client import GeminiClient, create_gemini_client
            from utils.image_processing import validate_image_format, convert_to_bytes
            from utils.metadata_handler import validate_json_metadata_enhanced
            from utils.error_handler import ErrorContext, ErrorHandler
            print("✅ All required modules imported successfully")
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")
        
        # Test that key classes can be instantiated (without initialization)
        try:
            from workflow.engine import WorkflowEngine
            from services.vertex_ai_client import GeminiClient
            from utils.error_handler import ErrorHandler
            
            # These should not fail to create (though they may fail to initialize)
            engine = WorkflowEngine()
            client = GeminiClient()
            handler = ErrorHandler()
            
            print("✅ All key classes can be instantiated")
        except Exception as e:
            pytest.fail(f"Failed to instantiate key classes: {e}")


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v", "-s"])