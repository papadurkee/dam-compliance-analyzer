"""
Unit tests for Google Cloud Platform authentication manager.

Tests the GCPAuthManager class functionality including credential loading,
validation, and error handling scenarios.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account

from auth.gcp_auth import (
    GCPAuthManager,
    GCPAuthenticationError,
    get_auth_manager,
    initialize_gcp_auth
)


class TestGCPAuthManager:
    """Test cases for GCPAuthManager class"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a GCPAuthManager instance for testing"""
        return GCPAuthManager()
    
    @pytest.fixture
    def valid_service_account_info(self):
        """Valid service account info for testing"""
        return {
            "type": "service_account",
            "project_id": "test-project-123",
            "private_key_id": "key-id-123",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project-123.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    
    @patch('auth.gcp_auth.st')
    @patch('auth.gcp_auth.service_account.Credentials.from_service_account_info')
    def test_load_service_account_credentials_success(self, mock_from_info, mock_st, 
                                                     auth_manager, valid_service_account_info):
        """Test successful loading of service account credentials"""
        # Setup mocks
        mock_st.secrets = {"gcp_service_account": valid_service_account_info}
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_from_info.return_value = mock_credentials
        
        # Test the method
        result = auth_manager.load_service_account_credentials()
        
        # Verify results
        assert result == mock_credentials
        assert auth_manager._credentials == mock_credentials
        assert auth_manager._project_id == "test-project-123"
        
        # Verify service account creation was called with correct parameters
        mock_from_info.assert_called_once_with(
            valid_service_account_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
    
    @patch('auth.gcp_auth.st')
    def test_load_service_account_credentials_missing_secrets(self, mock_st, auth_manager):
        """Test loading credentials when secrets are missing"""
        # Setup mocks
        mock_st.secrets = {}  # No gcp_service_account key
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="GCP service account credentials not found"):
            auth_manager.load_service_account_credentials()
    
    @patch('auth.gcp_auth.st')
    def test_load_service_account_credentials_missing_required_fields(self, mock_st, auth_manager):
        """Test loading credentials with missing required fields"""
        # Setup mocks - missing private_key field
        incomplete_info = {
            "type": "service_account",
            "project_id": "test-project-123",
            "client_email": "test@test-project-123.iam.gserviceaccount.com"
            # Missing other required fields
        }
        mock_st.secrets = {"gcp_service_account": incomplete_info}
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Missing required fields"):
            auth_manager.load_service_account_credentials()
    
    @patch('auth.gcp_auth.st')
    @patch('auth.gcp_auth.service_account.Credentials.from_service_account_info')
    def test_load_service_account_credentials_google_auth_error(self, mock_from_info, mock_st,
                                                               auth_manager, valid_service_account_info):
        """Test loading credentials when Google Auth raises an error"""
        # Setup mocks
        mock_st.secrets = {"gcp_service_account": valid_service_account_info}
        mock_from_info.side_effect = GoogleAuthError("Invalid credentials")
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Google Auth error"):
            auth_manager.load_service_account_credentials()
    
    @patch('auth.gcp_auth.st')
    @patch('auth.gcp_auth.service_account.Credentials.from_service_account_info')
    def test_load_service_account_credentials_unexpected_error(self, mock_from_info, mock_st,
                                                              auth_manager, valid_service_account_info):
        """Test loading credentials when an unexpected error occurs"""
        # Setup mocks
        mock_st.secrets = {"gcp_service_account": valid_service_account_info}
        mock_from_info.side_effect = Exception("Unexpected error")
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Unexpected error loading credentials"):
            auth_manager.load_service_account_credentials()
    
    def test_validate_credentials_not_loaded(self, auth_manager):
        """Test validating credentials when they haven't been loaded"""
        with pytest.raises(GCPAuthenticationError, match="Credentials not loaded"):
            auth_manager.validate_credentials()
    
    @patch('auth.gcp_auth.Request')
    def test_validate_credentials_valid(self, mock_request, auth_manager):
        """Test validating valid credentials"""
        # Setup mocks
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = True
        mock_credentials.has_scopes.return_value = True
        auth_manager._credentials = mock_credentials
        
        # Test the method
        result = auth_manager.validate_credentials()
        
        # Verify results
        assert result is True
        mock_credentials.has_scopes.assert_called_once_with(['https://www.googleapis.com/auth/cloud-platform'])
    
    @patch('auth.gcp_auth.Request')
    def test_validate_credentials_expired_refresh_success(self, mock_request, auth_manager):
        """Test validating expired credentials that can be refreshed"""
        # Setup mocks
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.has_scopes.return_value = True
        auth_manager._credentials = mock_credentials
        
        # After refresh, credentials become valid
        def refresh_side_effect(request):
            mock_credentials.valid = True
        
        mock_credentials.refresh.side_effect = refresh_side_effect
        
        # Test the method
        result = auth_manager.validate_credentials()
        
        # Verify results
        assert result is True
        mock_credentials.refresh.assert_called_once()
    
    @patch('auth.gcp_auth.Request')
    def test_validate_credentials_invalid_cannot_refresh(self, mock_request, auth_manager):
        """Test validating invalid credentials that cannot be refreshed"""
        # Setup mocks
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = False  # Not expired, just invalid
        auth_manager._credentials = mock_credentials
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Credentials are invalid and cannot be refreshed"):
            auth_manager.validate_credentials()
    
    @patch('auth.gcp_auth.Request')
    def test_validate_credentials_refresh_error(self, mock_request, auth_manager):
        """Test validating credentials when refresh fails"""
        # Setup mocks
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh.side_effect = GoogleAuthError("Refresh failed")
        auth_manager._credentials = mock_credentials
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Credential validation failed"):
            auth_manager.validate_credentials()
    
    def test_get_credentials_not_loaded(self, auth_manager):
        """Test getting credentials when they haven't been loaded"""
        with pytest.raises(GCPAuthenticationError, match="Credentials not loaded"):
            auth_manager.get_credentials()
    
    def test_get_credentials_success(self, auth_manager):
        """Test getting loaded credentials"""
        # Setup
        mock_credentials = Mock(spec=service_account.Credentials)
        auth_manager._credentials = mock_credentials
        
        # Test the method
        result = auth_manager.get_credentials()
        
        # Verify results
        assert result == mock_credentials
    
    def test_get_project_id_not_loaded(self, auth_manager):
        """Test getting project ID when credentials haven't been loaded"""
        with pytest.raises(GCPAuthenticationError, match="Project ID not available"):
            auth_manager.get_project_id()
    
    def test_get_project_id_success(self, auth_manager):
        """Test getting project ID from loaded credentials"""
        # Setup
        auth_manager._project_id = "test-project-123"
        
        # Test the method
        result = auth_manager.get_project_id()
        
        # Verify results
        assert result == "test-project-123"
    
    def test_refresh_token_if_needed_not_loaded(self, auth_manager):
        """Test refreshing token when credentials haven't been loaded"""
        with pytest.raises(GCPAuthenticationError, match="Credentials not loaded"):
            auth_manager.refresh_token_if_needed()
    
    @patch('auth.gcp_auth.Request')
    def test_refresh_token_if_needed_valid_credentials(self, mock_request, auth_manager):
        """Test refreshing token when credentials are already valid"""
        # Setup
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = True
        auth_manager._credentials = mock_credentials
        
        # Test the method
        auth_manager.refresh_token_if_needed()
        
        # Verify refresh was not called
        mock_credentials.refresh.assert_not_called()
    
    @patch('auth.gcp_auth.Request')
    def test_refresh_token_if_needed_expired_success(self, mock_request, auth_manager):
        """Test refreshing expired token successfully"""
        # Setup
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = True
        auth_manager._credentials = mock_credentials
        
        # Test the method
        auth_manager.refresh_token_if_needed()
        
        # Verify refresh was called
        mock_credentials.refresh.assert_called_once()
    
    @patch('auth.gcp_auth.Request')
    def test_refresh_token_if_needed_cannot_refresh(self, mock_request, auth_manager):
        """Test refreshing token when credentials cannot be refreshed"""
        # Setup
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = False  # Not expired, just invalid
        auth_manager._credentials = mock_credentials
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Cannot refresh expired credentials"):
            auth_manager.refresh_token_if_needed()
    
    @patch('auth.gcp_auth.Request')
    def test_refresh_token_if_needed_refresh_error(self, mock_request, auth_manager):
        """Test refreshing token when refresh fails"""
        # Setup
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh.side_effect = GoogleAuthError("Refresh failed")
        auth_manager._credentials = mock_credentials
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Token refresh failed"):
            auth_manager.refresh_token_if_needed()


class TestGlobalFunctions:
    """Test global convenience functions"""
    
    def test_get_auth_manager_singleton(self):
        """Test that get_auth_manager returns the same instance"""
        manager1 = get_auth_manager()
        manager2 = get_auth_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, GCPAuthManager)
    
    @patch('auth.gcp_auth.get_auth_manager')
    def test_initialize_gcp_auth_success(self, mock_get_manager):
        """Test successful GCP authentication initialization"""
        # Setup mocks
        mock_manager = Mock(spec=GCPAuthManager)
        mock_get_manager.return_value = mock_manager
        
        # Test the function
        result = initialize_gcp_auth()
        
        # Verify results
        assert result == mock_manager
        mock_manager.load_service_account_credentials.assert_called_once()
        mock_manager.validate_credentials.assert_called_once()
    
    @patch('auth.gcp_auth.get_auth_manager')
    def test_initialize_gcp_auth_load_error(self, mock_get_manager):
        """Test GCP authentication initialization when loading fails"""
        # Setup mocks
        mock_manager = Mock(spec=GCPAuthManager)
        mock_manager.load_service_account_credentials.side_effect = GCPAuthenticationError("Load failed")
        mock_get_manager.return_value = mock_manager
        
        # Test the function
        with pytest.raises(GCPAuthenticationError, match="Load failed"):
            initialize_gcp_auth()
    
    @patch('auth.gcp_auth.get_auth_manager')
    def test_initialize_gcp_auth_validation_error(self, mock_get_manager):
        """Test GCP authentication initialization when validation fails"""
        # Setup mocks
        mock_manager = Mock(spec=GCPAuthManager)
        mock_manager.validate_credentials.side_effect = GCPAuthenticationError("Validation failed")
        mock_get_manager.return_value = mock_manager
        
        # Test the function
        with pytest.raises(GCPAuthenticationError, match="Validation failed"):
            initialize_gcp_auth()


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a GCPAuthManager instance for testing"""
        return GCPAuthManager()
    
    @patch('auth.gcp_auth.st')
    def test_malformed_json_in_secrets(self, mock_st, auth_manager):
        """Test handling of malformed JSON in secrets"""
        # This test simulates a scenario where secrets contain invalid data
        # that would cause JSON parsing issues
        mock_st.secrets = {"gcp_service_account": "not a dict"}
        
        # The actual error will depend on how Streamlit handles this,
        # but our code should catch and re-raise as GCPAuthenticationError
        with pytest.raises(GCPAuthenticationError):
            auth_manager.load_service_account_credentials()
    
    @patch('auth.gcp_auth.st')
    def test_key_error_handling(self, mock_st, auth_manager):
        """Test handling of KeyError during credential loading"""
        # Setup mocks to simulate a KeyError
        mock_secrets = MagicMock()
        mock_secrets.__contains__.return_value = True
        mock_secrets.__getitem__.side_effect = KeyError("test_key")
        mock_st.secrets = mock_secrets
        
        # Test the method
        with pytest.raises(GCPAuthenticationError, match="Missing key in service account credentials"):
            auth_manager.load_service_account_credentials()
    
    def test_custom_exception_inheritance(self):
        """Test that GCPAuthenticationError is properly defined"""
        error = GCPAuthenticationError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestCredentialScopes:
    """Test credential scope handling"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a GCPAuthManager instance for testing"""
        return GCPAuthManager()
    
    @patch('auth.gcp_auth.Request')
    def test_validate_credentials_missing_scopes_warning(self, mock_request, auth_manager):
        """Test validation when credentials don't have required scopes"""
        # Setup mocks
        mock_credentials = Mock(spec=service_account.Credentials)
        mock_credentials.valid = True
        mock_credentials.has_scopes.return_value = False  # Missing required scopes
        auth_manager._credentials = mock_credentials
        
        # Test the method - should still return True but log a warning
        result = auth_manager.validate_credentials()
        
        # Verify results
        assert result is True  # Still valid, just missing scopes
        mock_credentials.has_scopes.assert_called_once_with(['https://www.googleapis.com/auth/cloud-platform'])


if __name__ == "__main__":
    pytest.main([__file__])