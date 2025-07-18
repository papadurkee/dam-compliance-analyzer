# DAM Compliance Analyzer - Main Streamlit Application
# This is the main entry point for the application

import streamlit as st
import json
import asyncio
import time
import logging
from typing import Optional, Dict, Any
from PIL import Image

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.image_processing import (
    validate_image_format, 
    convert_to_bytes, 
    generate_image_preview,
    resize_image_if_needed,
    extract_embedded_metadata,
    merge_metadata_with_embedded
)
from utils.metadata_handler import (
    validate_json_metadata,
    validate_json_metadata_enhanced,
    format_for_ai_prompt,
    get_default_metadata_structure
)
from utils.validation_errors import validate_image_upload
from utils.error_handler import ErrorContext
from workflow.engine import create_workflow_engine, WorkflowStep


def display_file_details(uploaded_file, image, embedded_metadata):
    """
    Display enhanced file details with EXIF metadata information.
    
    Args:
        uploaded_file: The uploaded file object
        image: PIL Image object
        embedded_metadata: Extracted metadata dictionary
    """
    st.markdown("**File Details:**")
    
    # Basic file information
    st.markdown(f"• **Name:** {uploaded_file.name}")
    st.markdown(f"• **Size:** {uploaded_file.size / (1024*1024):.2f} MB")
    st.markdown(f"• **Dimensions:** {image.width} x {image.height}")
    st.markdown(f"• **Format:** {image.format}")
    
    # Metadata indicator and details
    has_custom_metadata = embedded_metadata.get('has_custom_metadata', False)
    has_exif = embedded_metadata.get('has_exif', False)
    
    if has_custom_metadata or has_exif:
        if has_custom_metadata:
            st.success("📋 EXIF metadata detected!")  # Keep the same message for consistency
        else:
            st.success("📋 EXIF metadata detected!")
        
        # Show DAM-relevant metadata if available
        if 'dam_relevant' in embedded_metadata:
            dam_data = embedded_metadata['dam_relevant']
            
            # Display key metadata fields in bullet format
            # Prioritize custom metadata fields
            if 'component_id' in dam_data:
                st.markdown(f"• **Component ID:** {dam_data['component_id']}")
            if 'component_name' in dam_data:
                st.markdown(f"• **Component Name:** {dam_data['component_name']}")
            if 'component_type' in dam_data:
                st.markdown(f"• **Type:** {dam_data['component_type']}")
            if 'status' in dam_data:
                st.markdown(f"• **Status:** {dam_data['status']}")
            if 'version' in dam_data:
                st.markdown(f"• **Version:** {dam_data['version']}")
            if 'creation_date' in dam_data:
                st.markdown(f"• **Created:** {dam_data['creation_date']}")
            
            # Show usage rights if available
            if 'usage_rights' in dam_data:
                usage_rights = dam_data['usage_rights']
                if isinstance(usage_rights, dict):
                    if 'licenseType' in usage_rights:
                        st.markdown(f"• **License:** {usage_rights['licenseType']}")
                    if 'usageRestrictions' in usage_rights:
                        st.markdown(f"• **Usage:** {usage_rights['usageRestrictions']}")
            
            # Show restrictions
            if 'geographic_restrictions' in dam_data:
                restrictions = dam_data['geographic_restrictions']
                if restrictions:
                    st.markdown(f"• **Geographic:** {', '.join(restrictions)}")
            
            if 'channel_restrictions' in dam_data:
                channels = dam_data['channel_restrictions']
                if channels:
                    st.markdown(f"• **Channels:** {', '.join(channels)}")
            
            # Fallback to traditional EXIF fields if no custom metadata
            if not has_custom_metadata:
                if 'photographer' in dam_data:
                    st.markdown(f"• **Photographer:** {dam_data['photographer']}")
                if 'copyright' in dam_data:
                    st.markdown(f"• **Copyright:** {dam_data['copyright']}")
                if 'shoot_date' in dam_data:
                    st.markdown(f"• **Date Taken:** {dam_data['shoot_date']}")
                if 'camera_make' in dam_data:
                    camera_info = dam_data['camera_make']
                    if 'camera_model' in dam_data:
                        camera_info += f" {dam_data['camera_model']}"
                    st.markdown(f"• **Camera:** {camera_info}")
                
                # Technical settings
                tech_settings = []
                if 'iso_speed' in dam_data:
                    tech_settings.append(f"ISO {dam_data['iso_speed']}")
                if 'aperture' in dam_data:
                    tech_settings.append(f"f/{dam_data['aperture']}")
                if 'exposure_time' in dam_data:
                    tech_settings.append(f"{dam_data['exposure_time']}s")
                
                if tech_settings:
                    st.markdown(f"• **Camera Settings:** {', '.join(tech_settings)}")
                
                # Location data
                if dam_data.get('has_location_data'):
                    st.markdown("• **Location:** GPS data available")
            
            # Show expandable detailed metadata
            with st.expander("🔍 View All Metadata"):
                if has_custom_metadata:
                    custom_data = embedded_metadata.get('custom_metadata', {})
                    if custom_data:
                        st.markdown("**Custom Metadata:**")
                        for key, value in custom_data.items():
                            if isinstance(value, dict):
                                st.json(value)
                            else:
                                st.markdown(f"**{key}:** {value}")
                
                exif_data = embedded_metadata.get('exif_data', {})
                if exif_data:
                    st.markdown("**EXIF Data:**")
                    for key, value in exif_data.items():
                        if key != 'extraction_error':
                            st.markdown(f"**{key}:** {value}")
                
                if not custom_data and not exif_data:
                    st.info("No detailed metadata available")
    else:
        st.info("ℹ️ No metadata found in this image")


