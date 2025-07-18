"""
Schema management package for DAM Compliance Analyzer.
"""

from .job_aid import (
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

__all__ = [
    'DIGITAL_COMPONENT_ANALYSIS_SCHEMA',
    'FINDINGS_OUTPUT_SCHEMA',
    'get_job_aid_schema',
    'get_findings_schema',
    'validate_job_aid_data',
    'validate_findings_data',
    'create_empty_job_aid',
    'create_empty_findings_output',
    'extract_assessment_summary'
]