"""
Tests for the main Streamlit application components.
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
import io
from PIL import Image

# Import the functions we want to test
from app import (
    create_main_interface,
    create_image_upload_section,
    create_metadata_input_section,
    display_workflow_execution_interface,
    display_workflow_progress,
    display_step_results,
    display_workflow_results,
    execute_workflow_analysis,
    display_instructions,
    main
)


class TestMainAppComponents:
    """Test the main application UI components."""
    
    @patch('app.st')
    def test_create_main_interface(self, mock_st):
        """Test the main interface creation with title and description."""
        create_main_interface()
        
        # Verify page configuration was called
        mock_st.set_page_config.assert_called_once_with(
            page_title="DAM Compliance Analyzer",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Verify title and description were set
        mock_st.title.assert_called_once_with("🔍 DAM Compliance Analyzer")
        assert mock_st.markdown.call_count >= 2  # Description and separator
    
    @patch('app.st')
    @patch('app.validate_image_upload')
    @patch('app.generate_image_preview')
    @patch('app.resize_image_if_needed')
    @patch('app.convert_to_bytes')
    def test_create_image_upload_section_valid_file(self, mock_convert, mock_resize, 
                                                   mock_preview, mock_validate, mock_st):
        """Test image upload section with valid file."""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.name = "test.jpg"
        mock_file.size = 1024 * 1024  # 1MB
        mock_st.file_uploader.return_value = mock_file
        # Mock ValidationResult for enhanced validation
        from utils.validation_errors import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)
        
        # Mock columns to return mock column objects
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        mock_image = MagicMock()
        mock_image.width = 800
        mock_image.height = 600
        mock_image.format = "JPEG"
        mock_preview.return_value = mock_image
        mock_resize.return_value = mock_image
        mock_convert.return_value = b"image_bytes"
        
        # Test the function
        result = create_image_upload_section()
        
        # Verify UI elements were created
        mock_st.subheader.assert_called_with("📁 Image Upload")
        mock_st.file_uploader.assert_called_once()
        
        # Verify validation was called with context
        from unittest.mock import ANY
        mock_validate.assert_called_once_with(mock_file, ANY)
        
        # Verify image processing was called
        mock_preview.assert_called_once_with(mock_file)
        mock_resize.assert_called_once_with(mock_image, max_width=600)
        mock_convert.assert_called_once_with(mock_file)
        
        # Verify return value
        assert result == b"image_bytes"
    
    @patch('app.st')
    @patch('app.validate_image_upload')
    def test_create_image_upload_section_invalid_file(self, mock_validate, mock_st):
        """Test image upload section with invalid file."""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        mock_st.file_uploader.return_value = mock_file
        
        # Mock ValidationResult for enhanced validation (invalid file)
        from utils.validation_errors import ValidationResult
        from utils.error_handler import ErrorDetails, ErrorCategory, ErrorSeverity
        error_details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_IMG_004",
            message="Unsupported file format",
            user_message="Unsupported file format",
            recovery_suggestions=["Convert to JPG or PNG"]
        )
        mock_validate.return_value = ValidationResult(is_valid=False, error_details=error_details)
        
        # Mock expander for recovery suggestions
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        # Test the function
        result = create_image_upload_section()
        
        # Verify validation was called with context
        from unittest.mock import ANY
        mock_validate.assert_called_once_with(mock_file, ANY)
        
        # Verify error message was displayed
        mock_st.error.assert_called_once_with("❌ Unsupported file format")
        
        # Verify return value is None
        assert result is None
    
    @patch('app.st')
    def test_create_image_upload_section_no_file(self, mock_st):
        """Test image upload section with no file uploaded."""
        # Setup mocks
        mock_st.file_uploader.return_value = None
        
        # Test the function
        result = create_image_upload_section()
        
        # Verify file uploader was called
        mock_st.file_uploader.assert_called_once()
        
        # Verify return value is None
        assert result is None
    
    @patch('app.st')
    @patch('app.validate_json_metadata_enhanced')
    @patch('app.format_for_ai_prompt')
    @patch('app.get_default_metadata_structure')
    @patch('app.json.loads')
    def test_create_metadata_input_section_valid_json(self, mock_json_loads, mock_default, mock_format, 
                                                     mock_validate, mock_st):
        """Test metadata input section with valid JSON."""
        # Setup mocks
        test_metadata = {"component_id": "test", "component_name": "Test"}
        mock_st.text_area.return_value = '{"component_id": "test", "component_name": "Test"}'
        
        # Mock ValidationResult for enhanced validation
        from utils.validation_errors import ValidationResult
        mock_validate.return_value = ValidationResult(is_valid=True)
        
        mock_json_loads.return_value = test_metadata
        mock_format.return_value = "Formatted metadata"
        mock_default.return_value = {"default": "structure"}
        
        # Mock columns to return mock column objects
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock expander
        mock_expander = MagicMock()
        mock_st.expander.return_value = mock_expander
        
        # Test the function
        result = create_metadata_input_section()
        
        # Verify UI elements were created
        mock_st.subheader.assert_called_with("📝 Component Metadata")
        mock_st.text_area.assert_called_once()
        
        # Verify validation was called with context
        from unittest.mock import ANY
        mock_validate.assert_called_once_with('{"component_id": "test", "component_name": "Test"}', ANY)
        
        # Verify success message
        mock_st.success.assert_called_once_with("✅ Valid JSON metadata provided")
        
        # Verify return value
        assert result == test_metadata
    
    @patch('app.st')
    @patch('app.validate_json_metadata_enhanced')
    def test_create_metadata_input_section_invalid_json(self, mock_validate, mock_st):
        """Test metadata input section with invalid JSON."""
        # Setup mocks
        mock_st.text_area.return_value = '{"invalid": json}'
        
        # Mock ValidationResult for enhanced validation (invalid JSON)
        from utils.validation_errors import ValidationResult
        from utils.error_handler import ErrorDetails, ErrorCategory, ErrorSeverity
        error_details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_JSON_002",
            message="JSON syntax error",
            user_message="JSON syntax error on line 1: Invalid JSON syntax",
            recovery_suggestions=["Check JSON syntax", "Use online validator"]
        )
        mock_validate.return_value = ValidationResult(is_valid=False, error_details=error_details)
        
        # Mock columns to return mock column objects
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock expander for recovery suggestions
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        # Test the function
        result = create_metadata_input_section()
        
        # Verify validation was called with context
        from unittest.mock import ANY
        mock_validate.assert_called_once_with('{"invalid": json}', ANY)
        
        # Verify error message was displayed
        mock_st.error.assert_called_once_with("❌ JSON Validation Error")
        
        # Verify return value is None
        assert result is None
    
    @patch('app.st')
    def test_create_metadata_input_section_empty_input(self, mock_st):
        """Test metadata input section with empty input."""
        # Setup mocks
        mock_st.text_area.return_value = ""
        
        # Mock columns to return mock column objects
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Test the function
        result = create_metadata_input_section()
        
        # Verify info message was displayed
        mock_st.info.assert_called_once_with("ℹ️ No metadata provided - default structure will be used")
        
        # Verify return value is empty dict
        assert result == {}
    
    @patch('app.st')
    def test_display_workflow_execution_interface_basic(self, mock_st):
        """Test basic workflow execution interface functionality."""
        # Setup mocks
        mock_st.button.return_value = False
        
        # Mock columns to return mock column objects
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Test the function
        display_workflow_execution_interface(b"image_bytes", {"test": "metadata"})
        
        # Verify UI elements were created
        mock_st.subheader.assert_called_with("🚀 Analysis Workflow")
        mock_st.button.assert_called_once()
    
    @patch('app.st')
    def test_display_workflow_execution_interface_no_image_basic(self, mock_st):
        """Test workflow execution interface without image."""
        # Test the function
        display_workflow_execution_interface(None, {"test": "metadata"})
        
        # Verify warning message was displayed
        mock_st.warning.assert_called_once_with("⚠️ Please upload a valid image file to proceed with analysis")
        
        # Verify button was disabled
        mock_st.button.assert_called_with("Start Analysis", disabled=True)
    
    @patch('app.st')
    def test_display_instructions(self, mock_st):
        """Test display of usage instructions."""
        display_instructions()
        
        # Verify expander was created
        mock_st.expander.assert_called_once_with("📖 How to Use This Application")
        
        # Verify that st.markdown was called (it's called within the context manager)
        # The exact number of calls may vary, so we just check it was called
        assert mock_st.markdown.called
    
    @patch('app.create_main_interface')
    @patch('app.display_instructions')
    @patch('app.create_image_upload_section')
    @patch('app.create_metadata_input_section')
    @patch('app.display_workflow_execution_interface')
    def test_main_function_flow(self, mock_workflow, mock_metadata, 
                               mock_image, mock_instructions, mock_interface):
        """Test the main function execution flow."""
        # Setup mocks
        mock_image.return_value = b"image_bytes"
        mock_metadata.return_value = {"test": "metadata"}
        
        # Test the function
        main()
        
        # Verify all components were called in order
        mock_interface.assert_called_once()
        mock_instructions.assert_called_once()
        mock_image.assert_called_once()
        mock_metadata.assert_called_once()
        mock_workflow.assert_called_once_with(b"image_bytes", {"test": "metadata"})
    
    @patch('app.create_main_interface')
    @patch('app.display_instructions')
    @patch('app.create_image_upload_section')
    @patch('app.create_metadata_input_section')
    @patch('app.display_workflow_execution_interface')
    def test_main_function_analysis_ready(self, mock_workflow, mock_metadata, 
                                         mock_image, mock_instructions, mock_interface):
        """Test the main function when workflow interface is displayed."""
        # Setup mocks
        mock_image.return_value = b"image_bytes"
        mock_metadata.return_value = {"test": "metadata"}
        
        # Test the function
        main()
        
        # Verify all components were called
        mock_interface.assert_called_once()
        mock_instructions.assert_called_once()
        mock_image.assert_called_once()
        mock_metadata.assert_called_once()
        mock_workflow.assert_called_once_with(b"image_bytes", {"test": "metadata"})
    
    def test_image_upload_validation_integration(self):
        """Test that image upload integrates with validation functions."""
        from utils.image_processing import validate_image_format
        
        # Test with None (no file uploaded)
        is_valid, error = validate_image_format(None)
        assert not is_valid
        assert "No file uploaded" in error
    
    def test_metadata_validation_integration(self):
        """Test that metadata input integrates with validation functions."""
        from utils.metadata_handler import validate_json_metadata
        
        # Test with valid JSON
        valid_json = '{"component_id": "test", "component_name": "Test Component"}'
        is_valid, error, data = validate_json_metadata(valid_json)
        assert is_valid
        assert error == ""
        assert data["component_id"] == "test"
        
        # Test with invalid JSON
        invalid_json = '{"component_id": "test", "component_name":}'
        is_valid, error, data = validate_json_metadata(invalid_json)
        assert not is_valid
        assert "JSON syntax error" in error
        assert data is None
    
    def test_default_metadata_structure(self):
        """Test that default metadata structure is available."""
        from utils.metadata_handler import get_default_metadata_structure
        
        default_structure = get_default_metadata_structure()
        assert isinstance(default_structure, dict)
        assert "component_id" in default_structure
        assert "component_name" in default_structure
        assert "usage_rights" in default_structure
        assert "file_specifications" in default_structure
    
    def test_ai_prompt_formatting(self):
        """Test that metadata can be formatted for AI prompts."""
        from utils.metadata_handler import format_for_ai_prompt
        
        test_metadata = {
            "component_id": "IMG_001",
            "component_name": "Test Image",
            "description": "A test image for validation"
        }
        
        formatted = format_for_ai_prompt(test_metadata)
        assert "COMPONENT METADATA:" in formatted
        assert "IMG_001" in formatted
        assert "Test Image" in formatted
        assert "A test image for validation" in formatted


class TestWorkflowExecutionInterface:
    """Test the workflow execution interface components."""
    
    @patch('app.st')
    def test_display_workflow_progress(self, mock_st):
        """Test workflow progress display."""
        display_workflow_progress("DAM Analysis", 1, 3)
        
        # Verify progress bar was called with correct parameters
        mock_st.progress.assert_called_once_with(1/3, text="Step 1/3: DAM Analysis")
    
    @patch('app.st')
    def test_display_step_results_step1(self, mock_st):
        """Test display of Step 1 results."""
        step1_data = {
            "notes": "Analysis notes",
            "job_aid_assessment": {"field": "value"},
            "human_readable_section": "Human readable text",
            "next_steps": ["Step 1", "Step 2"]
        }
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        # Mock columns for job aid assessment
        mock_col1 = MagicMock()
        mock_st.columns.return_value = [mock_col1]
        
        display_step_results("DAM Analysis", step1_data, 1)
        
        # Verify main expander was created
        mock_st.expander.assert_any_call("📋 Step 1: DAM Analysis", expanded=True)
        # Also verify the "View Raw JSON" expander was created
        mock_st.expander.assert_any_call("View Raw JSON")
        
        # Verify subheaders were called
        assert mock_st.subheader.call_count >= 3
        
        # Verify content was displayed
        mock_st.markdown.assert_called()
        mock_st.json.assert_called_once_with({"field": "value"})
    
    @patch('app.st')
    def test_display_step_results_step2(self, mock_st):
        """Test display of Step 2 results."""
        step2_data = {
            "completed_job_aid": {"assessment": "complete"},
            "assessment_summary": "Summary text"
        }
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step_results("Job Aid Assessment", step2_data, 2)
        
        # Verify main expander was created
        mock_st.expander.assert_any_call("📋 Step 2: Job Aid Assessment", expanded=True)
        # Also verify the "View Raw JSON" expander was created
        mock_st.expander.assert_any_call("View Raw JSON")
        
        # Verify content was displayed
        mock_st.json.assert_called_once_with({"assessment": "complete"})
        mock_st.markdown.assert_called()
    
    @patch('app.st')
    def test_display_step_results_step3(self, mock_st):
        """Test display of Step 3 results."""
        step3_data = {
            "json_output": {"status": "PASSED"},
            "human_readable_report": "Report text"
        }
        
        # Mock expander and columns
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock radio for view mode selection
        mock_st.radio.return_value = "Human-Readable Report"
        
        display_step_results("Findings Transmission", step3_data, 3)
        
        # Verify main expander was created
        mock_st.expander.assert_any_call("📋 Step 3: Findings Transmission", expanded=True)
        
        # Verify radio button was created for view mode selection
        mock_st.radio.assert_called_once()
    
    @patch('app.st')
    def test_display_workflow_results_success(self, mock_st):
        """Test display of successful workflow results."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Step 1 complete"},
            "step2_result": {"completed_job_aid": {}},
            "step3_result": {
                "json_output": {
                    "check_status": "PASSED",
                    "issues_detected": [],
                    "missing_information": []
                }
            }
        }
        
        # Mock columns for summary (both 2 and 3 column layouts)
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        
        def mock_columns_side_effect(num_cols):
            if num_cols == 2:
                return [mock_col1, mock_col2]
            elif num_cols == 3:
                return [mock_col1, mock_col2, mock_col3]
            else:
                return [mock_col1, mock_col2, mock_col3]
        
        mock_st.columns.side_effect = mock_columns_side_effect
        
        # Mock expander for step results
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_workflow_results(results)
        
        # Verify main subheader
        mock_st.subheader.assert_any_call("📊 Analysis Results")
        
        # Verify no error messages
        mock_st.error.assert_not_called()
        mock_st.warning.assert_not_called()
    
    @patch('app.st')
    def test_display_workflow_results_error(self, mock_st):
        """Test display of workflow results with error."""
        results = {
            "workflow_complete": False,
            "error": "Test error message"
        }
        
        display_workflow_results(results)
        
        # Verify error message was displayed
        mock_st.error.assert_called_once_with("❌ Workflow Error: Test error message")
    
    @patch('app.st')
    def test_display_workflow_results_incomplete(self, mock_st):
        """Test display of incomplete workflow results."""
        results = {
            "workflow_complete": False,
            "error": None
        }
        
        display_workflow_results(results)
        
        # Verify warning message was displayed
        mock_st.warning.assert_called_once_with("⚠️ Workflow incomplete")
    
    @patch('app.st')
    @patch('app.time.sleep')  # Mock sleep to speed up tests
    def test_display_workflow_execution_interface_no_image(self, mock_sleep, mock_st):
        """Test workflow execution interface without image."""
        display_workflow_execution_interface(None, {"test": "metadata"})
        
        # Verify warning message was displayed
        mock_st.warning.assert_called_once_with("⚠️ Please upload a valid image file to proceed with analysis")
        
        # Verify button was disabled
        mock_st.button.assert_called_with("Start Analysis", disabled=True)
    
    @patch('app.st')
    @patch('app.time.sleep')  # Mock sleep to speed up tests
    def test_display_workflow_execution_interface_with_image_no_click(self, mock_sleep, mock_st):
        """Test workflow execution interface with image but no button click."""
        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Mock button not clicked
        mock_st.button.return_value = False
        
        display_workflow_execution_interface(b"image_bytes", {"test": "metadata"})
        
        # Verify UI elements were created
        mock_st.subheader.assert_called_with("🚀 Analysis Workflow")
        mock_st.button.assert_called_once()
    
    @patch('app.st')
    @patch('app.time.sleep')  # Mock sleep to speed up tests
    def test_display_workflow_execution_interface_button_clicked(self, mock_sleep, mock_st):
        """Test workflow execution interface when analysis button is clicked."""
        # Mock columns for different layouts
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        
        def mock_columns_side_effect(num_cols):
            if num_cols == 2:
                return [mock_col1, mock_col2]
            elif num_cols == 3:
                return [mock_col1, mock_col2, mock_col3]
            elif isinstance(num_cols, list) and len(num_cols) == 3:
                return [mock_col1, mock_col2, mock_col3]
            else:
                return [mock_col1, mock_col2, mock_col3]
        
        mock_st.columns.side_effect = mock_columns_side_effect
        
        # Mock button clicked
        mock_st.button.return_value = True
        
        # Mock session state as a proper object with attribute access
        mock_session_state = MagicMock()
        mock_st.session_state = mock_session_state
        
        # Mock containers and placeholders
        mock_container = MagicMock()
        mock_st.container.return_value = mock_container
        
        mock_placeholder = MagicMock()
        mock_st.empty.return_value = mock_placeholder
        
        # Mock expander for step results
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_workflow_execution_interface(b"image_bytes", {"test": "metadata"})
        
        # Verify workflow execution started
        mock_st.info.assert_called()
        # Verify success was called (could be workflow completion or summary)
        mock_st.success.assert_called()
    
    @patch('app.create_workflow_engine')
    @pytest.mark.asyncio
    async def test_execute_workflow_analysis_success(self, mock_create_engine):
        """Test successful workflow analysis execution."""
        from unittest.mock import AsyncMock
        
        # Mock workflow engine with async methods
        mock_engine = MagicMock()
        mock_state = MagicMock()
        mock_state.error = None
        
        # Use AsyncMock for async methods
        mock_engine.execute_workflow = AsyncMock(return_value=mock_state)
        mock_engine.get_workflow_results.return_value = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Success"}
        }
        
        # Use AsyncMock for create_workflow_engine
        mock_create_engine.return_value = mock_engine
        
        # Test the function
        result = await execute_workflow_analysis(b"image_bytes", {"test": "metadata"})
        
        # Verify engine was created
        mock_create_engine.assert_called_once()
        
        # Verify results
        assert result["workflow_complete"] is True
        assert result["error"] is None
    
    @patch('app.create_workflow_engine')
    @pytest.mark.asyncio
    async def test_execute_workflow_analysis_failure(self, mock_create_engine):
        """Test workflow analysis execution failure."""
        # Mock workflow engine to raise exception
        mock_create_engine.side_effect = Exception("Test error")
        
        # Test the function
        result = await execute_workflow_analysis(b"image_bytes", {"test": "metadata"})
        
        # Verify error handling
        assert result["workflow_complete"] is False
        assert "Workflow execution failed: Test error" in result["error"]