def create_metadata_from_exif(filename, embedded_metadata):
    """
    Create a JSON metadata structure from EXIF and custom metadata.
    
    Args:
        filename: Name of the uploaded file
        embedded_metadata: Extracted metadata dictionary
        
    Returns:
        Dict[str, Any]: JSON metadata structure populated with extracted data
    """
    # Check if we have custom metadata (like componentMetadata)
    custom_metadata = embedded_metadata.get('custom_metadata', {})
    
    # If we found embedded JSON metadata, use it as the primary source
    if custom_metadata:
        # Look for componentMetadata in various locations
        component_metadata = None
        
        # Check different possible locations for the metadata
        for key, value in custom_metadata.items():
            if isinstance(value, dict):
                if 'componentMetadata' in value:
                    component_metadata = value['componentMetadata']
                    break
                elif 'id' in value and 'name' in value:
                    # Direct component metadata
                    component_metadata = value
                    break
        
        if component_metadata:
            # Convert the embedded metadata to our expected format
            return convert_component_metadata_to_standard_format(component_metadata, embedded_metadata)
    
    # Fallback to EXIF-based metadata creation
    return create_metadata_from_exif_fallback(filename, embedded_metadata)


def convert_component_metadata_to_standard_format(component_metadata, embedded_metadata):
    """
    Convert componentMetadata format to our standard metadata format.
    
    Args:
        component_metadata: The componentMetadata object from the image
        embedded_metadata: Full embedded metadata for additional info
        
    Returns:
        Dict[str, Any]: Converted metadata in standard format
    """
    # Start with default structure
    metadata = get_default_metadata_structure()
    
    # Map componentMetadata fields to our format
    if 'id' in component_metadata:
        metadata['component_id'] = component_metadata['id']
    
    if 'name' in component_metadata:
        metadata['component_name'] = component_metadata['name']
    
    if 'description' in component_metadata:
        metadata['description'] = component_metadata['description']
    
    # Map usage rights
    if 'usageRights' in component_metadata:
        usage_rights = component_metadata['usageRights']
        metadata['usage_rights'] = {
            'commercial_use': usage_rights.get('licenseType', ''),
            'editorial_use': usage_rights.get('owner', ''),
            'restrictions': usage_rights.get('usageRestrictions', '')
        }
    
    # Map geographic restrictions
    if 'geographicRestrictions' in component_metadata:
        metadata['geographic_restrictions'] = component_metadata['geographicRestrictions']
    
    # Map channel requirements
    if 'channelRestrictions' in component_metadata:
        channels = component_metadata['channelRestrictions']
        metadata['channel_requirements'] = {
            'web': 'Digital' in channels,
            'print': 'Print' in channels,
            'social_media': 'Social Media' in channels,
            'broadcast': 'Broadcast' in channels if 'Broadcast' in channels else ''
        }
    
    # Map file specifications
    file_specs = {}
    if 'fileFormat' in component_metadata:
        file_specs['format'] = component_metadata['fileFormat']
    
    if 'dimensions' in component_metadata:
        dims = component_metadata['dimensions']
        if 'width' in dims and 'height' in dims:
            file_specs['resolution'] = f"{dims['width']}x{dims['height']}"
    
    if 'colorSpace' in component_metadata:
        file_specs['color_profile'] = component_metadata['colorSpace']
    
    if 'fileSize' in component_metadata:
        file_specs['file_size'] = component_metadata['fileSize']
    
    metadata['file_specifications'] = file_specs
    
    # Add additional metadata fields
    additional_metadata = {}
    
    if 'version' in component_metadata:
        additional_metadata['version'] = component_metadata['version']
    
    if 'creationDate' in component_metadata:
        additional_metadata['creation_date'] = component_metadata['creationDate']
    
    if 'lastModifiedDate' in component_metadata:
        additional_metadata['last_modified_date'] = component_metadata['lastModifiedDate']
    
    if 'status' in component_metadata:
        additional_metadata['status'] = component_metadata['status']
    
    if 'componentType' in component_metadata:
        additional_metadata['component_type'] = component_metadata['componentType']
    
    if 'lifespan' in component_metadata:
        lifespan = component_metadata['lifespan']
        additional_metadata['lifespan'] = {
            'start_date': lifespan.get('startDate', ''),
            'end_date': lifespan.get('endDate', '')
        }
    
    if additional_metadata:
        metadata['additional_metadata'] = additional_metadata
    
    return metadata


