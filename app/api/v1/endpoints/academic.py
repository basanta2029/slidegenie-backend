"""
Academic domain validation endpoints.
"""
from typing import Any, List

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth.academic_validator import AcademicEmailValidator

router = APIRouter()


@router.get("/validate-domain", response_model=dict)
async def validate_academic_domain(
    domain: str = Query(..., description="Email domain to validate"),
) -> Any:
    """
    Validate if a domain is academic and get institution information.
    
    - Checks against known academic domains
    - Returns institution name if recognized
    - Useful for registration form validation
    """
    validator = AcademicEmailValidator()
    
    institution = await validator.validate_domain(domain)
    is_academic = institution is not None
    
    return {
        "domain": domain,
        "is_academic": is_academic,
        "institution": institution,
        "requires_verification": is_academic,  # Academic emails require verification
    }


@router.get("/suggest-domains", response_model=List[str])
async def suggest_academic_domains(
    query: str = Query(..., min_length=2, description="Partial domain to search"),
) -> Any:
    """
    Get academic domain suggestions for autocomplete.
    
    - Searches known academic domains
    - Returns up to 10 matching domains
    - Useful for email input autocomplete
    """
    validator = AcademicEmailValidator()
    
    suggestions = await validator.get_domain_suggestions(query)
    
    return suggestions


@router.get("/check-email", response_model=dict)
async def check_academic_email(
    email: str = Query(..., description="Email address to check"),
) -> Any:
    """
    Quick check if email is from an academic institution.
    
    - Validates email format
    - Checks if domain is academic
    - Returns institution info if available
    """
    validator = AcademicEmailValidator()
    
    try:
        # Extract domain from email
        domain = email.split('@')[1].lower()
        
        # Check if academic
        is_academic = validator.is_likely_academic(email)
        institution = None
        
        if is_academic:
            institution = await validator.validate_domain(domain)
        
        return {
            "email": email,
            "domain": domain,
            "is_academic": is_academic,
            "institution": institution,
            "requires_verification": is_academic,
        }
        
    except (IndexError, AttributeError):
        return {
            "email": email,
            "domain": None,
            "is_academic": False,
            "institution": None,
            "requires_verification": False,
            "error": "Invalid email format",
        }