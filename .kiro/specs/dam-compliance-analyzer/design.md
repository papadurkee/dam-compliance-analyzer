# Design Document

## Overview

The DAM Compliance Analyzer is a Streamlit-based web application that integrates with Google Vertex AI's Gemini 2.5 Flash model to perform automated compliance analysis of digital assets. The system implements a structured 3-step workflow that transforms uploaded images and metadata into comprehensive compliance assessments suitable for both automated processing and human review.

The application serves as a proof of concept demonstrating how AI can augment Digital Asset Management workflows by providing consistent, structured analysis against predefined compliance criteria while maintaining the flexibility to handle various image types and metadata structures.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    A[User Interface - Streamlit] --> B[Workflow Engine]
    B --> C[Step 1: DAM Analysis]
    B --> D[Step 2: Job Aid Assessment]
    B --> E[Step 3: Findings Transmission]
    
    C --> F[Vertex AI Integration]
    D --> F
    E --> F
    
    F --> G[Gemini 2.5 Flash Model]
    
    H[Prompt Management] --> C
    H --> D
    H --> E
    
    I[Schema Management] --> D
    I --> E
    
    J[Authentication Manager] --> F
    
    K[Error Handler] --> A
    K --> B
    K --> F
```

### System Components

1. **Streamlit Frontend**: Provides the user interface for image upload, metadata input, and results display
2. **Workflow Engine**: Orchestrates the 3-step analysis process and manages data flow between steps
3. **Vertex AI Integration Layer**: Handles authentication, API calls, and response processing
4. **Prompt Management System**: Stores and manages the exact prompts for each workflow step
5. **Schema Management**: Maintains the job aid schema and output format definitions
6. **Authentication Manager**: Handles Google Cloud Platform authentication and credential management
7. **Error Handling System**: Provides comprehensive error handling and user feedback

### Deployment Architecture

```mermaid
graph LR
    A[GitHub Repository] --> B[Streamlit Community Cloud]
    B --> C[Application Instance]
    C --> D[Google Cloud Platform]
    D --> E[Vertex AI API]
    E --> F[Gemini 2.5 Flash Model]
    
    G[Service Account Credentials] --> C
    H[Streamlit Secrets] --> G