def create_metadata_from_exif_fallback(filename, embedded_metadata):
    """
    Fallback method to create metadata from EXIF data when no custom metadata is found.
    
    Args:
        filename: Name of the uploaded file
        embedded_metadata: Extracted metadata dictionary
        
    Returns:
        Dict[str, Any]: JSON metadata structure populated with EXIF data
    """
    # Start with default structure
    metadata = get_default_metadata_structure()
    
    # Extract component ID from filename (remove extension)
    component_id = filename.rsplit('.', 1)[0].upper()
    metadata['component_id'] = component_id
    metadata['component_name'] = filename
    
    # Add basic file information
    basic_info = embedded_metadata.get('basic_info', {})
    if basic_info:
        if basic_info.get('format'):
            metadata['file_specifications']['format'] = basic_info['format']
        if basic_info.get('width') and basic_info.get('height'):
            metadata['file_specifications']['resolution'] = f"{basic_info['width']}x{basic_info['height']}"
    
    # Add DAM-relevant metadata if available
    if embedded_metadata.get('has_exif') and 'dam_relevant' in embedded_metadata:
        dam_data = embedded_metadata['dam_relevant']
        
        # Add additional metadata fields section for EXIF data
        if 'photographer' in dam_data or 'copyright' in dam_data or 'shoot_date' in dam_data:
            metadata['additional_metadata'] = {}
            
            if 'photographer' in dam_data:
                metadata['additional_metadata']['photographer'] = dam_data['photographer']
            
            if 'copyright' in dam_data:
                metadata['additional_metadata']['copyright'] = dam_data['copyright']
            
            if 'shoot_date' in dam_data:
                metadata['additional_metadata']['creation_date'] = dam_data['shoot_date']
        
        # Add camera information to description
        camera_info = []
        if 'camera_make' in dam_data:
            camera_info.append(dam_data['camera_make'])
        if 'camera_model' in dam_data:
            camera_info.append(dam_data['camera_model'])
        
        if camera_info:
            camera_desc = f"Captured with {' '.join(camera_info)}"
            
            # Add technical settings to description
            tech_settings = []
            if 'iso_speed' in dam_data:
                tech_settings.append(f"ISO {dam_data['iso_speed']}")
            if 'aperture' in dam_data:
                tech_settings.append(f"f/{dam_data['aperture']}")
            if 'exposure_time' in dam_data:
                tech_settings.append(f"{dam_data['exposure_time']}s")
            
            if tech_settings:
                camera_desc += f" ({', '.join(tech_settings)})"
            
            metadata['description'] = camera_desc
        
        # Add color space information if available
        if 'color_space' in dam_data:
            metadata['file_specifications']['color_profile'] = str(dam_data['color_space'])
    
    # Add a note about EXIF auto-population
    if not metadata.get('description'):
        metadata['description'] = "Metadata auto-populated from EXIF data"
    else:
        metadata['description'] += " - Auto-populated from EXIF data"
    
    return metadata


