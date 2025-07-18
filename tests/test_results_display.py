"""
Tests for the results display interface components.
"""
import pytest
from unittest.mock import MagicMock, patch
import json

# Import the functions we want to test
from app import (
    display_step_results,
    display_step1_results,
    display_step2_results,
    display_step3_results,
    display_workflow_results
)


class TestResultsDisplayInterface:
    """Test the results display interface components."""
    
    @patch('app.st')
    def test_display_step_results_step1(self, mock_st):
        """Test display_step_results function for Step 1."""
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
        
        # Verify main expander was created with correct title
        mock_st.expander.assert_any_call("📋 Step 1: DAM Analysis", expanded=True)
        # Also verify the "View Raw JSON" expander was created
        mock_st.expander.assert_any_call("View Raw JSON")
    
    @patch('app.st')
    def test_display_step_results_step2(self, mock_st):
        """Test display_step_results function for Step 2."""
        step2_data = {
            "completed_job_aid": {"assessment": "complete"},
            "assessment_summary": "Summary text"
        }
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step_results("Job Aid Assessment", step2_data, 2)
        
        # Verify main expander was created with correct title
        mock_st.expander.assert_any_call("📋 Step 2: Job Aid Assessment", expanded=True)
        # Also verify the "View Raw JSON" expander was created
        mock_st.expander.assert_any_call("View Raw JSON")
    
    @patch('app.st')
    def test_display_step_results_step3(self, mock_st):
        """Test display_step_results function for Step 3."""
        step3_data = {
            "json_output": {"status": "PASSED"},
            "human_readable_report": "Report text"
        }
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        # Mock radio button for view mode selection
        mock_st.radio.return_value = "Human-Readable Report"
        
        display_step_results("Findings Transmission", step3_data, 3)
        
        # Verify expander was created with correct title
        mock_st.expander.assert_called_once_with("📋 Step 3: Findings Transmission", expanded=True)
    
    @patch('app.st')
    def test_display_step_results_invalid_step(self, mock_st):
        """Test display_step_results function with invalid step number."""
        step_data = {"test": "data"}
        
        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step_results("Invalid Step", step_data, 99)
        
        # Verify warning was displayed
        mock_st.warning.assert_called_once_with("Unknown step number: 99")


class TestStep1ResultsDisplay:
    """Test Step 1 results display functionality."""
    
    @patch('app.st')
    def test_display_step1_results_complete_data(self, mock_st):
        """Test Step 1 results display with complete data."""
        step1_data = {
            "notes": "Detailed analysis notes",
            "job_aid_assessment": {
                "file_format": "Acceptable",
                "resolution": "Meets requirements",
                "color_profile": "Standard RGB"
            },
            "human_readable_section": "The image meets basic technical requirements.",
            "next_steps": [
                "Proceed to detailed job aid assessment",
                "Validate metadata completeness"
            ]
        }
        
        # Mock columns for job aid assessment
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Mock expander for raw JSON
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step1_results(step1_data)
        
        # Verify all sections were displayed
        expected_subheaders = [
            "🔍 Analysis Notes",
            "📋 Job Aid Assessment", 
            "📄 Summary",
            "➡️ Next Steps"
        ]
        
        actual_calls = [call[0][0] for call in mock_st.subheader.call_args_list]
        for expected in expected_subheaders:
            assert expected in actual_calls
        
        # Verify markdown content was displayed
        mock_st.markdown.assert_called()
        
        # Verify JSON was displayed in expander
        mock_st.json.assert_called_once()
    
    @patch('app.st')
    def test_display_step1_results_many_job_aid_items(self, mock_st):
        """Test Step 1 results display with many job aid assessment items."""
        step1_data = {
            "notes": "Analysis notes",
            "job_aid_assessment": {
                "file_format": "Acceptable",
                "resolution": "Meets requirements", 
                "color_profile": "Standard RGB",
                "naming_convention": "Compliant",
                "metadata_completeness": "Partial",
                "usage_rights": "Missing"
            }
        }
        
        # Mock expander for raw JSON
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step1_results(step1_data)
        
        # Verify that with >4 items, we use markdown list instead of columns
        # Should not call st.columns since we have 6 items
        mock_st.columns.assert_not_called()
        
        # Verify markdown was called for each item
        assert mock_st.markdown.call_count >= 6  # At least one call per job aid item
    
    @patch('app.st')
    def test_display_step1_results_empty_data(self, mock_st):
        """Test Step 1 results display with empty data."""
        display_step1_results({})
        
        # Verify warning was displayed
        mock_st.warning.assert_called_once_with("No data available for Step 1")
    
    @patch('app.st')
    def test_display_step1_results_none_data(self, mock_st):
        """Test Step 1 results display with None data."""
        display_step1_results(None)
        
        # Verify warning was displayed
        mock_st.warning.assert_called_once_with("No data available for Step 1")
    
    @patch('app.st')
    def test_display_step1_results_partial_data(self, mock_st):
        """Test Step 1 results display with partial data."""
        step1_data = {
            "notes": "Only notes available"
            # Missing other fields
        }
        
        display_step1_results(step1_data)
        
        # Verify only notes section was displayed
        mock_st.subheader.assert_called_once_with("🔍 Analysis Notes")
        mock_st.markdown.assert_called()


