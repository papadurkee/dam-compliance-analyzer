"""
Job Aid Schema Management

This module defines the complete job aid schema for the DAM Compliance Analyzer
and provides validation functions to ensure data conforms to the schema.
"""

from typing import Dict, Any, List, Optional, Union, Literal
import json
import jsonschema
from jsonschema import validate, ValidationError


# Complete Digital Component Analysis Job Aid Schema
DIGITAL_COMPONENT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "digital_component_analysis": {
            "type": "object",
            "properties": {
                "instructions": {
                    "type": "string",
                    "description": "General instructions for completing the job aid"
                },
                "component_specifications": {
                    "type": "object",
                    "properties": {
                        "file_format_requirements": {
                            "type": "object",
                            "properties": {
                                "allowed_formats": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "format_restrictions": {
                                    "type": "string"
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "resolution_requirements": {
                            "type": "object",
                            "properties": {
                                "minimum_resolution": {
                                    "type": "string"
                                },
                                "optimal_resolution": {
                                    "type": "string"
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "color_profile_requirements": {
                            "type": "object",
                            "properties": {
                                "required_profile": {
                                    "type": "string"
                                },
                                "color_space": {
                                    "type": "string"
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "naming_convention_requirements": {
                            "type": "object",
                            "properties": {
                                "pattern": {
                                    "type": "string"
                                },
                                "examples": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "assessment": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "notes": {
                            "type": "string"
                        }
                    }
                },
                "component_metadata": {
                    "type": "object",
                    "properties": {
                        "required_fields": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "optional_fields": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "validation_rules": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "string"
                            }
                        },
                        "assessment": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "notes": {
                            "type": "string"
                        }
                    }
                },
                "component_qc": {
                    "type": "object",
                    "properties": {
                        "visual_quality_checks": {
                            "type": "object",
                            "properties": {
                                "clarity": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "lighting": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "composition": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "color_accuracy": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "technical_quality_checks": {
                            "type": "object",
                            "properties": {
                                "compression_artifacts": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "noise_levels": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "sharpness": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "compliance_checks": {
                            "type": "object",
                            "properties": {
                                "brand_guidelines": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "legal_requirements": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "accessibility_standards": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "assessment": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "notes": {
                            "type": "string"
                        }
                    }
                },
                "component_linking": {
                    "type": "object",
                    "properties": {
                        "relationship_requirements": {
                            "type": "object",
                            "properties": {
                                "required_links": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "dependency_checks": {
                            "type": "object",
                            "properties": {
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "assessment": {
                                    "type": "string",
                                    "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                },
                                "notes": {
                                    "type": "string"
                                }
                            }
                        },
                        "assessment": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "notes": {
                            "type": "string"
                        }
                    }
                },
                "material_distribution_package_qc": {
                    "type": "object",
                    "properties": {
                        "package_integrity_checks": {
                            "type": "object",
                            "properties": {
                                "completeness": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "consistency": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "distribution_readiness_checks": {
                            "type": "object",
                            "properties": {
                                "channel_requirements": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "delivery_specifications": {
                                    "type": "object",
                                    "properties": {
                                        "assessment": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                                        },
                                        "notes": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "assessment": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "notes": {
                            "type": "string"
                        }
                    }
                },
                "overall_assessment": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["PASS", "FAIL", "NEEDS_REVIEW"]
                        },
                        "summary": {
                            "type": "string"
                        },
                        "critical_issues": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "recommendations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["status"]
                }
            }
        }
    },
    "required": ["digital_component_analysis"]
}


# Findings Output Schema for Step 3
FINDINGS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "component_id": {
            "type": "string",
            "description": "Unique identifier for the digital component"
        },
        "component_name": {
            "type": "string",
            "description": "Name of the digital component"
        },
        "check_status": {
            "type": "string",
            "enum": ["PASSED", "FAILED", "PARTIAL"],
            "description": "Overall status of the compliance check"
        },
        "issues_detected": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category of the issue (e.g., 'Visual Quality', 'Technical Specifications')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue"
                    },
                    "action": {
                        "type": "string",
                        "description": "Recommended action to resolve the issue"
                    }
                },
                "required": ["category", "description"]
            },
            "description": "List of compliance issues detected"
        },
        "missing_information": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "Field or attribute with missing information"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what information is missing"
                    },
                    "action": {
                        "type": "string",
                        "description": "Recommended action to provide the missing information"
                    }
                },
                "required": ["field", "description"]
            },
            "description": "List of missing information that prevented complete assessment"
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of recommendations for improving compliance"
        }
    },
    "required": ["component_id", "check_status"]
}


def get_job_aid_schema() -> Dict[str, Any]:
    """
    Get the complete job aid schema.
    
    Returns:
        Dict[str, Any]: The complete job aid schema
    """
    return DIGITAL_COMPONENT_ANALYSIS_SCHEMA


def get_findings_schema() -> Dict[str, Any]:
    """
    Get the findings output schema.
    
    Returns:
        Dict[str, Any]: The findings output schema
    """
    return FINDINGS_OUTPUT_SCHEMA


def validate_job_aid_data(data: Dict[str, Any]) -> bool:
    """
    Validate data against the job aid schema.
    
    Args:
        data: The data to validate
        
    Returns:
        bool: True if the data is valid, False otherwise
        
    Raises:
        ValidationError: If the data does not conform to the schema
    """
    try:
        validate(instance=data, schema=DIGITAL_COMPONENT_ANALYSIS_SCHEMA)
        return True
    except ValidationError:
        raise


def validate_findings_data(data: Dict[str, Any]) -> bool:
    """
    Validate data against the findings output schema.
    
    Args:
        data: The data to validate
        
    Returns:
        bool: True if the data is valid, False otherwise
        
    Raises:
        ValidationError: If the data does not conform to the schema
    """
    try:
        validate(instance=data, schema=FINDINGS_OUTPUT_SCHEMA)
        return True
    except ValidationError:
        raise


def create_empty_job_aid() -> Dict[str, Any]:
    """
    Create an empty job aid structure with all required fields.
    
    Returns:
        Dict[str, Any]: An empty job aid structure
    """
    return {
        "digital_component_analysis": {
            "instructions": "Complete all sections of this job aid to assess the digital component.",
            "component_specifications": {
                "file_format_requirements": {},
                "resolution_requirements": {},
                "color_profile_requirements": {},
                "naming_convention_requirements": {}
            },
            "component_metadata": {
                "required_fields": [],
                "optional_fields": [],
                "validation_rules": {}
            },
            "component_qc": {
                "visual_quality_checks": {
                    "clarity": {},
                    "lighting": {},
                    "composition": {},
                    "color_accuracy": {}
                },
                "technical_quality_checks": {
                    "compression_artifacts": {},
                    "noise_levels": {},
                    "sharpness": {}
                },
                "compliance_checks": {
                    "brand_guidelines": {},
                    "legal_requirements": {},
                    "accessibility_standards": {}
                }
            },
            "component_linking": {
                "relationship_requirements": {},
                "dependency_checks": {}
            },
            "material_distribution_package_qc": {
                "package_integrity_checks": {
                    "completeness": {},
                    "consistency": {}
                },
                "distribution_readiness_checks": {
                    "channel_requirements": {},
                    "delivery_specifications": {}
                }
            },
            "overall_assessment": {
                "status": "NEEDS_REVIEW",
                "summary": "",
                "critical_issues": [],
                "recommendations": []
            }
        }
    }


def create_empty_findings_output(component_id: str = "", component_name: str = "") -> Dict[str, Any]:
    """
    Create an empty findings output structure with all required fields.
    
    Args:
        component_id: Optional component ID to include
        component_name: Optional component name to include
        
    Returns:
        Dict[str, Any]: An empty findings output structure
    """
    return {
        "component_id": component_id,
        "component_name": component_name,
        "check_status": "FAILED",  # Default to FAILED until explicitly set to PASSED
        "issues_detected": [],
        "missing_information": [],
        "recommendations": []
    }


def extract_assessment_summary(job_aid_data: Dict[str, Any]) -> str:
    """
    Extract an assessment summary from job aid data.
    
    Args:
        job_aid_data: The completed job aid data
        
    Returns:
        str: A summary of the assessment
    """
    try:
        digital_component = job_aid_data.get("digital_component_analysis", {})
        overall = digital_component.get("overall_assessment", {})
        
        status = overall.get("status", "NEEDS_REVIEW")
        summary = overall.get("summary", "")
        critical_issues = overall.get("critical_issues", [])
        
        if not summary:
            if status == "PASS":
                summary = "The digital component meets all compliance requirements."
            elif status == "FAIL":
                summary = "The digital component has compliance issues that need to be addressed."
            else:
                summary = "The digital component requires further review."
        
        result = f"Assessment Status: {status}\n\n{summary}"
        
        if critical_issues:
            result += "\n\nCritical Issues:\n"
            for i, issue in enumerate(critical_issues, 1):
                result += f"{i}. {issue}\n"
        
        return result
        
    except Exception as e:
        return f"Error extracting assessment summary: {str(e)}"