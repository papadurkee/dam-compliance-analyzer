"""
Prompt Templates for DAM Compliance Analyzer

This module contains the exact prompt templates for all workflow steps in the
DAM Compliance Analyzer application. These templates are designed to be used
with the Google Gemini API for multimodal analysis of digital assets.
"""

from typing import Dict, Any, List, Optional
import json


# Step 1: DAM Analysis - Role and Task Format
DAM_ANALYST_ROLE = """
You are a professional Digital Asset Management (DAM) analyst with expertise in compliance assessment and quality control.
Your role is to analyze digital assets against established guidelines, identify compliance issues, and provide structured feedback.
You have extensive experience in evaluating images for brand consistency, technical quality, legal compliance, and metadata completeness.
You are detail-oriented, objective, and able to communicate findings clearly in both technical and non-technical terms.
"""

# Step 1: 4-Part Task Instructions
TASK_INSTRUCTIONS = """
TASK:
Analyze the provided image and metadata for compliance with Digital Asset Management standards. Follow these specific steps:

1. Examine the image for visual quality issues (blurriness, poor lighting, composition problems, etc.)
2. Assess technical specifications (resolution, file format, color profile)
3. Evaluate compliance with brand guidelines and legal requirements
4. Review metadata completeness and accuracy

OUTPUT INSTRUCTIONS:
Provide your analysis in the following structured format:

1. NOTES: Detailed observations about the image and metadata
2. JOB AID ASSESSMENT: Initial assessment of key compliance areas using the job aid structure
3. HUMAN-READABLE SECTION: A clear summary of findings written in professional language
4. NEXT STEPS: Recommended actions based on your analysis
"""

# Step 1: Output Guidelines
OUTPUT_GUIDELINES = """
Your output must follow this exact structure:

```json
{
  "notes": "Detailed observations about visual quality, technical specifications, brand compliance, and metadata...",
  "job_aid_assessment": {
    "visual_quality": {
      "assessment": "PASS/FAIL/NEEDS_REVIEW",
      "issues": ["Issue 1", "Issue 2"]
    },
    "technical_specifications": {
      "assessment": "PASS/FAIL/NEEDS_REVIEW",
      "issues": ["Issue 1", "Issue 2"]
    },
    "brand_compliance": {
      "assessment": "PASS/FAIL/NEEDS_REVIEW",
      "issues": ["Issue 1", "Issue 2"]
    },
    "metadata_completeness": {
      "assessment": "PASS/FAIL/NEEDS_REVIEW",
      "issues": ["Issue 1", "Issue 2"]
    }
  },
  "human_readable_section": "Professional summary of findings...",
  "next_steps": [
    "Recommended action 1",
    "Recommended action 2"
  ]
}
```
"""

# Step 2: Job Aid Assessment Prompt
JOB_AID_PROMPT = """
Using the image and the initial assessment from Step 1, complete the full Digital Component Analysis Job Aid below.
For each field, provide a detailed assessment based on the image and metadata provided.
If information is missing or cannot be determined from the available data, leave the field blank.
Be thorough and specific in your assessments, noting any compliance issues or concerns.

DIGITAL COMPONENT ANALYSIS JOB AID:
{job_aid_schema}

OUTPUT INSTRUCTIONS:
Provide your completed job aid assessment as a valid JSON object following the exact schema provided.
For each field, include an "assessment" (PASS/FAIL/NEEDS_REVIEW) and "notes" with detailed observations.
"""

# Step 3: Findings Transmission Prompt
FINDINGS_PROMPT = """
Based on the completed job aid assessment from Step 2, generate a comprehensive findings report in two formats:

1. STRUCTURED JSON OUTPUT: A machine-readable summary of compliance status
2. HUMAN-READABLE REPORT: A professional communication suitable for stakeholders

The structured JSON output must follow this exact schema:
{findings_schema}

The human-readable report should be formatted as a professional communication with:
- A clear summary of overall compliance status
- Specific issues identified, organized by category
- Missing information that prevented complete assessment
- Actionable recommendations for addressing issues

Both outputs should be consistent with each other and accurately reflect the assessment from Step 2.
"""


def format_step1_prompt(metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Format the complete prompt for Step 1: DAM Analysis.
    
    Args:
        metadata: Optional metadata to include in the prompt
        
    Returns:
        str: Formatted prompt for Step 1
    """
    prompt_parts = [
        DAM_ANALYST_ROLE,
        TASK_INSTRUCTIONS,
        OUTPUT_GUIDELINES
    ]
    
    if metadata:
        metadata_str = json.dumps(metadata, indent=2)
        prompt_parts.insert(1, f"METADATA:\n```json\n{metadata_str}\n```\n")
    
    return "\n\n".join(prompt_parts)


def format_step2_prompt(job_aid_schema: Dict[str, Any], step1_results: Dict[str, Any], 
                        metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Format the complete prompt for Step 2: Job Aid Assessment.
    
    Args:
        job_aid_schema: The complete job aid schema
        step1_results: Results from Step 1
        metadata: Optional metadata to include in the prompt
        
    Returns:
        str: Formatted prompt for Step 2
    """
    job_aid_schema_str = json.dumps(job_aid_schema, indent=2)
    step1_results_str = json.dumps(step1_results, indent=2)
    
    prompt = f"""
{DAM_ANALYST_ROLE}

STEP 1 RESULTS:
```json
{step1_results_str}
```

{JOB_AID_PROMPT.format(job_aid_schema=job_aid_schema_str)}
"""
    
    if metadata:
        metadata_str = json.dumps(metadata, indent=2)
        prompt = f"""
{DAM_ANALYST_ROLE}

METADATA:
```json
{metadata_str}
```

STEP 1 RESULTS:
```json
{step1_results_str}
```

{JOB_AID_PROMPT.format(job_aid_schema=job_aid_schema_str)}
"""
    
    return prompt


def format_step3_prompt(findings_schema: Dict[str, Any], step2_results: Dict[str, Any],
                       metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Format the complete prompt for Step 3: Findings Transmission.
    
    Args:
        findings_schema: The schema for findings output
        step2_results: Results from Step 2
        metadata: Optional metadata to include in the prompt
        
    Returns:
        str: Formatted prompt for Step 3
    """
    findings_schema_str = json.dumps(findings_schema, indent=2)
    step2_results_str = json.dumps(step2_results, indent=2)
    
    prompt = f"""
{DAM_ANALYST_ROLE}

STEP 2 RESULTS:
```json
{step2_results_str}
```

{FINDINGS_PROMPT.format(findings_schema=findings_schema_str)}
"""
    
    if metadata:
        metadata_str = json.dumps(metadata, indent=2)
        prompt = f"""
{DAM_ANALYST_ROLE}

METADATA:
```json
{metadata_str}
```

STEP 2 RESULTS:
```json
{step2_results_str}
```

{FINDINGS_PROMPT.format(findings_schema=findings_schema_str)}
"""
    
    return prompt


def get_system_instruction() -> str:
    """
    Get the system instruction for the Gemini model.
    
    Returns:
        str: System instruction for the model
    """
    return "You are a professional Digital Asset Management (DAM) analyst with expertise in compliance assessment and quality control."