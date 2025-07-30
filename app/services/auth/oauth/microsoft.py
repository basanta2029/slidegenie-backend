"""
Microsoft OAuth Provider Implementation

Handles Microsoft OAuth integration with focus on Microsoft 365 Education accounts.
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


class MicrosoftOAuthProvider(OAuthProviderInterface):
    """Microsoft OAuth provider with academic focus."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, tenant: str = "common"):
        """
        Initialize Microsoft OAuth provider.
        
        Args:
            client_id: Microsoft application client ID
            client_secret: Microsoft application client secret
            redirect_uri: OAuth redirect URI
            tenant: Azure AD tenant ID or 'common' for multi-tenant
        """
        super().__init__(client_id, client_secret, redirect_uri)
        self.tenant = tenant
    
    @property
    def authorization_base_url(self) -> str:
        """Microsoft OAuth authorization endpoint."""
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/authorize"
    
    @property
    def token_url(self) -> str:
        """Microsoft OAuth token endpoint."""
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
    
    @property
    def user_info_url(self) -> str:
        """Microsoft Graph user endpoint."""
        return "https://graph.microsoft.com/v1.0/me"
    
    @property
    def scope(self) -> str:
        """Required Microsoft OAuth scopes."""
        # Request profile, email, and education-related information
        return "openid profile email User.Read EduRoster.ReadBasic"
    
    def _get_additional_auth_params(self) -> Dict[str, str]:
        """Get Microsoft-specific authorization parameters."""
        return {
            "response_mode": "query",  # Use query parameters for response
            "prompt": "consent",  # Force consent to ensure refresh token
        }
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> OAuthTokens:
        """Exchange authorization code for Microsoft OAuth tokens."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
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
                            "microsoft_token_exchange_failed",
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
                            "microsoft_token_exchange_error",
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
                        "microsoft_tokens_obtained",
                        has_refresh_token=bool(tokens.refresh_token),
                        expires_in=tokens.expires_in,
                        scope=tokens.scope
                    )
                    
                    return tokens
        
        except aiohttp.ClientError as e:
            logger.error("microsoft_token_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Microsoft: {str(e)}")
        except Exception as e:
            logger.error("microsoft_token_exchange_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user information from Microsoft Graph."""
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
                            "microsoft_userinfo_failed",
                            status=response.status,
                            error=error_text
                        )
                        raise OAuthError("userinfo_failed", error_text)
                    
                    user_data = await response.json()
                    
                    # Extract user information
                    email = user_data.get("mail") or user_data.get("userPrincipalName", "")
                    domain = self._extract_domain_from_email(email)
                    is_edu_email = self._is_edu_email(email)
                    institution = self._extract_institution_from_domain(domain) if domain else None
                    
                    # Try to get additional academic info
                    academic_info = await self._get_academic_info(access_token, headers)
                    
                    # Create user info object
                    user_info = OAuthUserInfo(
                        id=user_data["id"],
                        email=email,
                        name=user_data.get("displayName", ""),
                        first_name=user_data.get("givenName"),
                        last_name=user_data.get("surname"),
                        picture=None,  # Microsoft Graph has profile photos but requires separate call
                        verified_email=True,  # Microsoft accounts are generally verified
                        locale=user_data.get("preferredLanguage"),
                        domain=domain,
                        is_edu_email=is_edu_email,
                        institution=institution or academic_info.get("institution"),
                        provider="microsoft",
                        raw_data={**user_data, **academic_info}
                    )
                    
                    logger.info(
                        "microsoft_userinfo_obtained",
                        email=user_info.email,
                        domain=user_info.domain,
                        is_edu=user_info.is_edu_email,
                        institution=user_info.institution,
                        user_type=academic_info.get("userType")
                    )
                    
                    return user_info
        
        except aiohttp.ClientError as e:
            logger.error("microsoft_userinfo_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Microsoft: {str(e)}")
        except KeyError as e:
            logger.error("microsoft_userinfo_invalid_response", missing_field=str(e))
            raise OAuthError("invalid_response", f"Missing required field: {str(e)}")
        except ValidationError as e:
            logger.error("microsoft_userinfo_validation_failed", error=str(e))
            raise OAuthError("validation_error", str(e))
        except Exception as e:
            logger.error("microsoft_userinfo_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def _get_academic_info(self, access_token: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get additional academic information from Microsoft Graph."""
        academic_info = {}
        
        try:
            # Try to get organization information
            async with aiohttp.ClientSession() as session:
                # Get user's organization
                org_url = "https://graph.microsoft.com/v1.0/organization"
                async with session.get(org_url, headers=headers) as response:
                    if response.status == 200:
                        org_data = await response.json()
                        if org_data.get("value") and len(org_data["value"]) > 0:
                            org = org_data["value"][0]
                            academic_info.update({
                                "institution": org.get("displayName"),
                                "organization_type": org.get("businessPhones"),
                                "tenant_type": org.get("tenantType"),
                            })
                
                # Try to get education information if available
                edu_url = "https://graph.microsoft.com/v1.0/me/extensions"
                async with session.get(edu_url, headers=headers) as response:
                    if response.status == 200:
                        ext_data = await response.json()
                        # Look for education-related extensions
                        for extension in ext_data.get("value", []):
                            if "education" in extension.get("id", "").lower():
                                academic_info["education_extension"] = extension
                
                # Get user type (member, guest, etc.)
                user_url = f"{self.user_info_url}?$select=userType,accountEnabled,creationType"
                async with session.get(user_url, headers=headers) as response:
                    if response.status == 200:
                        user_type_data = await response.json()
                        academic_info.update({
                            "userType": user_type_data.get("userType"),
                            "accountEnabled": user_type_data.get("accountEnabled"),
                            "creationType": user_type_data.get("creationType"),
                        })
        
        except Exception as e:
            logger.warning("microsoft_academic_info_failed", error=str(e))
            # Don't fail the whole process if academic info fails
        
        return academic_info
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh Microsoft OAuth access token."""
        refresh_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": self.scope,
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
                            "microsoft_token_refresh_failed",
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
                            "microsoft_token_refresh_error",
                            error=error,
                            description=description
                        )
                        raise OAuthError(error, description)
                    
                    # Create new token object
                    tokens = OAuthTokens(
                        access_token=token_response["access_token"],
                        token_type=token_response.get("token_type", "Bearer"),
                        expires_in=token_response.get("expires_in"),
                        refresh_token=token_response.get("refresh_token", refresh_token),
                        scope=token_response.get("scope"),
                        id_token=token_response.get("id_token"),
                    )
                    
                    logger.info(
                        "microsoft_token_refreshed",
                        expires_in=tokens.expires_in,
                        scope=tokens.scope
                    )
                    
                    return tokens
        
        except aiohttp.ClientError as e:
            logger.error("microsoft_token_refresh_request_failed", error=str(e))
            raise OAuthError("network_error", f"Failed to connect to Microsoft: {str(e)}")
        except Exception as e:
            logger.error("microsoft_token_refresh_unexpected_error", error=str(e))
            raise OAuthError("unexpected_error", str(e))
    
    async def validate_user_info(self, user_info: OAuthUserInfo) -> bool:
        """Validate Microsoft user info for academic requirements."""
        # First run base validation
        if not await super().validate_user_info(user_info):
            return False
        
        # Microsoft-specific validations
        
        # Check if user is from an educational tenant
        user_type = user_info.raw_data.get("userType")
        tenant_type = user_info.raw_data.get("tenant_type")
        
        if tenant_type == "Education":
            logger.info(
                "microsoft_education_tenant",
                email=user_info.email,
                institution=user_info.institution
            )
            return True
        
        # Check if domain is academic
        if user_info.is_edu_email:
            logger.info(
                "microsoft_edu_email_user",
                domain=user_info.domain,
                email=user_info.email
            )
            return True
        
        # For non-edu emails, check if institution is known academic
        if user_info.institution:
            logger.info(
                "microsoft_institutional_user",
                institution=user_info.institution,
                email=user_info.email
            )
            return True
        
        # Allow all Microsoft users but log for review
        logger.info(
            "microsoft_general_user",
            domain=user_info.domain,
            email=user_info.email,
            user_type=user_type
        )
        
        return True
    
    async def get_academic_resources(self, access_token: str) -> Dict[str, Any]:
        """
        Get additional academic resources if user has access.
        This could include OneNote notebooks, Teams classes, etc.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        resources = {
            "provider": "microsoft",
            "academic_services": ["onenote", "teams", "onedrive"],
            "verified_academic": False,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check if user has access to Microsoft Teams for Education
                teams_url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
                async with session.get(teams_url, headers=headers) as response:
                    if response.status == 200:
                        teams_data = await response.json()
                        edu_teams = [
                            team for team in teams_data.get("value", [])
                            if "education" in team.get("description", "").lower()
                            or "class" in team.get("displayName", "").lower()
                        ]
                        resources["education_teams"] = len(edu_teams)
                        if edu_teams:
                            resources["verified_academic"] = True
                
                # Check for OneNote sections (often used in academic settings)
                onenote_url = "https://graph.microsoft.com/v1.0/me/onenote/sections"
                async with session.get(onenote_url, headers=headers) as response:
                    if response.status == 200:
                        onenote_data = await response.json()
                        resources["onenote_sections"] = len(onenote_data.get("value", []))
        
        except Exception as e:
            logger.warning("microsoft_academic_resources_failed", error=str(e))
        
        return resources