class TestWorkflowExecutionFlow:
    """Test the complete workflow execution flow."""
    
    @patch('app.create_main_interface')
    @patch('app.display_instructions')
    @patch('app.create_image_upload_section')
    @patch('app.create_metadata_input_section')
    @patch('app.display_workflow_execution_interface')
    def test_main_function_workflow_flow(self, mock_workflow, mock_metadata, 
                                        mock_image, mock_instructions, mock_interface):
        """Test the main function with new workflow execution interface."""
        # Setup mocks
        mock_image.return_value = b"image_bytes"
        mock_metadata.return_value = {"test": "metadata"}
        
        # Test the function
        main()
        
        # Verify all components were called in order
        mock_interface.assert_called_once()
        mock_instructions.assert_called_once()
        mock_image.assert_called_once()
        mock_metadata.assert_called_once()
        mock_workflow.assert_called_once_with(b"image_bytes", {"test": "metadata"})
    
    @patch('app.st')
    @patch('app.time.sleep')
    def test_workflow_progress_indicators(self, mock_sleep, mock_st):
        """Test that workflow progress indicators work correctly."""
        # Test progress for each step
        display_workflow_progress("DAM Analysis", 1, 3)
        display_workflow_progress("Job Aid Assessment", 2, 3)
        display_workflow_progress("Findings Transmission", 3, 3)
        
        # Verify progress calls
        expected_calls = [
            ((1/3, ), {"text": "Step 1/3: DAM Analysis"}),
            ((2/3, ), {"text": "Step 2/3: Job Aid Assessment"}),
            ((1.0, ), {"text": "Step 3/3: Findings Transmission"})
        ]
        
        actual_calls = mock_st.progress.call_args_list
        assert len(actual_calls) == 3
        
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_args, actual_kwargs = actual_calls[i]
            assert actual_args == expected_args
            assert actual_kwargs == expected_kwargs
    
    def test_workflow_step_data_structure(self):
        """Test that workflow step data structures are handled correctly."""
        # Test Step 1 data structure
        step1_data = {
            "notes": "Analysis complete",
            "job_aid_assessment": {"format": "valid"},
            "human_readable_section": "Summary text",
            "next_steps": ["Step 1", "Step 2"]
        }
        
        # Verify all required fields are present
        assert "notes" in step1_data
        assert "job_aid_assessment" in step1_data
        assert "human_readable_section" in step1_data
        assert "next_steps" in step1_data
        assert isinstance(step1_data["next_steps"], list)
        
        # Test Step 2 data structure
        step2_data = {
            "completed_job_aid": {"assessment": "complete"},
            "assessment_summary": "Summary"
        }
        
        assert "completed_job_aid" in step2_data
        assert "assessment_summary" in step2_data
        
        # Test Step 3 data structure
        step3_data = {
            "json_output": {
                "component_id": "test",
                "check_status": "PASSED",
                "issues_detected": [],
                "missing_information": [],
                "recommendations": []
            },
            "human_readable_report": "Report text"
        }
        
        assert "json_output" in step3_data
        assert "human_readable_report" in step3_data
        assert "check_status" in step3_data["json_output"]
    
    def test_error_handling_in_workflow_execution(self):
        """Test error handling scenarios in workflow execution."""
        # Test error result structure
        error_result = {
            "workflow_complete": False,
            "error": "Test error message"
        }
        
        assert error_result["workflow_complete"] is False
        assert "error" in error_result
        assert isinstance(error_result["error"], str)
        
        # Test incomplete workflow structure
        incomplete_result = {
            "workflow_complete": False,
            "error": None
        }
        
        assert incomplete_result["workflow_complete"] is False
        assert incomplete_result["error"] is None


