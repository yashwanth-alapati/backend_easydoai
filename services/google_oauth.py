# easydo_backend/services/google_oauth.py
import requests
import os
from typing import Dict, Optional, List, Any
from urllib.parse import urlencode
import secrets
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    """Google OAuth2 service for EasyDoAI platform"""
    
    def __init__(self):
        # EasyDoAI's OAuth app credentials (same for all users)
        self.client_id = os.getenv('EASYDOAI_GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('EASYDOAI_GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('EASYDOAI_GOOGLE_REDIRECT_URI')
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required Google OAuth environment variables")
        
        # Scopes for different services
        self.service_scopes = {
            'gmail': [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.send'
            ],
            'google_calendar': [
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        }
        
        # OAuth endpoints
        self.auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.revoke_url = 'https://oauth2.googleapis.com/revoke'
        
        # Temporary state storage (in production, use Redis or database)
        self._state_storage = {}
    
    def get_authorization_url(self, service: str, user_id: str) -> Dict[str, str]:
        """Generate OAuth2 authorization URL for a specific service"""
        if service not in self.service_scopes:
            raise ValueError(f"Unsupported service: {service}")
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        state_data = {
            'user_id': user_id,
            'service': service,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store state temporarily (expires in 10 minutes)
        self._state_storage[state] = state_data
        
        # Clean up old states (simple cleanup, in production use proper TTL)
        self._cleanup_old_states()
        
        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.service_scopes[service]),
            'response_type': 'code',
            'access_type': 'offline',  # To get refresh token
            'prompt': 'consent',  # Force consent to ensure refresh token
            'state': state,
            'include_granted_scopes': 'true'  # Incremental authorization
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        return {
            'authorization_url': auth_url,
            'state': state
        }
    
    def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        # Validate state
        if state not in self._state_storage:
            raise ValueError("Invalid or expired state parameter")
        
        state_data = self._state_storage.pop(state)  # Remove state after use
        
        # Check state expiry (10 minutes)
        state_time = datetime.fromisoformat(state_data['timestamp'])
        if datetime.utcnow() - state_time > timedelta(minutes=10):
            raise ValueError("State parameter expired")
        
        try:
            # Exchange code for tokens
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(
                self.token_url,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise Exception(f"Token exchange failed: {response.text}")
            
            tokens = response.json()
            
            return {
                'tokens': tokens,
                'user_id': state_data['user_id'],
                'service': state_data['service']
            }
            
        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            raise Exception(f"Network error during token exchange: {str(e)}")
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an expired access token"""
        try:
            refresh_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(
                self.token_url,
                data=refresh_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Network error during token refresh: {e}")
            return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token"""
        try:
            response = requests.post(
                self.revoke_url,
                data={'token': token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    def _cleanup_old_states(self):
        """Clean up expired state parameters"""
        current_time = datetime.utcnow()
        expired_states = []
        
        for state, data in self._state_storage.items():
            state_time = datetime.fromisoformat(data['timestamp'])
            if current_time - state_time > timedelta(minutes=10):
                expired_states.append(state)
        
        for state in expired_states:
            del self._state_storage[state]

# Global OAuth service instance
oauth_service = GoogleOAuthService()