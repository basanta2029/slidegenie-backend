"""
Google OAuth Provider Implementation

Handles Google OAuth integration with focus on Google Workspace for Education accounts.
"""
import json
from typing import Any, Dict, Optional

import aiohttp
import structlog
from pydantic import ValidationError

from app.core.config import get_settings
from .base import OAuthError, OAuthProviderInterface, OAuthTokens, OAuthUserInfo

logger = structlog.get_logger(__name__)
settings = get_settings()


class GoogleOAuthProvider(OAuthProviderInterface):
    """Google OAuth provider with academic focus."""
    
    @property
    def authorization_base_url(self) -> str:
        """Google OAuth authorization endpoint."""
        return "https://accounts.google.com/o/oauth2/v2/auth"
    
    @property
    def token_url(self) -> str:
        """Google OAuth token endpoint."""
        return "https://oauth2.googleapis.com/token"
    
    @property
    def user_info_url(self) -> str:
        """Google userinfo endpoint."""
        return "https://www.googleapis.com/oauth2/v2/userinfo"
    
    @property
    def scope(self) -> str:
        """Required Google OAuth scopes."""
        # Request profile, email, and hosted domain information
        return "openid profile email"
    
    def _get_additional_auth_params(self) -> Dict[str, str]:
        """Get Google-specific authorization parameters."""
        return {
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "include_granted_scopes": "true",  # Include previously granted scopes
            # Add hd parameter to prefer .edu domains
            "hd": "*",  # Allow any hosted domain but prefer .edu
        }
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> OAuthTokens:
        """Exchange authorization code for Google OAuth tokens."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "google_token_exchange_failed",
                            status=response.status,
                            error=error_text
                        )
                        raise OAuthError("token_exchange_failed", error_text)
                    
                    token_response = await response.json()
                    
                    # Check for error in response
                    if "error" in token_response:
                        error = token_response["error"]
                        description = token_response.get("error_description")
                        logger.error(
                            "google_token_exchange_error",
                            error=error,
                            description=description
                        )
                        raise OAuthError(error, description)
                    
                    # Create token object
                    tokens = OAuthTokens(
                        access_token=token_response["access_token"],
                        token_type=token_response.get("token_type", "Bearer"),
                        expires_in=token_response.get("expires_in"),
                        refresh_token=token_response.get("refresh_token"),
                        scope=token_response.get("scope"),
                        id_token=token_response.get("id_token"),
                    )
                    
                    logger.info(
                        "google_tokens_obtained",
                        has_refresh_token=bool(tokens.refresh_token),
                        expires_in=tokens.expires_in,
                        scope=tokens.scope
                    )
                    
                    return tokens
        
        except aiohttp.ClientError as e:
            logger.error("google_token_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Google: {str(e)}")
        except Exception as e:
            logger.error("google_token_exchange_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user information from Google."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.user_info_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "google_userinfo_failed",
                            status=response.status,
                            error=error_text
                        )
                        raise OAuthError("userinfo_failed", error_text)
                    
                    user_data = await response.json()
                    
                    # Extract user information
                    email = user_data.get("email", "")
                    domain = self._extract_domain_from_email(email)
                    is_edu_email = self._is_edu_email(email)
                    institution = self._extract_institution_from_domain(domain) if domain else None
                    
                    # Create user info object
                    user_info = OAuthUserInfo(
                        id=user_data["id"],
                        email=email,
                        name=user_data.get("name", ""),
                        first_name=user_data.get("given_name"),
                        last_name=user_data.get("family_name"),
                        picture=user_data.get("picture"),
                        verified_email=user_data.get("verified_email", False),
                        locale=user_data.get("locale"),
                        domain=domain,
                        is_edu_email=is_edu_email,
                        institution=institution,
                        hd=user_data.get("hd"),  # Google Workspace hosted domain
                        provider="google",
                        raw_data=user_data
                    )
                    
                    # If user has a hosted domain, prefer that for institution
                    if user_info.hd and not user_info.institution:
                        user_info.institution = self._extract_institution_from_domain(
                            user_info.hd
                        )
                    
                    logger.info(
                        "google_userinfo_obtained",
                        email=user_info.email,
                        domain=user_info.domain,
                        is_edu=user_info.is_edu_email,
                        has_hd=bool(user_info.hd),
                        institution=user_info.institution,
                        verified=user_info.verified_email
                    )
                    
                    return user_info
        
        except aiohttp.ClientError as e:
            logger.error("google_userinfo_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Google: {str(e)}")
        except KeyError as e:
            logger.error("google_userinfo_invalid_response", missing_field=str(e))
            raise OAuthError("invalid_response", f"Missing required field: {str(e)}")
        except ValidationError as e:
            logger.error("google_userinfo_validation_failed", error=str(e))
            raise OAuthError("validation_error", str(e))
        except Exception as e:
            logger.error("google_userinfo_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh Google OAuth access token."""
        refresh_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    data=refresh_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "google_token_refresh_failed",
                            status=response.status,
                            error=error_text
                        )
                        raise OAuthError("token_refresh_failed", error_text)
                    
                    token_response = await response.json()
                    
                    # Check for error in response
                    if "error" in token_response:
                        error = token_response["error"]
                        description = token_response.get("error_description")
                        logger.error(
                            "google_token_refresh_error",
                            error=error,
                            description=description
                        )
                        raise OAuthError(error, description)
                    
                    # Create new token object
                    tokens = OAuthTokens(
                        access_token=token_response["access_token"],
                        token_type=token_response.get("token_type", "Bearer"),
                        expires_in=token_response.get("expires_in"),
                        refresh_token=refresh_token,  # Reuse existing refresh token
                        scope=token_response.get("scope"),
                        id_token=token_response.get("id_token"),
                    )
                    
                    logger.info(
                        "google_token_refreshed",
                        expires_in=tokens.expires_in,
                        scope=tokens.scope
                    )
                    
                    return tokens
        
        except aiohttp.ClientError as e:
            logger.error("google_token_refresh_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Google: {str(e)}")
        except Exception as e:
            logger.error("google_token_refresh_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def validate_user_info(self, user_info: OAuthUserInfo) -> bool:
        """Validate Google user info for academic requirements."""
        # First run base validation
        if not await super().validate_user_info(user_info):
            return False
        
        # Google-specific validations
        
        # Prefer users with Google Workspace for Education (hosted domain)
        if user_info.hd:
            logger.info(
                "google_workspace_user",
                domain=user_info.hd,
                email=user_info.email
            )
            # G Suite for Education users are preferred
            return True
        
        # Check if domain is academic even without hosted domain
        if user_info.is_edu_email:
            logger.info(
                "google_edu_email_user",
                domain=user_info.domain,
                email=user_info.email
            )
            return True
        
        # For non-edu emails, we can still allow but with logging
        logger.info(
            "google_non_edu_user",
            domain=user_info.domain,
            email=user_info.email
        )
        
        return True
    
    async def get_academic_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get additional academic information if available.
        This could be extended to use Google Scholar API or other services.
        """
        # For now, return basic info
        # Could be extended to fetch Google Scholar profile, etc.
        return {
            "provider": "google",
            "academic_services": ["google_scholar", "google_workspace"],
            "verified_academic": False,  # Would need additional verification
        }