def create_main_interface():
    """Creates the main application interface with title and description."""
    st.set_page_config(
        page_title="DAM Compliance Analyzer",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("🔍 DAM Compliance Analyzer")
    st.markdown("""
    **Proof of concept web application** that demonstrates how Google Vertex AI and the Gemini model 
    can be used to analyze images for Digital Asset Management (DAM) quality control and regulatory 
    compliance through a structured, multi-step workflow.
    """)
    
    st.markdown("---")


def create_image_upload_section() -> Optional[bytes]:
    """
    Creates the image upload widget with format validation and preview.
    
    Returns:
        Optional[bytes]: Image bytes if valid upload, None otherwise
    """
    st.subheader("📁 Image Upload")
    st.markdown("Upload an image file for compliance analysis. Supported formats: JPG, JPEG, PNG")
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['jpg', 'jpeg', 'png'],
        help="Maximum file size: 10MB"
    )
    
    if uploaded_file is not None:
        # Validate the uploaded file using enhanced validation
        context = ErrorContext(operation="image_upload", step="validation", component="file_validator")
        validation_result = validate_image_upload(uploaded_file, context)
        
        if not validation_result.is_valid:
            st.error(f"❌ {validation_result.error_details.user_message}")
            
            # Show recovery suggestions
            if validation_result.error_details.recovery_suggestions:
                with st.expander("💡 How to fix this issue"):
                    for suggestion in validation_result.error_details.recovery_suggestions:
                        st.markdown(f"• {suggestion}")
            return None
        
        # Show any warnings
        if validation_result.warnings:
            for warning in validation_result.warnings:
                st.warning(f"⚠️ {warning}")
        
        # Display image preview
        try:
            image = generate_image_preview(uploaded_file)
            resized_image = resize_image_if_needed(image, max_width=600)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.image(resized_image, caption=f"Preview: {uploaded_file.name}")
            
            with col2:
                st.success("✅ Image uploaded successfully!")
                
                # Extract and display embedded metadata
                try:
                    embedded_metadata = extract_embedded_metadata(uploaded_file)
                    
                    # Display file details with enhanced metadata
                    display_file_details(uploaded_file, image, embedded_metadata)
                    
                    # Store embedded metadata in session state for later use
                    st.session_state.embedded_metadata = embedded_metadata
                    
                    # Auto-populate JSON metadata if EXIF detected
                    if embedded_metadata.get('has_exif'):
                        auto_metadata = create_metadata_from_exif(uploaded_file.name, embedded_metadata)
                        st.session_state.auto_populated_metadata = json.dumps(auto_metadata, indent=2)
                    else:
                        st.session_state.auto_populated_metadata = None
                        
                except Exception as e:
                    st.warning(f"⚠️ Could not extract metadata: {str(e)}")
                    st.session_state.embedded_metadata = None
                    st.session_state.auto_populated_metadata = None
            
            # Convert to bytes for processing
            image_bytes = convert_to_bytes(uploaded_file)
            return image_bytes
            
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
            return None
    
    return None


def create_metadata_input_section() -> Optional[Dict[str, Any]]:
    """
    Creates the JSON metadata input area with syntax validation.
    
    Returns:
        Optional[Dict[str, Any]]: Parsed metadata if valid, None otherwise
    """
    st.subheader("📝 Component Metadata")
    st.markdown("Provide metadata about the digital asset in JSON format (optional)")
    
    # Create two columns for input and example
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("**Example Structure:**")
        example_metadata = get_default_metadata_structure()
        example_metadata.update({
            "component_id": "IMG_001",
            "component_name": "Product Hero Image",
            "description": "Main product image for marketing campaign"
        })
        st.code(json.dumps(example_metadata, indent=2), language="json")
    
    with col1:
        # Check if we have auto-populated metadata from EXIF
        default_value = ""
        if hasattr(st.session_state, 'auto_populated_metadata') and st.session_state.auto_populated_metadata:
            default_value = st.session_state.auto_populated_metadata
            st.success("📋 EXIF metadata detected! JSON automatically populated below.")
        
        metadata_input = st.text_area(
            "JSON Metadata",
            value=default_value,
            height=300,
            placeholder="Enter JSON metadata here, or leave empty to use defaults...",
            help="Provide component metadata in valid JSON format. EXIF data will auto-populate when available."
        )
        
        if metadata_input.strip():
            # Validate JSON syntax using enhanced validation
            context = ErrorContext(operation="metadata_input", step="validation", component="json_validator")
            validation_result = validate_json_metadata_enhanced(metadata_input, context)
            
            if not validation_result.is_valid:
                st.error(f"❌ JSON Validation Error")
                
                # Display the detailed error message
                st.markdown(f"```\n{validation_result.error_details.user_message}\n```")
                
                # Show recovery suggestions
                if validation_result.error_details.recovery_suggestions:
                    with st.expander("💡 How to fix this issue"):
                        for suggestion in validation_result.error_details.recovery_suggestions:
                            st.markdown(f"• {suggestion}")
                return None
            else:
                st.success("✅ Valid JSON metadata provided")
                
                # Show any warnings
                if validation_result.warnings:
                    for warning in validation_result.warnings:
                        st.warning(f"⚠️ {warning}")
                
                # Parse the JSON to get the data
                parsed_data = json.loads(metadata_input)
                
                # Show formatted preview
                with st.expander("Preview Formatted Metadata"):
                    formatted_metadata = format_for_ai_prompt(parsed_data)
                    st.text(formatted_metadata)
                
                return parsed_data
        else:
            st.info("ℹ️ No metadata provided - default structure will be used")
            return {}


