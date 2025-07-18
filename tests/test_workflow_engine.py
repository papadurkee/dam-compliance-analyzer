"""
Integration tests for the Workflow Engine.

Tests the WorkflowEngine class functionality including step orchestration,
data flow between steps, error handling, and recovery from interruptions.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from workflow import (
    WorkflowEngine,
    WorkflowStep,
    WorkflowState,
    WorkflowError,
    WorkflowValidationError,
    WorkflowExecutionError,
    ProcessorResult
)
from workflow.step1_processor import Step1Processor
from workflow.step2_processor import Step2Processor
from workflow.step3_processor import Step3Processor
from services import GeminiClient, AIResponse


class TestWorkflowEngine:
    """Integration tests for WorkflowEngine class"""
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create a mock AI client"""
        client = Mock(spec=GeminiClient)
        client.process_multimodal_request = AsyncMock()
        client.parse_structured_response = Mock()
        return client
    
    @pytest.fixture
    def mock_step1_processor(self, mock_ai_client):
        """Create a mock Step1Processor"""
        processor = Mock(spec=Step1Processor)
        processor.process = AsyncMock()
        return processor
    
    @pytest.fixture
    def mock_step2_processor(self, mock_ai_client):
        """Create a mock Step2Processor"""
        processor = Mock(spec=Step2Processor)
        processor.process = AsyncMock()
        return processor
    
    @pytest.fixture
    def mock_step3_processor(self, mock_ai_client):
        """Create a mock Step3Processor"""
        processor = Mock(spec=Step3Processor)
        processor.process = AsyncMock()
        return processor
    
    @pytest.fixture
    def workflow_engine(self, mock_ai_client, mock_step1_processor, 
                       mock_step2_processor, mock_step3_processor):
        """Create a WorkflowEngine with mock processors"""
        engine = WorkflowEngine(mock_ai_client)
        engine._processors = {
            WorkflowStep.STEP1_DAM_ANALYSIS: mock_step1_processor,
            WorkflowStep.STEP2_JOB_AID_ASSESSMENT: mock_step2_processor,
            WorkflowStep.STEP3_FINDINGS_TRANSMISSION: mock_step3_processor
        }
        return engine
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Sample image bytes for testing"""
        return b'test_image_data'
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return {
            "component_id": "IMG_12345",
            "component_name": "Product Hero Image"
        }
    
    @pytest.fixture
    def sample_step1_result(self):
        """Sample Step 1 result for testing"""
        return ProcessorResult(
            success=True,
            data={
                "notes": "The image appears to be a high-quality product photo.",
                "job_aid_assessment": {
                    "visual_quality": {"assessment": "PASS", "issues": []}
                },
                "human_readable_section": "This product image meets quality standards.",
                "next_steps": ["Proceed to Step 2"]
            },
            raw_response="Raw response text"
        )
    
    @pytest.fixture
    def sample_step2_result(self):
        """Sample Step 2 result for testing"""
        return ProcessorResult(
            success=True,
            data={
                "completed_job_aid": {
                    "digital_component_analysis": {
                        "component_specifications": {
                            "assessment": "PASS",
                            "notes": "All specifications are met"
                        },
                        "overall_assessment": {
                            "status": "PASS",
                            "summary": "The image meets all requirements"
                        }
                    }
                },
                "assessment_summary": "Assessment Status: PASS\n\nThe image meets all requirements"
            },
            raw_response="Raw response text"
        )
    
    @pytest.fixture
    def sample_step3_result(self):
        """Sample Step 3 result for testing"""
        return ProcessorResult(
            success=True,
            data={
                "json_output": {
                    "component_id": "IMG_12345",
                    "component_name": "Product Hero Image",
                    "check_status": "PASSED",
                    "issues_detected": [],
                    "missing_information": [],
                    "recommendations": ["No changes needed"]
                },
                "human_readable_report": "DIGITAL ASSET COMPLIANCE ASSESSMENT REPORT\n\nComponent Name: Product Hero Image\nComponent ID: IMG_12345\n\nOVERALL COMPLIANCE STATUS: PASSED"
            },
            raw_response="Raw response text"
        )
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_ai_client):
        """Test initializing the workflow engine"""
        engine = WorkflowEngine(mock_ai_client)
        await engine.initialize()
        
        assert len(engine._processors) == 3
        assert WorkflowStep.STEP1_DAM_ANALYSIS in engine._processors
        assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT in engine._processors
        assert WorkflowStep.STEP3_FINDINGS_TRANSMISSION in engine._processors
    
    @pytest.mark.asyncio
    async def test_initialize_with_client_creation(self):
        """Test initializing the workflow engine with client creation"""
        with patch('workflow.engine.create_gemini_client', new_callable=AsyncMock) as mock_create_client:
            mock_client = Mock(spec=GeminiClient)
            mock_create_client.return_value = mock_client
            
            engine = WorkflowEngine()
            await engine.initialize()
            
            assert engine.ai_client == mock_client
            mock_create_client.assert_called_once()
    
    def test_validate_inputs_valid(self, workflow_engine, sample_image_bytes, sample_metadata):
        """Test validating valid inputs"""
        # Should not raise any exceptions
        workflow_engine._validate_inputs(sample_image_bytes, sample_metadata)
    
    def test_validate_inputs_empty_image(self, workflow_engine):
        """Test validating with empty image bytes"""
        with pytest.raises(WorkflowValidationError, match="Image bytes cannot be empty"):
            workflow_engine._validate_inputs(b'', {})
    
    def test_validate_inputs_invalid_metadata(self, workflow_engine, sample_image_bytes):
        """Test validating with invalid metadata"""
        with pytest.raises(WorkflowValidationError, match="Metadata must be a dictionary"):
            workflow_engine._validate_inputs(sample_image_bytes, "not a dictionary")
    
    @pytest.mark.asyncio
    async def test_execute_workflow_complete(self, workflow_engine, mock_step1_processor,
                                           mock_step2_processor, mock_step3_processor,
                                           sample_image_bytes, sample_metadata,
                                           sample_step1_result, sample_step2_result,
                                           sample_step3_result):
        """Test executing complete workflow successfully"""
        # Set up mock processor responses
        mock_step1_processor.process.return_value = sample_step1_result
        mock_step2_processor.process.return_value = sample_step2_result
        mock_step3_processor.process.return_value = sample_step3_result
        
        # Execute workflow
        state = await workflow_engine.execute_workflow(sample_image_bytes, sample_metadata)
        
        # Verify all steps were executed
        mock_step1_processor.process.assert_called_once_with(sample_image_bytes, sample_metadata)
        mock_step2_processor.process.assert_called_once()
        mock_step3_processor.process.assert_called_once()
        
        # Verify workflow state
        assert state.is_complete() is True
        assert state.error is None
        assert len(state.completed_steps) == 3
        assert WorkflowStep.STEP1_DAM_ANALYSIS in state.completed_steps
        assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT in state.completed_steps
        assert WorkflowStep.STEP3_FINDINGS_TRANSMISSION in state.completed_steps
        
        # Verify results were stored
        assert state.results[WorkflowStep.STEP1_DAM_ANALYSIS] == sample_step1_result
        assert state.results[WorkflowStep.STEP2_JOB_AID_ASSESSMENT] == sample_step2_result
        assert state.results[WorkflowStep.STEP3_FINDINGS_TRANSMISSION] == sample_step3_result
    
    @pytest.mark.asyncio
    async def test_execute_workflow_step1_failure(self, workflow_engine, mock_step1_processor,
                                                mock_step2_processor, mock_step3_processor,
                                                sample_image_bytes, sample_metadata):
        """Test workflow with Step 1 failure"""
        # Set up mock processor responses
        failed_result = ProcessorResult(success=False, data={}, error_message="Step 1 failed")
        mock_step1_processor.process.return_value = failed_result
        
        # Execute workflow
        state = await workflow_engine.execute_workflow(sample_image_bytes, sample_metadata)
        
        # Verify only Step 1 was executed
        mock_step1_processor.process.assert_called_once_with(sample_image_bytes, sample_metadata)
        mock_step2_processor.process.assert_not_called()
        mock_step3_processor.process.assert_not_called()
        
        # Verify workflow state
        assert state.is_complete() is False
        assert state.error is not None
        assert "Step 1 failed" in state.error
        assert state.error_step == WorkflowStep.STEP1_DAM_ANALYSIS
        assert len(state.completed_steps) == 0
    
    @pytest.mark.asyncio
    async def test_execute_workflow_step2_failure(self, workflow_engine, mock_step1_processor,
                                                mock_step2_processor, mock_step3_processor,
                                                sample_image_bytes, sample_metadata,
                                                sample_step1_result):
        """Test workflow with Step 2 failure"""
        # Set up mock processor responses
        mock_step1_processor.process.return_value = sample_step1_result
        failed_result = ProcessorResult(success=False, data={}, error_message="Step 2 failed")
        mock_step2_processor.process.return_value = failed_result
        
        # Execute workflow
        state = await workflow_engine.execute_workflow(sample_image_bytes, sample_metadata)
        
        # Verify Steps 1 and 2 were executed
        mock_step1_processor.process.assert_called_once_with(sample_image_bytes, sample_metadata)
        mock_step2_processor.process.assert_called_once()
        mock_step3_processor.process.assert_not_called()
        
        # Verify workflow state
        assert state.is_complete() is False
        assert state.error is not None
        assert "Step 2 failed" in state.error
        assert state.error_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT
        assert len(state.completed_steps) == 1
        assert WorkflowStep.STEP1_DAM_ANALYSIS in state.completed_steps
    
    @pytest.mark.asyncio
    async def test_execute_workflow_step3_failure(self, workflow_engine, mock_step1_processor,
                                                mock_step2_processor, mock_step3_processor,
                                                sample_image_bytes, sample_metadata,
                                                sample_step1_result, sample_step2_result):
        """Test workflow with Step 3 failure"""
        # Set up mock processor responses
        mock_step1_processor.process.return_value = sample_step1_result
        mock_step2_processor.process.return_value = sample_step2_result
        failed_result = ProcessorResult(success=False, data={}, error_message="Step 3 failed")
        mock_step3_processor.process.return_value = failed_result
        
        # Execute workflow
        state = await workflow_engine.execute_workflow(sample_image_bytes, sample_metadata)
        
        # Verify all steps were executed
        mock_step1_processor.process.assert_called_once_with(sample_image_bytes, sample_metadata)
        mock_step2_processor.process.assert_called_once()
        mock_step3_processor.process.assert_called_once()
        
        # Verify workflow state
        assert state.is_complete() is False
        assert state.error is not None
        assert "Step 3 failed" in state.error
        assert state.error_step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION
        assert len(state.completed_steps) == 2
        assert WorkflowStep.STEP1_DAM_ANALYSIS in state.completed_steps
        assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT in state.completed_steps
    
    @pytest.mark.asyncio
    async def test_resume_from_step2(self, workflow_engine, mock_step1_processor,
                                    mock_step2_processor, mock_step3_processor,
                                    sample_image_bytes, sample_metadata,
                                    sample_step1_result, sample_step2_result,
                                    sample_step3_result):
        """Test resuming workflow from Step 2"""
        # Create previous state with Step 1 completed
        previous_state = WorkflowState(current_step=WorkflowStep.STEP2_JOB_AID_ASSESSMENT)
        previous_state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        
        # Set up mock processor responses
        mock_step2_processor.process.return_value = sample_step2_result
        mock_step3_processor.process.return_value = sample_step3_result
        
        # Execute workflow from Step 2
        state = await workflow_engine.execute_workflow(
            sample_image_bytes, 
            sample_metadata,
            start_step=WorkflowStep.STEP2_JOB_AID_ASSESSMENT,
            previous_state=previous_state
        )
        
        # Verify only Steps 2 and 3 were executed
        mock_step1_processor.process.assert_not_called()
        mock_step2_processor.process.assert_called_once()
        mock_step3_processor.process.assert_called_once()
        
        # Verify workflow state
        assert state.is_complete() is True
        assert state.error is None
        assert len(state.completed_steps) == 3
        assert WorkflowStep.STEP1_DAM_ANALYSIS in state.completed_steps
        assert WorkflowStep.STEP2_JOB_AID_ASSESSMENT in state.completed_steps
        assert WorkflowStep.STEP3_FINDINGS_TRANSMISSION in state.completed_steps
    
    @pytest.mark.asyncio
    async def test_resume_from_step3(self, workflow_engine, mock_step1_processor,
                                    mock_step2_processor, mock_step3_processor,
                                    sample_image_bytes, sample_metadata,
                                    sample_step1_result, sample_step2_result,
                                    sample_step3_result):
        """Test resuming workflow from Step 3"""
        # Create previous state with Steps 1 and 2 completed
        previous_state = WorkflowState(current_step=WorkflowStep.STEP3_FINDINGS_TRANSMISSION)
        previous_state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        previous_state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, sample_step2_result)
        
        # Set up mock processor responses
        mock_step3_processor.process.return_value = sample_step3_result
        
        # Execute workflow from Step 3
        state = await workflow_engine.execute_workflow(
            sample_image_bytes, 
            sample_metadata,
            start_step=WorkflowStep.STEP3_FINDINGS_TRANSMISSION,
            previous_state=previous_state
        )
        
        # Verify only Step 3 was executed
        mock_step1_processor.process.assert_not_called()
        mock_step2_processor.process.assert_not_called()
        mock_step3_processor.process.assert_called_once()
        
        # Verify workflow state
        assert state.is_complete() is True
        assert state.error is None
        assert len(state.completed_steps) == 3
    
    @pytest.mark.asyncio
    async def test_resume_invalid_step(self, workflow_engine, sample_image_bytes, sample_metadata):
        """Test resuming workflow from invalid step"""
        # Create previous state with no steps completed
        previous_state = WorkflowState(current_step=WorkflowStep.STEP1_DAM_ANALYSIS)
        
        # Try to execute workflow from Step 2 without Step 1 results
        state = await workflow_engine.execute_workflow(
            sample_image_bytes, 
            sample_metadata,
            start_step=WorkflowStep.STEP2_JOB_AID_ASSESSMENT,
            previous_state=previous_state
        )
        
        # Verify error
        assert state.error is not None
        assert "Cannot resume workflow from step" in state.error
    
    def test_get_workflow_results_complete(self, workflow_engine, sample_step1_result,
                                          sample_step2_result, sample_step3_result):
        """Test getting workflow results when complete"""
        # Set up workflow state
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, sample_step2_result)
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, sample_step3_result)
        
        # Get results
        results = workflow_engine.get_workflow_results()
        
        # Verify results
        assert results["workflow_complete"] is True
        assert results["error"] is None
        assert "step1_result" in results
        assert "step2_result" in results
        assert "step3_result" in results
        assert results["step1_result"] == sample_step1_result.data
        assert results["step2_result"] == sample_step2_result.data
        assert results["step3_result"] == sample_step3_result.data
    
    def test_get_workflow_results_partial(self, workflow_engine, sample_step1_result):
        """Test getting workflow results when partially complete"""
        # Set up workflow state with only Step 1 completed
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        
        # Get results
        results = workflow_engine.get_workflow_results()
        
        # Verify results
        assert results["workflow_complete"] is False
        assert results["error"] is None
        assert "step1_result" in results
        assert "step2_result" not in results
        assert "step3_result" not in results
        assert results["step1_result"] == sample_step1_result.data
    
    def test_get_workflow_results_with_error(self, workflow_engine, sample_step1_result):
        """Test getting workflow results with error"""
        # Set up workflow state with Step 1 completed and Step 2 failed
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        workflow_engine.state.mark_step_failed(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, "Step 2 failed")
        
        # Get results
        results = workflow_engine.get_workflow_results()
        
        # Verify results
        assert results["workflow_complete"] is False
        assert results["error"] == "Step 2 failed"
        assert "step1_result" in results
        assert "step2_result" not in results
        assert "step3_result" not in results
    
    def test_get_workflow_state(self, workflow_engine, sample_step1_result, sample_step2_result):
        """Test getting serializable workflow state"""
        # Set up workflow state
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, sample_step1_result)
        workflow_engine.state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, sample_step2_result)
        
        # Get state
        state_dict = workflow_engine.get_workflow_state()
        
        # Verify state
        assert state_dict["current_step"] == "STEP3_FINDINGS_TRANSMISSION"
        assert "STEP1_DAM_ANALYSIS" in state_dict["completed_steps"]
        assert "STEP2_JOB_AID_ASSESSMENT" in state_dict["completed_steps"]
        assert state_dict["error"] is None
        assert state_dict["error_step"] is None
        assert state_dict["is_complete"] is False
    
    @pytest.mark.asyncio
    async def test_create_workflow_engine(self, mock_ai_client):
        """Test creating workflow engine with factory function"""
        with patch('workflow.engine.WorkflowEngine.initialize', new_callable=AsyncMock) as mock_initialize:
            from workflow.engine import create_workflow_engine
            
            engine = await create_workflow_engine(mock_ai_client)
            
            assert isinstance(engine, WorkflowEngine)
            assert engine.ai_client == mock_ai_client
            mock_initialize.assert_called_once()


class TestWorkflowState:
    """Tests for WorkflowState class"""
    
    def test_mark_step_complete(self):
        """Test marking a step as complete"""
        state = WorkflowState()
        result = ProcessorResult(success=True, data={"test": "data"})
        
        # Mark Step 1 complete
        state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result)
        
        assert WorkflowStep.STEP1_DAM_ANALYSIS in state.completed_steps
        assert state.results[WorkflowStep.STEP1_DAM_ANALYSIS] == result
        assert state.current_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT
    
    def test_mark_step_complete_sequence(self):
        """Test marking steps complete in sequence"""
        state = WorkflowState()
        result1 = ProcessorResult(success=True, data={"step": 1})
        result2 = ProcessorResult(success=True, data={"step": 2})
        result3 = ProcessorResult(success=True, data={"step": 3})
        
        # Mark steps complete in sequence
        state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result1)
        assert state.current_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT
        
        state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, result2)
        assert state.current_step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION
        
        state.mark_step_complete(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, result3)
        assert state.current_step == WorkflowStep.STEP3_FINDINGS_TRANSMISSION  # No next step
    
    def test_mark_step_failed(self):
        """Test marking a step as failed"""
        state = WorkflowState()
        
        # Mark Step 2 failed
        state.mark_step_failed(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, "Test error")
        
        assert state.error == "Test error"
        assert state.error_step == WorkflowStep.STEP2_JOB_AID_ASSESSMENT
    
    def test_is_complete(self):
        """Test checking if workflow is complete"""
        state = WorkflowState()
        result = ProcessorResult(success=True, data={})
        
        # Initially not complete
        assert state.is_complete() is False
        
        # Still not complete after Steps 1 and 2
        state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result)
        state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, result)
        assert state.is_complete() is False
        
        # Complete after Step 3
        state.mark_step_complete(WorkflowStep.STEP3_FINDINGS_TRANSMISSION, result)
        assert state.is_complete() is True
    
    def test_can_resume_from_step(self):
        """Test checking if workflow can resume from a step"""
        state = WorkflowState()
        result = ProcessorResult(success=True, data={})
        
        # Can always resume from Step 1
        assert state.can_resume_from_step(WorkflowStep.STEP1_DAM_ANALYSIS) is True
        
        # Cannot resume from Steps 2 or 3 initially
        assert state.can_resume_from_step(WorkflowStep.STEP2_JOB_AID_ASSESSMENT) is False
        assert state.can_resume_from_step(WorkflowStep.STEP3_FINDINGS_TRANSMISSION) is False
        
        # Complete Step 1
        state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result)
        
        # Now can resume from Step 2 but not Step 3
        assert state.can_resume_from_step(WorkflowStep.STEP2_JOB_AID_ASSESSMENT) is True
        assert state.can_resume_from_step(WorkflowStep.STEP3_FINDINGS_TRANSMISSION) is False
        
        # Complete Step 2
        state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, result)
        
        # Now can resume from Step 3
        assert state.can_resume_from_step(WorkflowStep.STEP3_FINDINGS_TRANSMISSION) is True
    
    def test_get_previous_step_result(self):
        """Test getting previous step result"""
        state = WorkflowState()
        result1 = ProcessorResult(success=True, data={"step": 1})
        result2 = ProcessorResult(success=True, data={"step": 2})
        
        # No previous result for Step 1
        assert state.get_previous_step_result(WorkflowStep.STEP1_DAM_ANALYSIS) is None
        
        # No previous result for Step 2 initially
        assert state.get_previous_step_result(WorkflowStep.STEP2_JOB_AID_ASSESSMENT) is None
        
        # Complete Step 1
        state.mark_step_complete(WorkflowStep.STEP1_DAM_ANALYSIS, result1)
        
        # Now Step 2 has previous result
        assert state.get_previous_step_result(WorkflowStep.STEP2_JOB_AID_ASSESSMENT) == result1.data
        
        # No previous result for Step 3 yet
        assert state.get_previous_step_result(WorkflowStep.STEP3_FINDINGS_TRANSMISSION) is None
        
        # Complete Step 2
        state.mark_step_complete(WorkflowStep.STEP2_JOB_AID_ASSESSMENT, result2)
        
        # Now Step 3 has previous result
        assert state.get_previous_step_result(WorkflowStep.STEP3_FINDINGS_TRANSMISSION) == result2.data


if __name__ == "__main__":
    pytest.main([__file__])