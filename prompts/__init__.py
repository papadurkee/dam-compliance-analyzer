"""
Prompt templates package for DAM Compliance Analyzer.
"""

from .templates import (
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

__all__ = [
    'DAM_ANALYST_ROLE',
    'TASK_INSTRUCTIONS',
    'OUTPUT_GUIDELINES',
    'JOB_AID_PROMPT',
    'FINDINGS_PROMPT',
    'format_step1_prompt',
    'format_step2_prompt',
    'format_step3_prompt',
    'get_system_instruction'
]