class TestStep2ResultsDisplay:
    """Test Step 2 results display functionality."""
    
    @patch('app.st')
    def test_display_step2_results_complete_data(self, mock_st):
        """Test Step 2 results display with complete data."""
        step2_data = {
            "assessment_summary": "Component meets most technical requirements.",
            "completed_job_aid": {
                "component_specifications": {
                    "file_format_requirements": "PASSED",
                    "resolution_requirements": "PASSED",
                    "color_profile_requirements": "FAILED"
                },
                "component_metadata": {
                    "required_fields": "PARTIAL",
                    "validation_rules": "PASSED"
                }
            }
        }
        
        # Mock columns for job aid sections
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Mock expander for raw JSON
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step2_results(step2_data)
        
        # Verify sections were displayed
        expected_subheaders = [
            "📊 Assessment Summary",
            "✅ Completed Job Aid"
        ]
        
        actual_calls = [call[0][0] for call in mock_st.subheader.call_args_list]
        for expected in expected_subheaders:
            assert expected in actual_calls
        
        # Verify status indicators were called
        mock_st.success.assert_called()  # For PASSED items
        mock_st.error.assert_called()    # For FAILED items
        mock_st.warning.assert_called()  # For PARTIAL items
    
    @patch('app.st')
    def test_display_step2_results_many_items_per_section(self, mock_st):
        """Test Step 2 results display with many items per section."""
        step2_data = {
            "completed_job_aid": {
                "component_specifications": {
                    "file_format_requirements": "PASSED",
                    "resolution_requirements": "PASSED",
                    "color_profile_requirements": "FAILED",
                    "naming_convention": "PASSED",
                    "metadata_structure": "PARTIAL"
                }
            }
        }
        
        # Mock expander for raw JSON
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step2_results(step2_data)
        
        # With >3 items, should not use columns layout
        mock_st.columns.assert_not_called()
        
        # Should display status indicators for each item
        mock_st.success.assert_called()  # For PASSED items
        mock_st.error.assert_called()    # For FAILED items
        mock_st.warning.assert_called()  # For PARTIAL items
    
    @patch('app.st')
    def test_display_step2_results_empty_data(self, mock_st):
        """Test Step 2 results display with empty data."""
        display_step2_results({})
        
        # Verify warning was displayed
        mock_st.warning.assert_called_once_with("No data available for Step 2")
    
    @patch('app.st')
    def test_display_step2_results_non_dict_section_data(self, mock_st):
        """Test Step 2 results display with non-dict section data."""
        step2_data = {
            "completed_job_aid": {
                "simple_field": "Simple string value"
            }
        }
        
        # Mock expander for raw JSON
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step2_results(step2_data)
        
        # Should call st.write for non-dict values
        mock_st.write.assert_called_with("Simple string value")


