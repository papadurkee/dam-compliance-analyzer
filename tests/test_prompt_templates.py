"""
Unit tests for prompt templates.

Tests the prompt template formatting functions and ensures they generate
the expected prompts for each workflow step.
"""

import json
import pytest
from prompts.templates import (
    DAM_ANALYST_ROLE,
    TASK_INSTRUCTIONS,
    OUTPUT_GUIDELINES,
    JOB_AID_PROMPT,
    FINDINGS_PROMPT,
    format_step1_prompt,
    format_step2_prompt,
    format_step3_prompt,
    get_system_instruction
)


class TestPromptTemplates:
    """Test cases for prompt templates"""
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return {
            "component_id": "IMG_12345",
            "component_name": "Product Hero Image",
            "description": "Main product image for website",
            "usage_rights": {
                "license_type": "commercial",
                "expiration_date": "2025-12-31"
            }
        }
    
    @pytest.fixture
    def sample_job_aid_schema(self):
        """Sample job aid schema for testing"""
        return {
            "digital_component_analysis": {
                "component_specifications": {
                    "file_format_requirements": {
                        "allowed_formats": ["JPG", "PNG"]
                    }
                }
            }
        }
    
    @pytest.fixture
    def sample_findings_schema(self):
        """Sample findings schema for testing"""
        return {
            "component_id": "string",
            "check_status": "PASSED or FAILED",
            "issues_detected": [
                {
                    "category": "string",
                    "description": "string"
                }
            ]
        }
    
    @pytest.fixture
    def sample_step1_results(self):
        """Sample Step 1 results for testing"""
        return {
            "notes": "Test notes",
            "job_aid_assessment": {
                "visual_quality": {
                    "assessment": "PASS",
                    "issues": []
                }
            },
            "human_readable_section": "Test summary",
            "next_steps": ["Action 1"]
        }
    
    @pytest.fixture
    def sample_step2_results(self):
        """Sample Step 2 results for testing"""
        return {
            "completed_job_aid": {
                "digital_component_analysis": {
                    "component_specifications": {
                        "assessment": "PASS",
                        "notes": "All specifications met"
                    }
                }
            }
        }
    
    def test_format_step1_prompt_without_metadata(self):
        """Test formatting Step 1 prompt without metadata"""
        prompt = format_step1_prompt()
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert TASK_INSTRUCTIONS in prompt
        assert OUTPUT_GUIDELINES in prompt
        
        # Check that metadata section is not included
        assert "METADATA:" not in prompt
    
    def test_format_step1_prompt_with_metadata(self, sample_metadata):
        """Test formatting Step 1 prompt with metadata"""
        prompt = format_step1_prompt(sample_metadata)
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert TASK_INSTRUCTIONS in prompt
        assert OUTPUT_GUIDELINES in prompt
        
        # Check that metadata section is included
        assert "METADATA:" in prompt
        assert json.dumps(sample_metadata["component_id"]) in prompt
        assert json.dumps(sample_metadata["component_name"]) in prompt
    
    def test_format_step2_prompt(self, sample_job_aid_schema, sample_step1_results):
        """Test formatting Step 2 prompt"""
        prompt = format_step2_prompt(sample_job_aid_schema, sample_step1_results)
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert "STEP 1 RESULTS:" in prompt
        assert json.dumps(sample_step1_results["notes"]) in prompt
        
        # Check that job aid schema is included
        schema_str = json.dumps(sample_job_aid_schema, indent=2)
        assert schema_str.strip() in prompt
    
    def test_format_step2_prompt_with_metadata(self, sample_job_aid_schema, sample_step1_results, sample_metadata):
        """Test formatting Step 2 prompt with metadata"""
        prompt = format_step2_prompt(sample_job_aid_schema, sample_step1_results, sample_metadata)
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert "METADATA:" in prompt
        assert "STEP 1 RESULTS:" in prompt
        
        # Check that metadata is included
        assert json.dumps(sample_metadata["component_id"]) in prompt
    
    def test_format_step3_prompt(self, sample_findings_schema, sample_step2_results):
        """Test formatting Step 3 prompt"""
        prompt = format_step3_prompt(sample_findings_schema, sample_step2_results)
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert "STEP 2 RESULTS:" in prompt
        
        # Check that findings schema is included
        schema_str = json.dumps(sample_findings_schema, indent=2)
        assert schema_str.strip() in prompt
    
    def test_format_step3_prompt_with_metadata(self, sample_findings_schema, sample_step2_results, sample_metadata):
        """Test formatting Step 3 prompt with metadata"""
        prompt = format_step3_prompt(sample_findings_schema, sample_step2_results, sample_metadata)
        
        # Check that all required sections are included
        assert DAM_ANALYST_ROLE in prompt
        assert "METADATA:" in prompt
        assert "STEP 2 RESULTS:" in prompt
        
        # Check that metadata is included
        assert json.dumps(sample_metadata["component_id"]) in prompt
    
    def test_get_system_instruction(self):
        """Test getting system instruction"""
        instruction = get_system_instruction()
        
        # Check that the instruction is not empty
        assert instruction
        assert "Digital Asset Management" in instruction
        assert "analyst" in instruction
        assert "compliance assessment" in instruction


if __name__ == "__main__":
    pytest.main([__file__])