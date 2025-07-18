"""
Workflow Orchestrator for DAM Compliance Analyzer

This module implements the main workflow engine that orchestrates the execution
of all three steps in the DAM Compliance Analyzer workflow. It manages data flow
between steps and provides error handling and recovery for workflow interruptions.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base_processor import (
    BaseProcessor,
    ProcessorResult,
    ProcessorError,
    ValidationError,
    ProcessingError,
    OutputParsingError
)
from .step1_processor import Step1Processor
from .step2_processor import Step2Processor
from .step3_processor import Step3Processor
from services import GeminiClient, create_gemini_client

logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    """Enum for workflow steps"""
    STEP1_DAM_ANALYSIS = 1
    STEP2_JOB_AID_ASSESSMENT = 2
    STEP3_FINDINGS_TRANSMISSION = 3


class WorkflowError(Exception):
    """Base exception for workflow errors"""
    pass


class WorkflowValidationError(WorkflowError):
    """Exception for workflow validation errors"""
    pass


class WorkflowExecutionError(WorkflowError):
    """Exception for workflow execution errors"""
    pass


@dataclass
class WorkflowState:
    """Class to track workflow state and results"""
    current_step: WorkflowStep = WorkflowStep.STEP1_DAM_ANALYSIS
    completed_steps: List[WorkflowStep] = field(default_factory=list)
    results: Dict[WorkflowStep, ProcessorResult] = field(default_factory=dict)
    error: Optional[str] = None
    error_step: Optional[WorkflowStep] = None
    
    def mark_step_complete(self, step: WorkflowStep, result: ProcessorResult) -> None:
        """
        Mark a step as complete and store its result.
        
        Args:
            step: The completed step
            result: The result of the step
        """
        self.results[step] = result
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        
        # Update current step to next step
        if step == WorkflowStep.STEP1_DAM_ANALYSIS:
            self.current_step = WorkflowStep.STEP2_JOB_AID_ASSESSMENT
        elif step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT:
            self.current_step = WorkflowStep.STEP3_FINDINGS_TRANSMISSION
        elif step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION:
            # Workflow complete
            pass
    
    def mark_step_failed(self, step: WorkflowStep, error: str) -> None:
        """
        Mark a step as failed.
        
        Args:
            step: The failed step
            error: The error message
        """
        self.error = error
        self.error_step = step
    
    def is_complete(self) -> bool:
        """
        Check if the workflow is complete.
        
        Returns:
            bool: True if the workflow is complete, False otherwise
        """
        return WorkflowStep.STEP3_FINDINGS_TRANSMISSION in self.completed_steps
    
    def can_resume_from_step(self, step: WorkflowStep) -> bool:
        """
        Check if the workflow can resume from a specific step.
        
        Args:
            step: The step to resume from
            
        Returns:
            bool: True if the workflow can resume from the step, False otherwise
        """
        if step == WorkflowStep.STEP1_DAM_ANALYSIS:
            # Can always resume from first step
            return True
        elif step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT:
            # Need results from Step 1
            return WorkflowStep.STEP1_DAM_ANALYSIS in self.completed_steps
        elif step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION:
            # Need results from Step 2
            return WorkflowStep.STEP2_JOB_AID_ASSESSMENT in self.completed_steps
        
        return False
    
    def get_previous_step_result(self, step: WorkflowStep) -> Optional[Dict[str, Any]]:
        """
        Get the result of the previous step.
        
        Args:
            step: The current step
            
        Returns:
            Optional[Dict[str, Any]]: The result of the previous step, or None if not available
        """
        if step == WorkflowStep.STEP1_DAM_ANALYSIS:
            # First step has no previous step
            return None
        elif step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT:
            # Get result from Step 1
            step1_result = self.results.get(WorkflowStep.STEP1_DAM_ANALYSIS)
            return step1_result.data if step1_result and step1_result.success else None
        elif step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION:
            # Get result from Step 2
            step2_result = self.results.get(WorkflowStep.STEP2_JOB_AID_ASSESSMENT)
            return step2_result.data if step2_result and step2_result.success else None
        
        return None


class WorkflowEngine:
    """
    Main workflow engine for DAM Compliance Analyzer.
    
    This class orchestrates the execution of all three steps in the workflow,
    manages data flow between steps, and provides error handling and recovery.
    """
    
    def __init__(self, ai_client: Optional[GeminiClient] = None):
        """
        Initialize the workflow engine.
        
        Args:
            ai_client: Optional AI client to use for processing
        """
        self.ai_client = ai_client
        self.state = WorkflowState()
        self._processors: Dict[WorkflowStep, BaseProcessor] = {}
    
    async def initialize(self) -> None:
        """
        Initialize the workflow engine and its processors.
        
        Raises:
            WorkflowError: If initialization fails
        """
        try:
            # Initialize AI client if not provided
            if not self.ai_client:
                logger.info("Creating new Gemini AI client")
                self.ai_client = await create_gemini_client()
            
            # Initialize processors
            self._processors = {
                WorkflowStep.STEP1_DAM_ANALYSIS: Step1Processor(self.ai_client),
                WorkflowStep.STEP2_JOB_AID_ASSESSMENT: Step2Processor(self.ai_client),
                WorkflowStep.STEP3_FINDINGS_TRANSMISSION: Step3Processor(self.ai_client)
            }
            
            logger.info("Workflow engine initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize workflow engine: {str(e)}"
            logger.error(error_msg)
            raise WorkflowError(error_msg)
    
    def _validate_inputs(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Validate workflow inputs.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            
        Raises:
            WorkflowValidationError: If validation fails
        """
        if not image_bytes:
            raise WorkflowValidationError("Image bytes cannot be empty")
        
        if metadata is not None and not isinstance(metadata, dict):
            raise WorkflowValidationError("Metadata must be a dictionary")
    
    async def execute_workflow(
        self,
        image_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None,
        start_step: WorkflowStep = WorkflowStep.STEP1_DAM_ANALYSIS,
        previous_state: Optional[WorkflowState] = None
    ) -> WorkflowState:
        """
        Execute the complete workflow or resume from a specific step.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            start_step: The step to start or resume from
            previous_state: Optional previous workflow state for resuming
            
        Returns:
            WorkflowState: The final workflow state
            
        Raises:
            WorkflowError: If workflow execution fails
        """
        try:
            # Validate inputs
            self._validate_inputs(image_bytes, metadata)
            
            # Initialize if not already initialized
            if not self._processors:
                await self.initialize()
            
            # Use previous state if provided
            if previous_state:
                self.state = previous_state
                
                # Validate that we can resume from the specified step
                if not self.state.can_resume_from_step(start_step):
                    raise WorkflowValidationError(
                        f"Cannot resume workflow from step {start_step.name} without required previous results"
                    )
            else:
                # Reset state if starting fresh
                self.state = WorkflowState(current_step=start_step)
            
            # Execute steps sequentially
            if start_step == WorkflowStep.STEP1_DAM_ANALYSIS:
                await self._execute_step1(image_bytes, metadata)
                if not self.state.error:
                    await self._execute_step2(image_bytes, metadata)
                    if not self.state.error:
                        await self._execute_step3(image_bytes, metadata)
            elif start_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT:
                await self._execute_step2(image_bytes, metadata)
                if not self.state.error:
                    await self._execute_step3(image_bytes, metadata)
            elif start_step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION:
                await self._execute_step3(image_bytes, metadata)
            
            # Return final state
            return self.state
            
        except WorkflowValidationError as e:
            error_msg = f"Workflow validation error: {str(e)}"
            logger.error(error_msg)
            self.state.error = error_msg
            return self.state
            
        except WorkflowExecutionError as e:
            error_msg = f"Workflow execution error: {str(e)}"
            logger.error(error_msg)
            self.state.error = error_msg
            return self.state
            
        except Exception as e:
            error_msg = f"Unexpected error in workflow: {str(e)}"
            logger.error(error_msg)
            self.state.error = error_msg
            return self.state
    
    async def _execute_step1(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute Step 1: DAM Analysis.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            
        Raises:
            WorkflowExecutionError: If step execution fails
        """
        try:
            logger.info("Executing Step 1: DAM Analysis")
            
            # Get processor
            processor = self._processors[WorkflowStep.STEP1_DAM_ANALYSIS]
            
            # Execute processor
            result = await processor.process(image_bytes, metadata)
            
            # Check result
            if not result.success:
                error_msg = result.error_message or "Step 1 failed with no error message"
                logger.error(f"Step 1 failed: {error_msg}")
                self.state.mark_step_failed(WorkflowStep.STEP1_DAM_ANALYSIS, error_msg)
                raise WorkflowExecutionError(f"Step 1 failed: {error_msg}")
            
            # Update state
            self.state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result)
            logger.info("Step 1 completed successfully")
            
        except ProcessorError as e:
            error_msg = f"Step 1 processor error: {str(e)}"
            logger.error(error_msg)
            self.state.mark_step_failed(WorkflowStep.STEP1_DAM_ANALYSIS, error_msg)
            raise WorkflowExecutionError(error_msg)
    
    async def _execute_step2(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute Step 2: Job Aid Assessment.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            
        Raises:
            WorkflowExecutionError: If step execution fails
        """
        try:
            logger.info("Executing Step 2: Job Aid Assessment")
            
            # Get processor
            processor = self._processors[WorkflowStep.STEP2_JOB_AID_ASSESSMENT]
            
            # Get previous step result
            previous_result = self.state.get_previous_step_result(WorkflowStep.STEP2_JOB_AID_ASSESSMENT)
            if not previous_result:
                error_msg = "Missing required results from Step 1"
                logger.error(error_msg)
                self.state.mark_step_failed(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, error_msg)
                raise WorkflowExecutionError(error_msg)
            
            # Execute processor
            result = await processor.process(image_bytes, metadata, previous_result)
            
            # Check result
            if not result.success:
                error_msg = result.error_message or "Step 2 failed with no error message"
                logger.error(f"Step 2 failed: {error_msg}")
                self.state.mark_step_failed(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, error_msg)
                raise WorkflowExecutionError(f"Step 2 failed: {error_msg}")
            
            # Update state
            self.state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, result)
            logger.info("Step 2 completed successfully")
            
        except ProcessorError as e:
            error_msg = f"Step 2 processor error: {str(e)}"
            logger.error(error_msg)
            self.state.mark_step_failed(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, error_msg)
            raise WorkflowExecutionError(error_msg)
    
    async def _execute_step3(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute Step 3: Findings Transmission.
        
        Args:
            image_bytes: The image bytes to process
            metadata: Optional metadata to include in processing
            
        Raises:
            WorkflowExecutionError: If step execution fails
        """
        try:
            logger.info("Executing Step 3: Findings Transmission")
            
            # Get processor
            processor = self._processors[WorkflowStep.STEP3_FINDINGS_TRANSMISSION]
            
            # Get previous step result
            previous_result = self.state.get_previous_step_result(WorkflowStep.STEP3_FINDINGS_TRANSMISSION)
            if not previous_result:
                error_msg = "Missing required results from Step 2"
                logger.error(error_msg)
                self.state.mark_step_failed(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, error_msg)
                raise WorkflowExecutionError(error_msg)
            
            # Execute processor
            result = await processor.process(image_bytes, metadata, previous_result)
            
            # Check result
            if not result.success:
                error_msg = result.error_message or "Step 3 failed with no error message"
                logger.error(f"Step 3 failed: {error_msg}")
                self.state.mark_step_failed(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, error_msg)
                raise WorkflowExecutionError(f"Step 3 failed: {error_msg}")
            
            # Update state
            self.state.mark_step_complete(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, result)
            logger.info("Step 3 completed successfully")
            
        except ProcessorError as e:
            error_msg = f"Step 3 processor error: {str(e)}"
            logger.error(error_msg)
            self.state.mark_step_failed(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, error_msg)
            raise WorkflowExecutionError(error_msg)
    
    def get_workflow_results(self) -> Dict[str, Any]:
        """
        Get the combined results from all workflow steps.
        
        Returns:
            Dict[str, Any]: Combined results from all steps
        """
        results = {
            "workflow_complete": self.state.is_complete(),
            "error": self.state.error
        }
        
        # Add results from each completed step
        if WorkflowStep.STEP1_DAM_ANALYSIS in self.state.completed_steps:
            step1_result = self.state.results[WorkflowStep.STEP1_DAM_ANALYSIS]
            results["step1_result"] = step1_result.data
        
        if WorkflowStep.STEP2_JOB_AID_ASSESSMENT in self.state.completed_steps:
            step2_result = self.state.results[WorkflowStep.STEP2_JOB_AID_ASSESSMENT]
            results["step2_result"] = step2_result.data
        
        if WorkflowStep.STEP3_FINDINGS_TRANSMISSION in self.state.completed_steps:
            step3_result = self.state.results[WorkflowStep.STEP3_FINDINGS_TRANSMISSION]
            results["step3_result"] = step3_result.data
        
        return results
    
    def get_workflow_state(self) -> Dict[str, Any]:
        """
        Get a serializable representation of the workflow state.
        
        Returns:
            Dict[str, Any]: Serializable workflow state
        """
        return {
            "current_step": self.state.current_step.name,
            "completed_steps": [step.name for step in self.state.completed_steps],
            "error": self.state.error,
            "error_step": self.state.error_step.name if self.state.error_step else None,
            "is_complete": self.state.is_complete()
        }


# Factory function for creating workflow engine instances
async def create_workflow_engine(ai_client: Optional[GeminiClient] = None) -> WorkflowEngine:
    """
    Create and initialize a workflow engine.
    
    Args:
        ai_client: Optional AI client to use for processing
        
    Returns:
        WorkflowEngine: Initialized workflow engine
        
    Raises:
        WorkflowError: If engine creation or initialization fails
    """
    engine = WorkflowEngine(ai_client)
    await engine.initialize()
    return engine