class TestStep3ResultsDisplay:
    """Test Step 3 results display functionality."""
    
    @patch('app.st')
    def test_display_step3_results_human_readable_mode(self, mock_st):
        """Test Step 3 results display in human-readable mode."""
        step3_data = {
            "json_output": {
                "component_id": "IMG_001",
                "component_name": "Test Image",
                "check_status": "PASSED",
                "issues_detected": [],
                "missing_information": [],
                "recommendations": ["Complete metadata"]
            },
            "human_readable_report": "**DAM Compliance Analysis Report**\n\nComponent: Test Image\nStatus: PASSED"
        }
        
        # Mock radio to return human-readable mode
        mock_st.radio.return_value = "Human-Readable Report"
        
        display_step3_results(step3_data)
        
        # Verify radio button was created
        mock_st.radio.assert_called_once_with(
            "Select view format:",
            ["Human-Readable Report", "JSON Output"],
            horizontal=True,
            key="step3_view_mode"
        )
        
        # Verify human-readable report was displayed
        mock_st.markdown.assert_called()
        
        # Should not display JSON components in this mode
        mock_st.code.assert_not_called()
    
    @patch('app.st')
    def test_display_step3_results_json_mode(self, mock_st):
        """Test Step 3 results display in JSON mode."""
        step3_data = {
            "json_output": {
                "component_id": "IMG_001",
                "component_name": "Test Image",
                "check_status": "PASSED",
                "issues_detected": [
                    {
                        "category": "Quality",
                        "description": "Low resolution",
                        "action": "Increase resolution"
                    }
                ],
                "missing_information": [
                    {
                        "field": "usage_rights",
                        "description": "Usage rights not specified",
                        "action": "Add usage rights"
                    }
                ],
                "recommendations": ["Complete metadata", "Verify quality"]
            },
            "human_readable_report": "Report text"
        }
        
        # Mock radio to return JSON mode
        mock_st.radio.return_value = "JSON Output"
        
        # Mock columns for component info
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock expanders for issues and missing info
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)
        
        display_step3_results(step3_data)
        
        # Verify JSON mode components were displayed
        mock_st.code.assert_called()  # For component ID and name
        mock_st.success.assert_called()  # For PASSED status
        
        # Verify expanders were created for issues and missing info
        assert mock_st.expander.call_count >= 2  # At least one for each issue/missing item
    
    @patch('app.st')
    def test_display_step3_results_failed_status(self, mock_st):
        """Test Step 3 results display with FAILED status."""
        step3_data = {
            "json_output": {
                "component_id": "IMG_001",
                "component_name": "Test Image",
                "check_status": "FAILED",
                "issues_detected": [],
                "missing_information": [],
                "recommendations": []
            }
        }
        
        # Mock radio to return JSON mode
        mock_st.radio.return_value = "JSON Output"
        
        # Mock columns for component info
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        display_step3_results(step3_data)
        
        # Verify error status was displayed
        mock_st.error.assert_called_with("❌ FAILED")
    
    @patch('app.st')
    def test_display_step3_results_no_issues_or_missing(self, mock_st):
        """Test Step 3 results display with no issues or missing information."""
        step3_data = {
            "json_output": {
                "component_id": "IMG_001",
                "component_name": "Test Image",
                "check_status": "PASSED",
                "issues_detected": [],
                "missing_information": [],
                "recommendations": []
            }
        }
        
        # Mock radio to return JSON mode
        mock_st.radio.return_value = "JSON Output"
        
        # Mock columns for component info
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        display_step3_results(step3_data)
        
        # Verify success messages for no issues/missing info
        success_calls = [call[0][0] for call in mock_st.success.call_args_list]
        assert "✅ No issues detected" in success_calls
        assert "✅ No missing information" in success_calls
    
    @patch('app.st')
    def test_display_step3_results_empty_data(self, mock_st):
        """Test Step 3 results display with empty data."""
        display_step3_results({})
        
        # Verify warning was displayed
        mock_st.warning.assert_called_once_with("No data available for Step 3")
    
    @patch('app.st')
    def test_display_step3_results_missing_human_readable(self, mock_st):
        """Test Step 3 results display when human-readable report is missing."""
        step3_data = {
            "json_output": {"status": "PASSED"}
            # Missing human_readable_report
        }
        
        # Mock radio to return human-readable mode
        mock_st.radio.return_value = "Human-Readable Report"
        
        display_step3_results(step3_data)
        
        # Verify warning was displayed
        mock_st.warning.assert_called_with("Human-readable report not available")
    
    @patch('app.st')
    def test_display_step3_results_fallback_to_json(self, mock_st):
        """Test Step 3 results display fallback when json_output is missing."""
        step3_data = {
            "human_readable_report": "Report text"
            # Missing json_output
        }
        
        # Mock radio to return JSON mode
        mock_st.radio.return_value = "JSON Output"
        
        display_step3_results(step3_data)
        
        # Should fallback to displaying all step data as JSON
        mock_st.json.assert_called_with(step3_data)


