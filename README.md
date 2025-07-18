# DAM Compliance Analyzer

A proof of concept web application that demonstrates how Google Vertex AI and the Gemini model can be used to analyze images for Digital Asset Management (DAM) quality control and regulatory compliance through a structured, multi-step workflow.

## Overview

This application provides an interactive interface for uploading images, inputting metadata, and receiving structured compliance assessments through a 3-step analysis process:

1. **Step 1: DAM Analysis** - Initial analysis with role-based prompting
2. **Step 2: Job Aid Assessment** - Structured assessment against compliance criteria
3. **Step 3: Findings Transmission** - Results in both JSON and human-readable formats

## Features

- Image upload support (JPG, PNG, JPEG formats)
- JSON metadata input with validation
- Integration with Google Vertex AI Gemini 2.5 Flash model
- Structured 3-step workflow analysis
- Dual-format output (JSON and human-readable)
- Comprehensive error handling and user feedback

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with Vertex AI API enabled
- Service account credentials with appropriate permissions

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd dam-compliance-analyzer
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Google Cloud Setup

1. Create a Google Cloud Project and enable the Vertex AI API
2. Create a service account with the following roles:
   - Vertex AI User (`roles/aiplatform.user`)
   - Storage Object Viewer (`roles/storage.objectViewer`) - if needed
3. Download the service account key as JSON

### Streamlit Secrets Configuration

Create a `.streamlit/secrets.toml` file in your project root:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"

# Optional: Vertex AI Configuration
[vertex_ai]
location = "us-central1"
model_name = "gemini-2.0-flash-exp"

# Optional: Application Configuration
[app_config]
max_image_size_mb = 10
supported_formats = ["jpg", "jpeg", "png"]
timeout_seconds = 300
```

### Environment Variables

Alternatively, you can use environment variables instead of or in addition to secrets:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GCP_PROJECT_ID` | Google Cloud Project ID | None | Yes |
| `GCP_LOCATION` | Vertex AI location | us-central1 | No |
| `MODEL_NAME` | Gemini model name | gemini-2.0-flash-exp | No |
| `MAX_UPLOAD_SIZE` | Maximum file upload size (MB) | 10 | No |
| `TIMEOUT_SECONDS` | API request timeout | 300 | No |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON file | None | Yes (if not using secrets) |

### Sample Data

The repository includes comprehensive sample data for testing different compliance scenarios:

#### Sample Images
- `compliant_high_quality.jpg` - 4K resolution image that should pass all compliance checks
- `compliant_standard.jpg` - Full HD resolution image that passes most checks
- `non_compliant_low_res.jpg` - Low resolution image that fails resolution requirements
- `non_compliant_tiny.jpg` - Very small image that fails multiple compliance checks
- `social_media_square.jpg` - Square format image suitable for social media
- `banner_wide.jpg` - Wide format image suitable for banner use

#### Sample Metadata Files
- `complete_metadata.json` - Comprehensive metadata with all fields populated
- `minimal_metadata.json` - Basic metadata with only required fields
- `problematic_metadata.json` - Metadata with various compliance issues for testing error handling

#### Image-Metadata Mapping
- `image_metadata_mapping.json` - Links sample images to their corresponding metadata files

To generate sample images, run:
```bash
python utils/create_sample_images.py
```

## Running the Application

### Local Development

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Deployment

This application is designed to be deployed on Streamlit Community Cloud. For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

Quick deployment steps:
1. Push your code to a GitHub repository
2. Connect your repository to Streamlit Community Cloud
3. Add your secrets in the Streamlit Cloud dashboard
4. Deploy the application

For Docker deployment, local production setup, and troubleshooting, refer to the comprehensive deployment guide.

## Testing

### Running Tests

The project includes comprehensive test suites for unit, integration, and end-to-end testing:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_integration.py -v          # Integration tests
python -m pytest tests/test_app_integration.py -v     # Application integration tests
python -m pytest tests/test_full_integration.py -v    # Full workflow tests

# Run tests with coverage
python -m pytest --cov=. --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing (utils, workflow processors, etc.)
- **Integration Tests**: Component interaction testing
- **Application Tests**: End-to-end application workflow testing
- **Sample Data Tests**: Validation of sample data and metadata

### Testing with Sample Data

Use the provided sample data to verify functionality:

1. **Test with compliant images**: Should pass all checks
2. **Test with non-compliant images**: Should identify specific issues
3. **Test with various metadata**: Validate different compliance scenarios

## Usage

1. **Upload Image**: Select and upload an image file (JPG, PNG, or JPEG)
2. **Input Metadata**: Provide JSON metadata for the digital asset (optional)
3. **Run Analysis**: Click the analysis button to start the 3-step workflow
4. **View Results**: Review the results from each step in the tabbed interface

For detailed usage instructions, see [USER_GUIDE.md](USER_GUIDE.md).

## Project Structure

```
dam-compliance-analyzer/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                      # This file
├── .gitignore                     # Git ignore rules
├── .streamlit/
│   └── secrets.toml              # Streamlit secrets (not in repo)
└── .kiro/
    └── specs/
        └── dam-compliance-analyzer/
            ├── requirements.md    # Feature requirements
            ├── design.md         # Technical design
            └── tasks.md          # Implementation tasks
```

## Development

This project follows a spec-driven development approach. See the `.kiro/specs/dam-compliance-analyzer/` directory for detailed requirements, design, and implementation tasks.

## Contributing

1. Review the requirements and design documents in `.kiro/specs/dam-compliance-analyzer/`
2. Follow the implementation tasks outlined in `tasks.md`
3. Ensure all tests pass before submitting changes
4. Follow Python PEP 8 style guidelines

## License

This is a proof of concept application. Please review and comply with Google Cloud Platform terms of service and Vertex AI usage policies.

## Support

For issues related to:
- Google Cloud Platform setup: Refer to [GCP Documentation](https://cloud.google.com/docs)
- Vertex AI integration: See [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- Streamlit deployment: Check [Streamlit Documentation](https://docs.streamlit.io)

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user guide with step-by-step instructions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Detailed troubleshooting guide for common issues
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide for various environments

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your service account credentials and permissions
2. **API Quota Exceeded**: Check your Google Cloud quotas and billing
3. **Image Upload Failures**: Ensure image format is JPG, PNG, or JPEG and under size limits
4. **JSON Validation Errors**: Verify metadata JSON syntax and structure

For detailed troubleshooting steps, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Getting Help

If you encounter issues not covered in this README:
1. Check the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide
2. Review the [USER_GUIDE.md](USER_GUIDE.md) for usage instructions
3. Consult the design documents in `.kiro/specs/dam-compliance-analyzer/`
4. Create an issue in the project repository with detailed information