```

## Components and Interfaces

### 1. User Interface Layer

**Streamlit Application (`app.py`)**
- **Purpose**: Main application entry point and UI orchestration
- **Key Functions**:
  - `create_main_interface()`: Renders the primary UI components
  - `handle_file_upload()`: Manages image upload and validation
  - `handle_metadata_input()`: Processes and validates JSON metadata
  - `display_results()`: Renders workflow results with tabbed interface
- **Interface**: Web-based UI accessible via browser

**UI Components**:
- Image upload widget with format validation
- JSON metadata text area with syntax highlighting
- Analysis trigger button with loading states
- Tabbed results display (Step 1, Step 2, Step 3 with JSON/Human-readable sub-tabs)
- Error message display areas

### 2. Workflow Engine

**Workflow Orchestrator (`workflow/engine.py`)**
- **Purpose**: Manages the sequential execution of the 3-step analysis process
- **Key Functions**:
  - `execute_workflow(image_bytes, metadata_json)`: Main workflow execution
  - `validate_inputs(image_bytes, metadata_json)`: Input validation
  - `handle_step_failure(step_number, error)`: Error recovery and reporting
- **Interface**: Python function calls returning structured results

**Step Processors**:
- `Step1Processor`: Handles DAM Analysis with role-based prompting
- `Step2Processor`: Manages Job Aid Assessment with schema integration
- `Step3Processor`: Generates findings in dual format (JSON + human-readable)

### 3. Vertex AI Integration

**AI Service Client (`services/vertex_ai_client.py`)**
- **Purpose**: Handles all interactions with Google Vertex AI
- **Key Functions**:
  - `initialize_client()`: Sets up authenticated Vertex AI client
  - `process_multimodal_request(image, text, config)`: Sends requests to Gemini model
  - `parse_structured_response(response)`: Extracts and validates structured outputs
- **Interface**: Async/await pattern for API calls

**Authentication Manager (`auth/gcp_auth.py`)**
- **Purpose**: Manages Google Cloud Platform authentication
- **Key Functions**:
  - `load_service_account_credentials()`: Loads credentials from Streamlit secrets
  - `validate_credentials()`: Verifies credential validity and permissions
  - `refresh_token_if_needed()`: Handles token refresh for long-running sessions

### 4. Prompt and Schema Management

**Prompt Templates (`prompts/templates.py`)**
- **Purpose**: Stores and manages exact prompts for each workflow step
- **Key Components**:
  - `DAM_ANALYST_ROLE`: Complete role description for Step 1
  - `TASK_INSTRUCTIONS`: 4-part task format for Step 1
  - `OUTPUT_GUIDELINES`: Structured output format requirements
  - `JOB_AID_PROMPT`: Integration prompt for Step 2
  - `FINDINGS_PROMPT`: Template for Step 3 dual output

**Schema Definitions (`schemas/job_aid.py`)**
- **Purpose**: Maintains the complete job aid JSON schema
- **Key Components**:
  - `DIGITAL_COMPONENT_ANALYSIS_SCHEMA`: Complete nested schema structure
  - `FINDINGS_OUTPUT_SCHEMA`: JSON structure for Step 3 output
  - `validate_schema_compliance(data)`: Schema validation functions

### 5. Data Processing

**Image Handler (`utils/image_processing.py`)**
- **Purpose**: Manages image upload, validation, and format conversion
- **Key Functions**:
  - `validate_image_format(file)`: Checks file type and size constraints
  - `convert_to_bytes(image)`: Converts uploaded image to bytes for API
  - `generate_image_preview(image)`: Creates display-ready image preview

**Metadata Processor (`utils/metadata_handler.py`)**
- **Purpose**: Handles JSON metadata validation and processing
- **Key Functions**:
  - `validate_json_metadata(json_string)`: Validates JSON syntax and structure
  - `enrich_metadata(metadata)`: Adds default fields if missing
  - `format_for_ai_prompt(metadata)`: Formats metadata for AI consumption

## Data Models

### Input Data Models

```python
@dataclass
class ImageUpload:
    file_bytes: bytes
    filename: str
    mime_type: str
    size_bytes: int
    
@dataclass
class ComponentMetadata:
    component_id: str
    component_name: str
    description: Optional[str]
    usage_rights: Optional[Dict]
    geographic_restrictions: Optional[List[str]]
    channel_requirements: Optional[Dict]
    file_specifications: Optional[Dict]
```

### Workflow Data Models

```python
@dataclass
class Step1Results:
    notes: str
    job_aid_assessment: Dict
    human_readable_section: str
    next_steps: List[str]
    
@dataclass
class Step2Results:
    completed_job_aid: Dict
    assessment_summary: str
    
@dataclass
class Step3Results:
    json_output: FindingsOutput
    human_readable_report: str
```

### Output Data Models

```python
@dataclass
class IssueDetected:
    category: str
    description: str
    action: str

@dataclass
class MissingInformation:
    field: str
    description: str
    action: str

@dataclass
class FindingsOutput:
    component_id: str
    component_name: str
    check_status: Literal["PASSED", "FAILED"]
    issues_detected: List[IssueDetected]
    missing_information: List[MissingInformation]
    recommendations: List[str]
```

### Job Aid Schema Model

```python
class JobAidSchema:
    digital_component_analysis: Dict = {
        "instructions": str,
        "component_specifications": {
            "file_format_requirements": Dict,
            "resolution_requirements": Dict,
            "color_profile_requirements": Dict,
            "naming_convention_requirements": Dict
        },
        "component_metadata": {
            "required_fields": List[str],
            "optional_fields": List[str],
            "validation_rules": Dict
        },
        "component_qc": {
            "visual_quality_checks": Dict,
            "technical_quality_checks": Dict,
            "compliance_checks": Dict
        },
        "component_linking": {
            "relationship_requirements": Dict,
            "dependency_checks": Dict
        },
        "material_distribution_package_qc": {
            "package_integrity_checks": Dict,
            "distribution_readiness_checks": Dict
        }
    }
