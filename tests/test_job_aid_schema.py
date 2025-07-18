"""
Unit tests for job aid schema management.

Tests the job aid schema validation functions and utilities.
"""

import pytest
import json
from jsonschema import ValidationError

from schemas.job_aid import (
    DIGITAL_COMPONENT_ANALYSIS_SCHEMA,
    FINDINGS_OUTPUT_SCHEMA,
    get_job_aid_schema,
    get_findings_schema,
    validate_job_aid_data,
    validate_findings_data,
    create_empty_job_aid,
    create_empty_findings_output,
    extract_assessment_summary
)


class TestJobAidSchema:
    """Test cases for job aid schema"""
    
    def test_get_job_aid_schema(self):
        """Test getting the job aid schema"""
        schema = get_job_aid_schema()
        
        assert schema == DIGITAL_COMPONENT_ANALYSIS_SCHEMA
        assert "digital_component_analysis" in schema["properties"]
    
    def test_get_findings_schema(self):
        """Test getting the findings schema"""
        schema = get_findings_schema()
        
        assert schema == FINDINGS_OUTPUT_SCHEMA
        assert "component_id" in schema["properties"]
        assert "check_status" in schema["properties"]
    
    def test_validate_job_aid_data_valid(self):
        """Test validating valid job aid data"""
        data = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "PASS",
                    "summary": "All checks passed"
                }
            }
        }
        
        result = validate_job_aid_data(data)
        assert result is True
    
    def test_validate_job_aid_data_invalid(self):
        """Test validating invalid job aid data"""
        data = {
            "invalid_key": "value"
        }
        
        with pytest.raises(ValidationError):
            validate_job_aid_data(data)
    
    def test_validate_job_aid_data_invalid_enum(self):
        """Test validating job aid data with invalid enum value"""
        data = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "INVALID_STATUS",  # Invalid enum value
                    "summary": "Test summary"
                }
            }
        }
        
        with pytest.raises(ValidationError):
            validate_job_aid_data(data)
    
    def test_validate_findings_data_valid(self):
        """Test validating valid findings data"""
        data = {
            "component_id": "IMG_12345",
            "check_status": "PASSED",
            "issues_detected": [
                {
                    "category": "Visual Quality",
                    "description": "Image is blurry"
                }
            ]
        }
        
        result = validate_findings_data(data)
        assert result is True
    
    def test_validate_findings_data_invalid(self):
        """Test validating invalid findings data"""
        data = {
            "invalid_key": "value"
        }
        
        with pytest.raises(ValidationError):
            validate_findings_data(data)
    
    def test_validate_findings_data_missing_required(self):
        """Test validating findings data with missing required field"""
        data = {
            "component_id": "IMG_12345"
            # Missing required check_status
        }
        
        with pytest.raises(ValidationError):
            validate_findings_data(data)
    
    def test_create_empty_job_aid(self):
        """Test creating an empty job aid structure"""
        job_aid = create_empty_job_aid()
        
        # Validate structure
        assert "digital_component_analysis" in job_aid
        assert "component_specifications" in job_aid["digital_component_analysis"]
        assert "component_qc" in job_aid["digital_component_analysis"]
        assert "overall_assessment" in job_aid["digital_component_analysis"]
        
        # Validate default values
        assert job_aid["digital_component_analysis"]["overall_assessment"]["status"] == "NEEDS_REVIEW"
        
        # Validate against schema
        assert validate_job_aid_data(job_aid) is True
    
    def test_create_empty_findings_output(self):
        """Test creating an empty findings output structure"""
        findings = create_empty_findings_output("IMG_12345", "Product Image")
        
        # Validate structure
        assert findings["component_id"] == "IMG_12345"
        assert findings["component_name"] == "Product Image"
        assert findings["check_status"] == "FAILED"  # Default value
        assert isinstance(findings["issues_detected"], list)
        assert isinstance(findings["missing_information"], list)
        assert isinstance(findings["recommendations"], list)
        
        # Validate against schema
        assert validate_findings_data(findings) is True
    
    def test_extract_assessment_summary_with_data(self):
        """Test extracting assessment summary with complete data"""
        job_aid_data = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "FAIL",
                    "summary": "Several issues found",
                    "critical_issues": [
                        "Image resolution too low",
                        "Missing metadata fields"
                    ]
                }
            }
        }
        
        summary = extract_assessment_summary(job_aid_data)
        
        assert "Assessment Status: FAIL" in summary
        assert "Several issues found" in summary
        assert "Critical Issues:" in summary
        assert "1. Image resolution too low" in summary
        assert "2. Missing metadata fields" in summary
    
    def test_extract_assessment_summary_minimal(self):
        """Test extracting assessment summary with minimal data"""
        job_aid_data = {
            "digital_component_analysis": {
                "overall_assessment": {
                    "status": "PASS"
                }
            }
        }
        
        summary = extract_assessment_summary(job_aid_data)
        
        assert "Assessment Status: PASS" in summary
        assert "meets all compliance requirements" in summary
    
    def test_extract_assessment_summary_empty(self):
        """Test extracting assessment summary with empty data"""
        job_aid_data = {}
        
        summary = extract_assessment_summary(job_aid_data)
        
        assert "Assessment Status: NEEDS_REVIEW" in summary
        assert "requires further review" in summary


if __name__ == "__main__":
    pytest.main([__file__])