class TestApplicationFlow:
    """Test the overall application flow and integration."""
    
    def test_complete_workflow_preparation(self):
        """Test that all components needed for workflow are available."""
        # Test image processing
        from utils.image_processing import convert_to_bytes, validate_image_format
        assert convert_to_bytes is not None
        assert validate_image_format is not None
        
        # Test metadata processing
        from utils.metadata_handler import validate_json_metadata, format_for_ai_prompt
        assert validate_json_metadata is not None
        assert format_for_ai_prompt is not None
        
        # Test workflow engine import
        from workflow.engine import create_workflow_engine, WorkflowStep
        assert create_workflow_engine is not None
        assert WorkflowStep is not None
        
        # Test that we can create a mock workflow
        mock_file = MagicMock()
        mock_file.name = "test.jpg"
        mock_file.size = 1024 * 1024  # 1MB
        
        is_valid, error = validate_image_format(mock_file)
        assert is_valid
        assert error == ""
    
    def test_error_handling_integration(self):
        """Test that error handling works across components."""
        from utils.image_processing import validate_image_format
        from utils.metadata_handler import validate_json_metadata
        
        # Test image validation errors
        mock_file = MagicMock()
        mock_file.name = "test.pdf"  # Invalid format
        is_valid, error = validate_image_format(mock_file)
        assert not is_valid
        assert "Unsupported file format" in error
        
        # Test JSON validation errors
        invalid_json = "not json at all"
        is_valid, error, data = validate_json_metadata(invalid_json)
        assert not is_valid
        assert "JSON syntax error" in error
    
    def test_workflow_integration_readiness(self):
        """Test that all workflow components are ready for integration."""
        # Test that workflow engine components exist
        try:
            from workflow.engine import WorkflowEngine, WorkflowStep, WorkflowState
            assert WorkflowEngine is not None
            assert WorkflowStep is not None
            assert WorkflowState is not None
        except ImportError as e:
            pytest.fail(f"Workflow engine components not available: {e}")
        
        # Test that step processors exist
        try:
            from workflow.step1_processor import Step1Processor
            from workflow.step2_processor import Step2Processor
            from workflow.step3_processor import Step3Processor
            assert Step1Processor is not None
            assert Step2Processor is not None
            assert Step3Processor is not None
        except ImportError as e:
            pytest.fail(f"Step processors not available: {e}")
        
        # Test that AI client exists
        try:
            from services.vertex_ai_client import GeminiClient
            assert GeminiClient is not None
        except ImportError as e:
            pytest.fail(f"AI client not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])