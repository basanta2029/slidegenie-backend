"""
OAuth Provider Base Interface

Defines the abstract interface that all OAuth providers must implement.
"""
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class OAuthUserInfo(BaseModel):
    """Standard user information returned by OAuth providers."""
    id: str  # Provider-specific user ID
    email: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    picture: Optional[str] = None
    verified_email: bool = False
    locale: Optional[str] = None
    
    # Academic-specific fields
    domain: Optional[str] = None
    is_edu_email: bool = False
    institution: Optional[str] = None
    hd: Optional[str] = None  # Google's hosted domain
    
    # Provider metadata
    provider: str
    raw_data: Dict[str, Any] = {}


class OAuthTokens(BaseModel):
    """OAuth token information."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None  # For OpenID Connect


class OAuthError(Exception):
    """OAuth-specific error."""
    def __init__(self, error: str, description: Optional[str] = None):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}" if description else error)


class OAuthProviderInterface(ABC):
    """Abstract base class for OAuth providers."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.provider_name = self.__class__.__name__.lower().replace("provider", "")
    
    @property
    @abstractmethod
    def authorization_base_url(self) -> str:
        """Base URL for OAuth authorization."""
        pass
    
    @property
    @abstractmethod
    def token_url(self) -> str:
        """URL for token exchange."""
        pass
    
    @property
    @abstractmethod
    def user_info_url(self) -> str:
        """URL for fetching user information."""
        pass
    
    @property
    @abstractmethod
    def scope(self) -> str:
        """Required OAuth scopes."""
        pass
    
    def generate_authorization_url(self, state: str, **kwargs) -> str:
        """
        Generate OAuth authorization URL.
        
        Args:
            state: CSRF protection state parameter
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_type": "code",
            "state": state,
            **kwargs
        }
        
        # Add provider-specific parameters
        params.update(self._get_additional_auth_params())
        
        url = f"{self.authorization_base_url}?{urlencode(params)}"
        logger.info(
            "oauth_authorization_url_generated",
            provider=self.provider_name,
            state=state[:8],  # Only log first 8 chars for security
        )
        return url
    
    @abstractmethod
    async def exchange_code_for_tokens(self, code: str, state: str) -> OAuthTokens:
        """
        Exchange authorization code for access tokens.
        
        Args:
            code: Authorization code from OAuth callback
            state: State parameter for CSRF protection
        
        Returns:
            OAuth tokens
        
        Raises:
            OAuthError: If token exchange fails
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Fetch user information using access token.
        
        Args:
            access_token: OAuth access token
        
        Returns:
            User information
        
        Raises:
            OAuthError: If user info fetch fails
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: OAuth refresh token
        
        Returns:
            New OAuth tokens
        
        Raises:
            OAuthError: If token refresh fails
        """
        pass
    
    def _get_additional_auth_params(self) -> Dict[str, str]:
        """
        Get provider-specific authorization parameters.
        Override in subclasses if needed.
        
        Returns:
            Additional parameters for authorization URL
        """
        return {}
    
    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address."""
        if "@" in email:
            return email.split("@")[1].lower()
        return None
    
    def _is_edu_email(self, email: str) -> bool:
        """Check if email is from an educational institution."""
        domain = self._extract_domain_from_email(email)
        if not domain:
            return False
        
        # Check for .edu domains
        if domain.endswith(".edu"):
            return True
        
        # Check for known academic domains
        academic_domains = {
            # US Universities
            "mit.edu", "harvard.edu", "stanford.edu", "berkeley.edu",
            "caltech.edu", "cmu.edu", "princeton.edu", "yale.edu",
            "columbia.edu", "uchicago.edu", "upenn.edu", "cornell.edu",
            
            # International Universities
            "ox.ac.uk", "cam.ac.uk", "imperial.ac.uk", "ucl.ac.uk",
            "eth.ch", "epfl.ch", "u-tokyo.ac.jp", "kyoto-u.ac.jp",
            "tsinghua.edu.cn", "pku.edu.cn", "nus.edu.sg", "ntu.edu.sg",
            "uoft.ca", "mcgill.ca", "ubc.ca", "utoronto.ca",
            "sydney.edu.au", "anu.edu.au", "unimelb.edu.au",
            
            # Research Institutions
            "nasa.gov", "nih.gov", "cern.ch", "riken.jp",
            "cnrs.fr", "mpg.de", "csic.es", "inria.fr",
        }
        
        return domain in academic_domains
    
    def _extract_institution_from_domain(self, domain: str) -> Optional[str]:
        """Extract institution name from email domain."""
        if not domain:
            return None
        
        # Remove common suffixes to get base name
        base_domain = domain.replace(".edu", "").replace(".ac.uk", "")
        base_domain = base_domain.replace(".edu.au", "").replace(".edu.ca", "")
        
        # Common institution mappings
        institution_map = {
            "mit": "Massachusetts Institute of Technology",
            "harvard": "Harvard University",
            "stanford": "Stanford University",
            "berkeley": "University of California, Berkeley",
            "caltech": "California Institute of Technology",
            "cmu": "Carnegie Mellon University",
            "princeton": "Princeton University",
            "yale": "Yale University",
            "columbia": "Columbia University",
            "uchicago": "University of Chicago",
            "upenn": "University of Pennsylvania",
            "cornell": "Cornell University",
            "ox": "Oxford University",
            "cam": "Cambridge University",
            "imperial": "Imperial College London",
            "ucl": "University College London",
            "eth": "ETH Zurich",
            "epfl": "EPFL",
            "u-tokyo": "University of Tokyo",
            "kyoto-u": "Kyoto University",
            "tsinghua": "Tsinghua University",
            "pku": "Peking University",
            "nus": "National University of Singapore",
            "ntu": "Nanyang Technological University",
            "uoft": "University of Toronto",
            "utoronto": "University of Toronto",
            "mcgill": "McGill University",
            "ubc": "University of British Columbia",
            "sydney": "University of Sydney",
            "anu": "Australian National University",
            "unimelb": "University of Melbourne",
        }
        
        return institution_map.get(base_domain.split(".")[0])
    
    async def validate_user_info(self, user_info: OAuthUserInfo) -> bool:
        """
        Validate user information for academic requirements.
        
        Args:
            user_info: User information from OAuth provider
        
        Returns:
            True if user meets academic requirements
        """
        # Check if email is verified
        if not user_info.verified_email:
            logger.warning(
                "oauth_unverified_email",
                provider=self.provider_name,
                email=user_info.email
            )
            return False
        
        # For academic focus, prefer .edu emails but don't strictly require them
        # in case some institutions use other domains
        if not user_info.is_edu_email:
            logger.info(
                "oauth_non_edu_email",
                provider=self.provider_name,
                email=user_info.email,
                domain=user_info.domain
            )
        
        return True