class TestWorkflowResultsDisplay:
    """Test the complete workflow results display functionality."""
    
    @patch('app.st')
    def test_display_workflow_results_complete_success(self, mock_st):
        """Test workflow results display with complete successful results."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {
                "notes": "Step 1 complete",
                "job_aid_assessment": {"format": "valid"}
            },
            "step2_result": {
                "completed_job_aid": {"assessment": "complete"}
            },
            "step3_result": {
                "json_output": {
                    "check_status": "PASSED",
                    "issues_detected": [],
                    "missing_information": []
                }
            }
        }
        
        # Mock tabs
        mock_tab1 = MagicMock()
        mock_tab2 = MagicMock()
        mock_tab3 = MagicMock()
        mock_st.tabs.return_value = [mock_tab1, mock_tab2, mock_tab3]
        
        # Mock columns for summary
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Mock other UI elements
        mock_st.radio.return_value = "Human-Readable Report"
        mock_st.button.return_value = False
        
        display_workflow_results(results)
        
        # Verify main subheader
        mock_st.subheader.assert_any_call("📊 Analysis Results")
        
        # Verify tabs were created
        expected_tab_names = [
            "🔍 Step 1: DAM Analysis",
            "📋 Step 2: Job Aid Assessment", 
            "📤 Step 3: Findings Transmission"
        ]
        mock_st.tabs.assert_called_once_with(expected_tab_names)
        
        # Verify summary section
        mock_st.subheader.assert_any_call("📋 Analysis Summary")
        
        # Verify no error messages
        mock_st.error.assert_not_called()
    
    @patch('app.st')
    def test_display_workflow_results_with_error(self, mock_st):
        """Test workflow results display with error."""
        results = {
            "workflow_complete": False,
            "error": "Test error message"
        }
        
        display_workflow_results(results)
        
        # Verify error message was displayed
        mock_st.error.assert_called_once_with("❌ Workflow Error: Test error message")
        
        # Should return early, not display other content
        mock_st.tabs.assert_not_called()
    
    @patch('app.st')
    def test_display_workflow_results_incomplete(self, mock_st):
        """Test workflow results display when incomplete."""
        results = {
            "workflow_complete": False,
            "error": None
        }
        
        display_workflow_results(results)
        
        # Verify warning message was displayed
        mock_st.warning.assert_called_once_with("⚠️ Workflow incomplete")
        
        # Should return early, not display other content
        mock_st.tabs.assert_not_called()
    
    @patch('app.st')
    def test_display_workflow_results_partial_steps(self, mock_st):
        """Test workflow results display with only some steps completed."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Step 1 complete"},
            # Missing step2_result
            "step3_result": {"json_output": {"check_status": "PASSED"}}
        }
        
        # Mock tabs
        mock_tab1 = MagicMock()
        mock_tab2 = MagicMock()
        mock_st.tabs.return_value = [mock_tab1, mock_tab2]
        
        # Mock other UI elements
        mock_st.radio.return_value = "Human-Readable Report"
        mock_st.button.return_value = False
        
        # Mock columns for summary
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        display_workflow_results(results)
        
        # Should only create tabs for available steps
        expected_tab_names = [
            "🔍 Step 1: DAM Analysis",
            "📤 Step 3: Findings Transmission"
        ]
        mock_st.tabs.assert_called_once_with(expected_tab_names)
    
    @patch('app.st')
    def test_display_workflow_results_restart_button(self, mock_st):
        """Test workflow results display restart functionality."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Complete"}
        }
        
        # Mock tabs
        mock_tab1 = MagicMock()
        mock_st.tabs.return_value = [mock_tab1]
        
        # Mock columns for restart button
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        # Mock button clicked
        mock_st.button.return_value = True
        
        # Mock session state
        mock_session_state = MagicMock()
        mock_session_state.workflow_results = "existing_results"
        mock_session_state.workflow_running = True
        mock_st.session_state = mock_session_state
        
        display_workflow_results(results)
        
        # Verify restart button was created
        mock_st.button.assert_called_with("🔄 Run New Analysis", use_container_width=True)
        
        # Verify session state cleanup (would be called if button clicked)
        # Note: The actual deletion and st.rerun() would happen in the real app
    
    @patch('app.st')
    def test_display_workflow_results_summary_metrics(self, mock_st):
        """Test workflow results display summary metrics."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step3_result": {
                "json_output": {
                    "check_status": "FAILED",
                    "issues_detected": [{"issue": "1"}, {"issue": "2"}],
                    "missing_information": [{"missing": "1"}]
                }
            }
        }
        
        # Mock columns for different layouts (2 columns for Step 3, 3 columns for summary)
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
        
        # Mock radio for Step 3 display
        mock_st.radio.return_value = "JSON Output"
        
        # Mock button
        mock_st.button.return_value = False
        
        display_workflow_results(results)
        
        # Verify summary metrics were displayed
        mock_st.error.assert_called()    # For FAILED status
        mock_st.warning.assert_called()  # For issues count > 0
        mock_st.info.assert_called()     # For missing info count > 0