async def execute_workflow_analysis(image_bytes: bytes, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute the complete workflow analysis.
    
    Args:
        image_bytes: Image data for analysis
        metadata: Component metadata
        
    Returns:
        Dict[str, Any]: Workflow results
    """
    try:
        # Merge embedded metadata with user-provided metadata if available
        final_metadata = metadata or {}
        
        # Check if we have embedded metadata in session state
        if hasattr(st.session_state, 'embedded_metadata') and st.session_state.embedded_metadata:
            logger.info("Merging embedded EXIF metadata with user-provided metadata")
            final_metadata = merge_metadata_with_embedded(final_metadata, st.session_state.embedded_metadata)
        
        # Create workflow engine
        engine = await create_workflow_engine()
        
        # Execute workflow with merged metadata
        final_state = await engine.execute_workflow(image_bytes, final_metadata)
        
        # Get results
        results = engine.get_workflow_results()
        
        return results
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return {
            "workflow_complete": False,
            "error": f"Workflow execution failed: {str(e)}"
        }


def display_workflow_progress(step_name: str, step_number: int, total_steps: int = 3):
    """
    Display progress indicator for workflow steps.
    
    Args:
        step_name: Name of the current step
        step_number: Current step number (1-3)
        total_steps: Total number of steps
    """
    progress = step_number / total_steps
    st.progress(progress, text=f"Step {step_number}/{total_steps}: {step_name}")


def display_step_results(step_name: str, step_data: Dict[str, Any], step_number: int):
    """
    Generic function to display step results in an expandable format.
    
    Args:
        step_name: Name of the step (e.g., "DAM Analysis")
        step_data: Step result data
        step_number: Step number (1-3)
    """
    with st.expander(f"📋 Step {step_number}: {step_name}", expanded=True):
        if step_number == 1:
            display_step1_results(step_data)
        elif step_number == 2:
            display_step2_results(step_data)
        elif step_number == 3:
            display_step3_results(step_data)
        else:
            st.warning(f"Unknown step number: {step_number}")


def display_step1_results(step_data: Dict[str, Any]):
    """Display formatted Step 1: DAM Analysis results."""
    if not step_data:
        st.warning("No data available for Step 1")
        return
    
    # Analysis Notes
    if "notes" in step_data:
        st.subheader("🔍 Analysis Notes")
        st.markdown(step_data["notes"])
        st.markdown("---")
    
    # Job Aid Assessment
    if "job_aid_assessment" in step_data:
        st.subheader("📋 Job Aid Assessment")
        job_aid = step_data["job_aid_assessment"]
        
        # Parse job aid if it's a string
        if isinstance(job_aid, str):
            try:
                import json
                job_aid = json.loads(job_aid)
            except json.JSONDecodeError:
                # If it's not valid JSON, display as text
                st.markdown(job_aid)
                return
        
        # Ensure job_aid is a dictionary
        if isinstance(job_aid, dict):
            # Display the assessment categories with their status indicators
            categories = list(job_aid.keys())
            if len(categories) <= 4:
                cols = st.columns(len(categories))
                for i, (category, category_data) in enumerate(job_aid.items()):
                    with cols[i]:
                        category_title = category.replace("_", " ").title()
                        
                        # Extract assessment status if it's a nested structure
                        if isinstance(category_data, dict) and "assessment" in category_data:
                            assessment = category_data["assessment"]
                            
                            # Display with appropriate color coding
                            if assessment == "PASS":
                                st.success(f"✅ {category_title}")
                                st.caption("PASS")
                            elif assessment == "FAIL":
                                st.error(f"❌ {category_title}")
                                st.caption("FAIL")
                            elif assessment == "NEEDS_REVIEW":
                                st.warning(f"⚠️ {category_title}")
                                st.caption("NEEDS REVIEW")
                            else:
                                st.info(f"ℹ️ {category_title}")
                                st.caption(str(assessment))
                        else:
                            # Fallback for simple values
                            st.metric(
                                label=category_title,
                                value=str(category_data)
                            )
            else:
                # Display as a formatted list for many items
                for category, category_data in job_aid.items():
                    category_title = category.replace("_", " ").title()
                    
                    if isinstance(category_data, dict) and "assessment" in category_data:
                        assessment = category_data["assessment"]
                        
                        # Display with appropriate color coding
                        if assessment == "PASS":
                            st.success(f"✅ **{category_title}:** PASS")
                        elif assessment == "FAIL":
                            st.error(f"❌ **{category_title}:** FAIL")
                        elif assessment == "NEEDS_REVIEW":
                            st.warning(f"⚠️ **{category_title}:** NEEDS REVIEW")
                        else:
                            st.info(f"ℹ️ **{category_title}:** {assessment}")
                        
                        # Show issues if present
                        if "issues" in category_data and category_data["issues"]:
                            for issue in category_data["issues"]:
                                st.caption(f"• {issue}")
                    else:
                        st.markdown(f"**{category_title}:** {category_data}")
            
            # Also show raw JSON in expander
            with st.expander("View Raw JSON"):
                st.json(job_aid)
        else:
            # If it's not a dict, display as text
            st.markdown(str(job_aid))
        
        st.markdown("---")
    
    # Human-Readable Summary
    if "human_readable_section" in step_data:
        st.subheader("📄 Summary")
        st.markdown(step_data["human_readable_section"])
        st.markdown("---")
    
    # Next Steps
    if "next_steps" in step_data:
        st.subheader("➡️ Next Steps")
        for i, step in enumerate(step_data["next_steps"], 1):
            st.markdown(f"**{i}.** {step}")


def display_step2_results(step_data: Dict[str, Any]):
    """Display formatted Step 2: Job Aid Assessment results."""
    if not step_data:
        st.warning("No data available for Step 2")
        return
    
    # Assessment Summary
    if "assessment_summary" in step_data:
        st.subheader("📊 Assessment Summary")
        st.markdown(step_data["assessment_summary"])
        st.markdown("---")
    
    # Completed Job Aid
    if "completed_job_aid" in step_data:
        st.subheader("✅ Completed Job Aid")
        job_aid = step_data["completed_job_aid"]
        
        # Display structured job aid results
        for section_name, section_data in job_aid.items():
            st.markdown(f"**{section_name.replace('_', ' ').title()}**")
            
            if isinstance(section_data, dict):
                # Create columns for better layout
                items = list(section_data.items())
                if len(items) <= 3:
                    cols = st.columns(len(items))
                    for i, (key, value) in enumerate(items):
                        with cols[i]:
                            # Color code based on status
                            if value == "PASSED":
                                st.success(f"✅ {key.replace('_', ' ').title()}")
                            elif value == "FAILED":
                                st.error(f"❌ {key.replace('_', ' ').title()}")
                            elif value == "PARTIAL":
                                st.warning(f"⚠️ {key.replace('_', ' ').title()}")
                            else:
                                st.info(f"ℹ️ {key.replace('_', ' ').title()}: {value}")
                else:
                    # Too many items, display as list
                    for key, value in section_data.items():
                        if value == "PASSED":
                            st.success(f"✅ {key.replace('_', ' ').title()}")
                        elif value == "FAILED":
                            st.error(f"❌ {key.replace('_', ' ').title()}")
                        elif value == "PARTIAL":
                            st.warning(f"⚠️ {key.replace('_', ' ').title()}")
                        else:
                            st.info(f"ℹ️ {key.replace('_', ' ').title()}: {value}")
            else:
                st.write(section_data)
            
            st.markdown("---")
        
        # Show raw JSON in expander
        with st.expander("View Raw JSON"):
            st.json(job_aid)


def display_step3_results(step_data: Dict[str, Any]):
    """Display formatted Step 3: Findings Transmission results with JSON/human-readable toggle."""
    if not step_data:
        st.warning("No data available for Step 3")
        return
    
    # Create toggle for JSON vs Human-readable view
    view_mode = st.radio(
        "Select view format:",
        ["Human-Readable Report", "JSON Output"],
        horizontal=True,
        key="step3_view_mode"
    )
    
    st.markdown("---")
    
    if view_mode == "Human-Readable Report":
        # Display human-readable report
        if "human_readable_report" in step_data:
            st.markdown("### 📄 Compliance Analysis Report")
            
            # Parse and format the report nicely
            report = step_data["human_readable_report"]
            st.markdown(report)
        else:
            st.warning("Human-readable report not available")
            
    else:  # JSON Output
        # Display JSON output with formatted sections
        if "json_output" in step_data:
            json_data = step_data["json_output"]
            
            st.markdown("### 📋 Structured JSON Output")
            
            # Component Information
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Component ID:**")
                st.code(json_data.get("component_id", "N/A"))
            with col2:
                st.markdown("**Component Name:**")
                st.code(json_data.get("component_name", "N/A"))
            
            # Status
            status = json_data.get("check_status", "UNKNOWN")
            st.markdown("**Check Status:**")
            if status == "PASSED":
                st.success(f"✅ {status}")
            elif status == "FAILED":
                st.error(f"❌ {status}")
            else:
                st.warning(f"⚠️ {status}")
            
            # Issues Detected
            st.markdown("**Issues Detected:**")
            issues = json_data.get("issues_detected", [])
            if issues:
                for i, issue in enumerate(issues, 1):
                    with st.expander(f"Issue {i}: {issue.get('category', 'Unknown')}"):
                        st.markdown(f"**Description:** {issue.get('description', 'N/A')}")
                        st.markdown(f"**Action:** {issue.get('action', 'N/A')}")
            else:
                st.success("✅ No issues detected")
            
            # Missing Information
            st.markdown("**Missing Information:**")
            missing = json_data.get("missing_information", [])
            if missing:
                for i, item in enumerate(missing, 1):
                    with st.expander(f"Missing {i}: {item.get('field', 'Unknown')}"):
                        st.markdown(f"**Description:** {item.get('description', 'N/A')}")
                        st.markdown(f"**Action:** {item.get('action', 'N/A')}")
            else:
                st.success("✅ No missing information")
            
            # Recommendations
            st.markdown("**Recommendations:**")
            recommendations = json_data.get("recommendations", [])
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    st.markdown(f"{i}. {rec}")
            else:
                st.info("No specific recommendations")
            
            # Raw JSON in expander
            with st.expander("View Raw JSON"):
                st.json(json_data)
        else:
            # Fallback to display all step data as JSON
            st.json(step_data)


def display_workflow_execution_interface(image_bytes: Optional[bytes], metadata: Optional[Dict[str, Any]]):
    """
    Creates the workflow execution interface with loading states and progress indicators.
    
    Args:
        image_bytes: Image data for analysis
        metadata: Component metadata
    """
    st.markdown("---")
    st.subheader("🚀 Analysis Workflow")
    
    if image_bytes is None:
        st.warning("⚠️ Please upload a valid image file to proceed with analysis")
        st.button("Start Analysis", disabled=True)
        return
    
    # Analysis trigger button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        start_analysis = st.button("🔍 Start Compliance Analysis", type="primary", use_container_width=True)
    
    # Execute workflow if button is clicked
    if start_analysis:
        # Initialize session state for workflow tracking
        if 'workflow_running' not in st.session_state:
            st.session_state.workflow_running = False
        if 'workflow_results' not in st.session_state:
            st.session_state.workflow_results = None
        
        # Set workflow as running
        st.session_state.workflow_running = True
        
        # Create containers for progress and results
        progress_container = st.container()
        
        with progress_container:
            st.info("🔄 Starting workflow analysis...")
            
            # Step 1 Progress
            display_workflow_progress("DAM Analysis", 1)
            step1_placeholder = st.empty()
            
            try:
                # Show step execution progress
                with step1_placeholder:
                    st.info("🔍 Executing Step 1: DAM Analysis...")
                
                # Step 2 Progress
                display_workflow_progress("Job Aid Assessment", 2)
                step2_placeholder = st.empty()
                
                with step2_placeholder:
                    st.info("📋 Executing Step 2: Job Aid Assessment...")
                
                # Step 3 Progress
                display_workflow_progress("Findings Transmission", 3)
                step3_placeholder = st.empty()
                
                with step3_placeholder:
                    st.info("📤 Executing Step 3: Findings Transmission...")
                
                # Execute actual workflow
                with step3_placeholder:
                    st.info("🔄 Executing complete workflow analysis...")
                
                # Run the actual workflow with proper error handling
                try:
                    workflow_results = asyncio.run(execute_workflow_analysis(image_bytes, metadata))
                except Exception as workflow_error:
                    logger.error(f"Workflow execution error: {str(workflow_error)}")
                    workflow_results = {
                        "workflow_complete": False,
                        "error": f"Workflow execution failed: {str(workflow_error)}"
                    }
                
                # Clear progress indicators
                step1_placeholder.empty()
                step2_placeholder.empty()
                step3_placeholder.empty()
                
                # Check if workflow completed successfully
                if workflow_results.get("workflow_complete"):
                    st.success("✅ Workflow completed successfully!")
                else:
                    error_msg = workflow_results.get('error', 'Unknown error')
                    st.error(f"❌ Workflow failed: {error_msg}")
                    
                    # Show error details in expander
                    with st.expander("🔍 Error Details"):
                        st.text(error_msg)
                        
                        # Provide recovery suggestions
                        st.markdown("**Possible solutions:**")
                        st.markdown("• Check your internet connection")
                        st.markdown("• Verify that the Gemini API key is configured correctly")
                        st.markdown("• Try uploading a different image")
                        st.markdown("• Refresh the page and try again")
                
                st.session_state.workflow_results = workflow_results
                st.session_state.workflow_running = False
                
            except Exception as e:
                logger.error(f"UI execution error: {str(e)}")
                st.error(f"❌ Application error: {str(e)}")
                st.session_state.workflow_running = False
                st.session_state.workflow_results = {
                    "workflow_complete": False,
                    "error": f"Application error: {str(e)}"
                }
        
        # Display results if available
        if st.session_state.workflow_results:
            display_workflow_results(st.session_state.workflow_results)
    
    # Display previous results if they exist
    elif 'workflow_results' in st.session_state and st.session_state.workflow_results:
        st.info("📊 Previous analysis results:")
        display_workflow_results(st.session_state.workflow_results)


def display_workflow_results(results: Dict[str, Any]):
    """
    Display the complete workflow results with tabbed interface for Step 1, Step 2, and Step 3 results.
    
    Args:
        results: Complete workflow results
    """
    st.markdown("---")
    st.subheader("📊 Analysis Results")
    
    if results.get("error"):
        st.error(f"❌ Workflow Error: {results['error']}")
        return
    
    if not results.get("workflow_complete"):
        st.warning("⚠️ Workflow incomplete")
        return
    
    # Create tabs for each step
    tab_names = []
    tab_data = []
    
    if "step1_result" in results:
        tab_names.append("🔍 Step 1: DAM Analysis")
        tab_data.append(("step1", results["step1_result"]))
    
    if "step2_result" in results:
        tab_names.append("📋 Step 2: Job Aid Assessment")
        tab_data.append(("step2", results["step2_result"]))
    
    if "step3_result" in results:
        tab_names.append("📤 Step 3: Findings Transmission")
        tab_data.append(("step3", results["step3_result"]))
    
    # Create the tabbed interface
    if tab_names:
        tabs = st.tabs(tab_names)
        
        for i, (step_type, step_data) in enumerate(tab_data):
            with tabs[i]:
                if step_type == "step1":
                    display_step1_results(step_data)
                elif step_type == "step2":
                    display_step2_results(step_data)
                elif step_type == "step3":
                    display_step3_results(step_data)
    
    # Summary section
    st.markdown("---")
    st.subheader("📋 Analysis Summary")
    
    if "step3_result" in results and "json_output" in results["step3_result"]:
        final_result = results["step3_result"]["json_output"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = final_result.get("check_status", "UNKNOWN")
            if status == "PASSED":
                st.success(f"✅ Status: {status}")
            elif status == "FAILED":
                st.error(f"❌ Status: {status}")
            else:
                st.warning(f"⚠️ Status: {status}")
        
        with col2:
            issues_count = len(final_result.get("issues_detected", []))
            if issues_count == 0:
                st.success(f"✅ Issues: {issues_count}")
            else:
                st.warning(f"⚠️ Issues: {issues_count}")
        
        with col3:
            missing_count = len(final_result.get("missing_information", []))
            if missing_count == 0:
                st.success(f"✅ Missing Info: {missing_count}")
            else:
                st.info(f"ℹ️ Missing Info: {missing_count}")
    
    # Add option to restart analysis
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Run New Analysis", use_container_width=True):
            # Clear session state to allow new analysis
            if 'workflow_results' in st.session_state:
                del st.session_state.workflow_results
            if 'workflow_running' in st.session_state:
                del st.session_state.workflow_running
            st.rerun()


def display_instructions():
    """Displays usage instructions for the application."""
    with st.expander("📖 How to Use This Application"):
        st.markdown("""
        ### Step-by-Step Instructions:
        
        1. **Upload Image**: Choose a JPG, JPEG, or PNG file (max 10MB)
        2. **Add Metadata** (Optional): Provide component information in JSON format
        3. **Start Analysis**: Click the analysis button to begin the 3-step workflow
        4. **Review Results**: View the compliance assessment results
        
        ### Analysis Workflow:
        
        The application performs a **3-step analysis process**:
        
        - **Step 1: DAM Analysis** - Professional assessment by AI DAM Analyst
        - **Step 2: Job Aid Assessment** - Structured compliance checklist evaluation  
        - **Step 3: Findings Transmission** - Final results in JSON and human-readable formats
        
        ### Supported File Formats:
        - JPG/JPEG images
        - PNG images
        - Maximum file size: 10MB
        
        ### Metadata Format:
        Metadata should be provided as valid JSON with component information such as:
        - Component ID and name
        - Usage rights and restrictions
        - Channel requirements
        - File specifications
        """)


def main():
    """Main application entry point."""
    # Create the main interface
    create_main_interface()
    
    # Display usage instructions
    display_instructions()
    
    # Image upload section
    image_bytes = create_image_upload_section()
    
    st.markdown("---")
    
    # Metadata input section
    metadata = create_metadata_input_section()
    
    # Workflow execution interface
    display_workflow_execution_interface(image_bytes, metadata)


if __name__ == "__main__":
    main()