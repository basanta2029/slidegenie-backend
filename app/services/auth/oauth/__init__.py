"""
OAuth integration framework for SlideGenie authentication.

This module provides OAuth2 integration with academic providers including
Google OAuth and Microsoft Academic login.
"""

from .base import (
    OAuthError,
    OAuthProviderInterface,
    OAuthTokens,
    OAuthUserInfo,
)
from .google import GoogleOAuthProvider
from .microsoft import MicrosoftOAuthProvider
from .state_manager import (
    OAuthProvider,
    OAuthStateData,
    OAuthStateManager,
    oauth_state_manager,
)

__all__ = [
    # Base classes and types
    "OAuthError",
    "OAuthProviderInterface",
    "OAuthTokens",
    "OAuthUserInfo",
    
    # Providers
    "GoogleOAuthProvider",
    "MicrosoftOAuthProvider",
    
    # State management
    "OAuthProvider",
    "OAuthStateData",
    "OAuthStateManager",
    "oauth_state_manager",
]