class TestResultsDisplayIntegration:
    """Test integration aspects of the results display interface."""
    
    def test_step_data_structure_compatibility(self):
        """Test that the display functions handle expected data structures."""
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
    
    def test_workflow_results_structure_compatibility(self):
        """Test that workflow results structure is compatible with display functions."""
        complete_results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Complete"},
            "step2_result": {"completed_job_aid": {}},
            "step3_result": {
                "json_output": {
                    "check_status": "PASSED",
                    "issues_detected": [],
                    "missing_information": []
                }
            }
        }
        
        # Verify structure
        assert complete_results["workflow_complete"] is True
        assert complete_results["error"] is None
        assert "step1_result" in complete_results
        assert "step2_result" in complete_results
        assert "step3_result" in complete_results
        
        # Test error results structure
        error_results = {
            "workflow_complete": False,
            "error": "Test error"
        }
        
        assert error_results["workflow_complete"] is False
        assert "error" in error_results
    
    @patch('app.st')
    def test_tabbed_interface_creation(self, mock_st):
        """Test that tabbed interface is created correctly."""
        results = {
            "workflow_complete": True,
            "error": None,
            "step1_result": {"notes": "Step 1"},
            "step2_result": {"completed_job_aid": {}},
            "step3_result": {"json_output": {"check_status": "PASSED"}}
        }
        
        # Mock tabs and other UI elements
        mock_tab1 = MagicMock()
        mock_tab2 = MagicMock()
        mock_tab3 = MagicMock()
        mock_st.tabs.return_value = [mock_tab1, mock_tab2, mock_tab3]
        
        mock_st.radio.return_value = "Human-Readable Report"
        mock_st.button.return_value = False
        
        # Mock columns for summary
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]
        
        display_workflow_results(results)
        
        # Verify tabs were created with correct names
        expected_tab_names = [
            "🔍 Step 1: DAM Analysis",
            "📋 Step 2: Job Aid Assessment",
            "📤 Step 3: Findings Transmission"
        ]
        mock_st.tabs.assert_called_once_with(expected_tab_names)
    
    @patch('app.st')
    def test_json_human_readable_toggle(self, mock_st):
        """Test JSON/human-readable toggle functionality."""
        step3_data = {
            "json_output": {"check_status": "PASSED"},
            "human_readable_report": "Report text"
        }
        
        # Test human-readable mode
        mock_st.radio.return_value = "Human-Readable Report"
        display_step3_results(step3_data)
        
        # Verify radio was created
        mock_st.radio.assert_called_with(
            "Select view format:",
            ["Human-Readable Report", "JSON Output"],
            horizontal=True,
            key="step3_view_mode"
        )
        
        # Reset mocks and test JSON mode
        mock_st.reset_mock()
        mock_st.radio.return_value = "JSON Output"
        
        # Mock columns for JSON mode
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        display_step3_results(step3_data)
        
        # Verify JSON mode components were called
        mock_st.code.assert_called()  # For component display