```

## Error Handling

### Error Categories and Responses

1. **Input Validation Errors**
   - Invalid image format: Display supported formats and file size limits
   - Malformed JSON metadata: Highlight syntax errors with line numbers
   - Missing required fields: List specific missing fields and examples

2. **Authentication Errors**
   - Invalid credentials: Guide user to credential setup documentation
   - Expired tokens: Automatic refresh with fallback to manual re-authentication
   - Insufficient permissions: List required Google Cloud permissions

3. **API Integration Errors**
   - Network connectivity issues: Retry mechanism with exponential backoff
   - Rate limiting: Queue requests with user feedback on wait times
   - Model unavailability: Fallback messaging with estimated recovery time

4. **Processing Errors**
   - Malformed AI responses: Retry with modified prompts, fallback to partial results
   - Schema validation failures: Log details for debugging, provide user-friendly summary
   - Workflow interruption: Save partial progress, allow resume from last successful step

### Error Recovery Strategies

```python
class ErrorHandler:
    def handle_workflow_error(self, step: int, error: Exception) -> ErrorResponse:
        if isinstance(error, ValidationError):
            return self.create_validation_error_response(error)
        elif isinstance(error, AuthenticationError):
            return self.create_auth_error_response(error)
        elif isinstance(error, APIError):
            return self.create_api_error_response(error)
        else:
            return self.create_generic_error_response(error)
    
    def retry_with_backoff(self, func, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                return func()
            except RetryableError as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)
```

## Testing Strategy

### Unit Testing

1. **Component Testing**
   - Image processing functions with various file formats and sizes
   - JSON metadata validation with valid and invalid inputs
   - Prompt template generation with different parameter combinations
   - Schema validation with compliant and non-compliant data structures

2. **Integration Testing**
   - Vertex AI client with mock responses
   - Workflow engine with simulated step failures
   - Authentication manager with various credential scenarios

### End-to-End Testing

1. **Workflow Testing**
   - Complete 3-step workflow with sample images and metadata
   - Error scenarios at each step with appropriate recovery
   - Output format validation for both JSON and human-readable results

2. **UI Testing**
   - File upload functionality with various image types
   - Metadata input validation and error display
   - Results display across different screen sizes and browsers

### Performance Testing

1. **Load Testing**
   - Multiple concurrent users uploading images
   - Large image file processing (within limits)
   - Extended session duration with token refresh

2. **API Testing**
   - Vertex AI response time measurement
   - Rate limiting behavior under load
   - Error rate monitoring and alerting

### Test Data Management

```python
class TestDataManager:
    def get_sample_images(self) -> List[ImageUpload]:
        return [
            self.load_compliant_image(),
            self.load_non_compliant_image(),
            self.load_edge_case_image()
        ]
    
    def get_sample_metadata(self) -> List[ComponentMetadata]:
        return [
            self.load_complete_metadata(),
            self.load_minimal_metadata(),
            self.load_invalid_metadata()
        ]
```

## Security Considerations

### Authentication and Authorization
- Service account credentials stored securely in Streamlit secrets
- Principle of least privilege for Google Cloud permissions
- No user authentication required for proof of concept, but architecture supports future implementation

### Data Protection
- Images and metadata processed in memory only, not stored persistently
- API communications encrypted in transit (HTTPS/TLS)
- No sensitive data logged or cached

### Input Validation
- File type and size restrictions to prevent malicious uploads
- JSON schema validation to prevent injection attacks
- Sanitization of user inputs before AI processing

## Deployment Configuration

### Environment Setup

```yaml
# streamlit_config.toml
[server]
maxUploadSize = 10
enableCORS = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### Dependencies

```txt
streamlit>=1.28.0
google-cloud-aiplatform>=1.38.0
google-auth>=2.23.0
Pillow>=10.0.0
pandas>=2.0.0
python-json-logger>=2.0.0
```

### Secrets Configuration

```toml
# .streamlit/secrets.toml (for local development)
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "service-account@project.iam.gserviceaccount.com"
client_id = "client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

This design provides a comprehensive foundation for implementing the DAM Compliance Analyzer while maintaining flexibility for future enhancements and ensuring robust error handling and security practices.