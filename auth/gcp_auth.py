"""
Google Cloud Platform Authentication Manager

This module handles authentication with Google Cloud Platform using service account credentials
loaded from Streamlit secrets. It provides credential validation and error handling.
"""

import json
import logging
from typing import Dict, Any, Optional
from google.auth import credentials
from google.oauth2 import service_account
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
import streamlit as st

logger = logging.getLogger(__name__)


class GCPAuthenticationError(Exception):
    """Custom exception for GCP authentication errors"""
    pass


class GCPAuthManager:
    """
    Manages Google Cloud Platform authentication using service account credentials.
    
    This class handles loading credentials from Streamlit secrets, validating them,
    and providing authenticated credentials for GCP services.
    """
    
    def __init__(self):
        self._credentials: Optional[service_account.Credentials] = None
        self._project_id: Optional[str] = None
    
    def load_service_account_credentials(self) -> service_account.Credentials:
        """
        Load service account credentials from Streamlit secrets.
        
        Returns:
            service_account.Credentials: Authenticated credentials object
            
        Raises:
            GCPAuthenticationError: If credentials cannot be loaded or are invalid
        """
        try:
            # Load credentials from Streamlit secrets
            if "gcp_service_account" not in st.secrets:
                raise GCPAuthenticationError(
                    "GCP service account credentials not found in Streamlit secrets. "
                    "Please configure 'gcp_service_account' in your secrets."
                )
            
            # Get the service account info from secrets
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            # Validate required fields
            required_fields = [
                "type", "project_id", "private_key_id", "private_key",
                "client_email", "client_id", "auth_uri", "token_uri"
            ]
            
            missing_fields = [field for field in required_fields if field not in service_account_info]
            if missing_fields:
                raise GCPAuthenticationError(
                    f"Missing required fields in service account credentials: {missing_fields}"
                )
            
            # Create credentials from service account info
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            self._project_id = service_account_info["project_id"]
            
            logger.info(f"Successfully loaded service account credentials for project: {self._project_id}")
            return self._credentials
            
        except KeyError as e:
            error_msg = f"Missing key in service account credentials: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in service account credentials: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
        
        except GoogleAuthError as e:
            error_msg = f"Google Auth error: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error loading credentials: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
    
    def validate_credentials(self) -> bool:
        """
        Validate that the loaded credentials are valid and have necessary permissions.
        
        Returns:
            bool: True if credentials are valid, False otherwise
            
        Raises:
            GCPAuthenticationError: If credentials are not loaded or validation fails
        """
        if not self._credentials:
            raise GCPAuthenticationError(
                "Credentials not loaded. Call load_service_account_credentials() first."
            )
        
        try:
            # Check if credentials are expired and refresh if needed
            if not self._credentials.valid:
                if self._credentials.expired:
                    self._credentials.refresh(Request())
                else:
                    raise GCPAuthenticationError("Credentials are invalid and cannot be refreshed")
            
            # Validate that we have the required scopes
            if not self._credentials.has_scopes(['https://www.googleapis.com/auth/cloud-platform']):
                logger.warning("Credentials may not have required cloud-platform scope")
            
            logger.info("Credentials validation successful")
            return True
            
        except GoogleAuthError as e:
            error_msg = f"Credential validation failed: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during credential validation: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
    
    def get_credentials(self) -> service_account.Credentials:
        """
        Get the loaded and validated credentials.
        
        Returns:
            service_account.Credentials: The authenticated credentials
            
        Raises:
            GCPAuthenticationError: If credentials are not loaded
        """
        if not self._credentials:
            raise GCPAuthenticationError(
                "Credentials not loaded. Call load_service_account_credentials() first."
            )
        
        return self._credentials
    
    def get_project_id(self) -> str:
        """
        Get the project ID from the loaded credentials.
        
        Returns:
            str: The GCP project ID
            
        Raises:
            GCPAuthenticationError: If credentials are not loaded
        """
        if not self._project_id:
            raise GCPAuthenticationError(
                "Project ID not available. Call load_service_account_credentials() first."
            )
        
        return self._project_id
    
    def refresh_token_if_needed(self) -> None:
        """
        Refresh the authentication token if it's expired or about to expire.
        
        Raises:
            GCPAuthenticationError: If token refresh fails
        """
        if not self._credentials:
            raise GCPAuthenticationError(
                "Credentials not loaded. Call load_service_account_credentials() first."
            )
        
        try:
            if not self._credentials.valid:
                if self._credentials.expired and hasattr(self._credentials, 'refresh'):
                    from google.auth.transport.requests import Request
                    self._credentials.refresh(Request())
                    logger.info("Successfully refreshed authentication token")
                else:
                    raise GCPAuthenticationError("Cannot refresh expired credentials")
        
        except GoogleAuthError as e:
            error_msg = f"Token refresh failed: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during token refresh: {str(e)}"
            logger.error(error_msg)
            raise GCPAuthenticationError(error_msg)


# Singleton instance for global use
_auth_manager = None


def get_auth_manager() -> GCPAuthManager:
    """
    Get the singleton GCP authentication manager instance.
    
    Returns:
        GCPAuthManager: The authentication manager instance
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GCPAuthManager()
    return _auth_manager


def initialize_gcp_auth() -> GCPAuthManager:
    """
    Initialize GCP authentication by loading and validating credentials.
    
    Returns:
        GCPAuthManager: The initialized authentication manager
        
    Raises:
        GCPAuthenticationError: If initialization fails
    """
    auth_manager = get_auth_manager()
    auth_manager.load_service_account_credentials()
    auth_manager.validate_credentials()
    return auth_manager