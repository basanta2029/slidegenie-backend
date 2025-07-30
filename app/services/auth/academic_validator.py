"""
Academic Email Validator for SlideGenie.

Validates academic email domains and provides institution information.
"""
import re
from typing import Dict, List, Optional, Set
import asyncio
import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class AcademicEmailValidator:
    """Service for validating academic email domains."""
    
    def __init__(self):
        # Common academic domain patterns
        self.edu_tlds = {'.edu', '.ac.uk', '.edu.au', '.edu.cn', '.edu.in', '.ac.jp', '.edu.br', '.edu.mx'}
        
        # Well-known academic domains (partial list)
        self.known_domains: Dict[str, str] = {
            # US Universities
            'harvard.edu': 'Harvard University',
            'mit.edu': 'Massachusetts Institute of Technology',
            'stanford.edu': 'Stanford University',
            'berkeley.edu': 'University of California, Berkeley',
            'yale.edu': 'Yale University',
            'princeton.edu': 'Princeton University',
            'columbia.edu': 'Columbia University',
            'cornell.edu': 'Cornell University',
            'upenn.edu': 'University of Pennsylvania',
            'caltech.edu': 'California Institute of Technology',
            'uchicago.edu': 'University of Chicago',
            'northwestern.edu': 'Northwestern University',
            'duke.edu': 'Duke University',
            'jhu.edu': 'Johns Hopkins University',
            'nyu.edu': 'New York University',
            'gatech.edu': 'Georgia Institute of Technology',
            'cmu.edu': 'Carnegie Mellon University',
            'umich.edu': 'University of Michigan',
            'usc.edu': 'University of Southern California',
            'brown.edu': 'Brown University',
            'vanderbilt.edu': 'Vanderbilt University',
            'rice.edu': 'Rice University',
            'ucla.edu': 'University of California, Los Angeles',
            'wustl.edu': 'Washington University in St. Louis',
            'umn.edu': 'University of Minnesota',
            'wisc.edu': 'University of Wisconsin-Madison',
            'uw.edu': 'University of Washington',
            'uiuc.edu': 'University of Illinois Urbana-Champaign',
            'utexas.edu': 'University of Texas at Austin',
            'virginia.edu': 'University of Virginia',
            'unc.edu': 'University of North Carolina at Chapel Hill',
            'umd.edu': 'University of Maryland',
            'bu.edu': 'Boston University',
            'purdue.edu': 'Purdue University',
            'osu.edu': 'Ohio State University',
            'psu.edu': 'Pennsylvania State University',
            'rutgers.edu': 'Rutgers University',
            'indiana.edu': 'Indiana University',
            'msu.edu': 'Michigan State University',
            'ufl.edu': 'University of Florida',
            'ucsd.edu': 'University of California, San Diego',
            'ucdavis.edu': 'University of California, Davis',
            'uci.edu': 'University of California, Irvine',
            'georgetown.edu': 'Georgetown University',
            'tufts.edu': 'Tufts University',
            'dartmouth.edu': 'Dartmouth College',
            'northeastern.edu': 'Northeastern University',
            'emory.edu': 'Emory University',
            'gwu.edu': 'George Washington University',
            
            # UK Universities
            'ox.ac.uk': 'University of Oxford',
            'cam.ac.uk': 'University of Cambridge',
            'imperial.ac.uk': 'Imperial College London',
            'lse.ac.uk': 'London School of Economics',
            'ucl.ac.uk': 'University College London',
            'ed.ac.uk': 'University of Edinburgh',
            'manchester.ac.uk': 'University of Manchester',
            'kcl.ac.uk': "King's College London",
            'warwick.ac.uk': 'University of Warwick',
            'bristol.ac.uk': 'University of Bristol',
            'glasgow.ac.uk': 'University of Glasgow',
            'southampton.ac.uk': 'University of Southampton',
            'durham.ac.uk': 'Durham University',
            'birmingham.ac.uk': 'University of Birmingham',
            'st-andrews.ac.uk': 'University of St Andrews',
            'leeds.ac.uk': 'University of Leeds',
            'sheffield.ac.uk': 'University of Sheffield',
            'nottingham.ac.uk': 'University of Nottingham',
            'york.ac.uk': 'University of York',
            'qmul.ac.uk': 'Queen Mary University of London',
            
            # Canadian Universities
            'utoronto.ca': 'University of Toronto',
            'ubc.ca': 'University of British Columbia',
            'mcgill.ca': 'McGill University',
            'ualberta.ca': 'University of Alberta',
            'uwaterloo.ca': 'University of Waterloo',
            'uwo.ca': 'Western University',
            'queensu.ca': "Queen's University",
            'umontreal.ca': 'Université de Montréal',
            'ucalgary.ca': 'University of Calgary',
            'sfu.ca': 'Simon Fraser University',
            
            # Australian Universities
            'unimelb.edu.au': 'University of Melbourne',
            'sydney.edu.au': 'University of Sydney',
            'anu.edu.au': 'Australian National University',
            'unsw.edu.au': 'University of New South Wales',
            'uq.edu.au': 'University of Queensland',
            'monash.edu': 'Monash University',
            'uwa.edu.au': 'University of Western Australia',
            'adelaide.edu.au': 'University of Adelaide',
            
            # European Universities
            'ethz.ch': 'ETH Zurich',
            'epfl.ch': 'École Polytechnique Fédérale de Lausanne',
            'uzh.ch': 'University of Zurich',
            'uni-heidelberg.de': 'Heidelberg University',
            'tum.de': 'Technical University of Munich',
            'lmu.de': 'Ludwig Maximilian University of Munich',
            'hu-berlin.de': 'Humboldt University of Berlin',
            'fu-berlin.de': 'Free University of Berlin',
            'sorbonne-universite.fr': 'Sorbonne University',
            'ens.fr': 'École Normale Supérieure',
            'polytechnique.edu': 'École Polytechnique',
            'uva.nl': 'University of Amsterdam',
            'vu.nl': 'Vrije Universiteit Amsterdam',
            'tudelft.nl': 'Delft University of Technology',
            'rug.nl': 'University of Groningen',
            'kuleuven.be': 'KU Leuven',
            'ugent.be': 'Ghent University',
            'uib.no': 'University of Bergen',
            'ntnu.no': 'Norwegian University of Science and Technology',
            'ku.dk': 'University of Copenhagen',
            'au.dk': 'Aarhus University',
            'su.se': 'Stockholm University',
            'uu.se': 'Uppsala University',
            'helsinki.fi': 'University of Helsinki',
            'aalto.fi': 'Aalto University',
            
            # Asian Universities
            'u-tokyo.ac.jp': 'University of Tokyo',
            'kyoto-u.ac.jp': 'Kyoto University',
            'tohoku.ac.jp': 'Tohoku University',
            'osaka-u.ac.jp': 'Osaka University',
            'nus.edu.sg': 'National University of Singapore',
            'ntu.edu.sg': 'Nanyang Technological University',
            'hku.hk': 'University of Hong Kong',
            'cuhk.edu.hk': 'Chinese University of Hong Kong',
            'tsinghua.edu.cn': 'Tsinghua University',
            'pku.edu.cn': 'Peking University',
            'fudan.edu.cn': 'Fudan University',
            'sjtu.edu.cn': 'Shanghai Jiao Tong University',
            'kaist.ac.kr': 'Korea Advanced Institute of Science and Technology',
            'snu.ac.kr': 'Seoul National University',
            'iitb.ac.in': 'Indian Institute of Technology Bombay',
            'iitd.ac.in': 'Indian Institute of Technology Delhi',
            'iisc.ac.in': 'Indian Institute of Science',
            
            # Research Institutions
            'cern.ch': 'CERN',
            'mpg.de': 'Max Planck Society',
            'cnrs.fr': 'French National Centre for Scientific Research',
            'csic.es': 'Spanish National Research Council',
            'infn.it': 'National Institute for Nuclear Physics',
        }
        
        # Additional patterns for academic domains
        self.academic_patterns = [
            r'.*\.edu$',
            r'.*\.edu\.[a-z]{2}$',
            r'.*\.ac\.[a-z]{2}$',
            r'.*\.uni-.*\.[a-z]{2}$',
            r'.*\.univ-.*\.[a-z]{2}$',
        ]
    
    async def validate_domain(self, domain: str) -> Optional[str]:
        """
        Validate if domain is academic and return institution name.
        
        Args:
            domain: Email domain to validate
            
        Returns:
            Institution name if academic domain, None otherwise
        """
        domain = domain.lower()
        
        # Check known domains first
        if domain in self.known_domains:
            return self.known_domains[domain]
        
        # Check if it's an educational TLD
        for tld in self.edu_tlds:
            if domain.endswith(tld):
                # Try to derive institution name from domain
                institution_name = self._derive_institution_name(domain)
                return institution_name
        
        # Check patterns
        for pattern in self.academic_patterns:
            if re.match(pattern, domain):
                institution_name = self._derive_institution_name(domain)
                return institution_name
        
        # If not recognized as academic
        return None
    
    def _derive_institution_name(self, domain: str) -> str:
        """
        Derive institution name from domain.
        
        Args:
            domain: Academic domain
            
        Returns:
            Derived institution name
        """
        # Remove common TLDs
        name = domain
        for tld in ['.edu', '.ac.uk', '.edu.au', '.edu.cn', '.ac.jp', '.edu.br', '.edu.mx', '.ac.in']:
            if name.endswith(tld):
                name = name[:-len(tld)]
                break
        
        # Handle subdomains (e.g., mail.harvard.edu -> harvard)
        parts = name.split('.')
        if len(parts) > 1:
            # Try to find the main institution part
            for part in reversed(parts):
                if len(part) > 3 and part not in ['mail', 'email', 'smtp', 'www']:
                    name = part
                    break
        
        # Convert to title case and expand common abbreviations
        name = name.replace('-', ' ').replace('_', ' ')
        
        # Expand common abbreviations
        abbreviations = {
            'uni': 'University',
            'univ': 'University',
            'tech': 'Technology',
            'inst': 'Institute',
            'coll': 'College',
            'acad': 'Academy',
            'poly': 'Polytechnic',
        }
        
        words = name.split()
        expanded_words = []
        for word in words:
            lower_word = word.lower()
            if lower_word in abbreviations:
                expanded_words.append(abbreviations[lower_word])
            else:
                expanded_words.append(word.title())
        
        institution_name = ' '.join(expanded_words)
        
        # Add "University" if not present and seems appropriate
        if 'university' not in institution_name.lower() and 'college' not in institution_name.lower():
            if not any(term in institution_name.lower() for term in ['institute', 'academy', 'school', 'center']):
                institution_name = f"{institution_name} University"
        
        return institution_name
    
    async def get_domain_suggestions(self, partial_domain: str) -> List[str]:
        """
        Get domain suggestions for autocomplete.
        
        Args:
            partial_domain: Partial domain string
            
        Returns:
            List of matching academic domains
        """
        partial = partial_domain.lower()
        suggestions = []
        
        # Search through known domains
        for domain, institution in self.known_domains.items():
            if partial in domain or partial in institution.lower():
                suggestions.append(domain)
        
        # Sort by relevance (domains starting with partial first)
        suggestions.sort(key=lambda d: (not d.startswith(partial), d))
        
        return suggestions[:10]  # Return top 10 matches
    
    def is_likely_academic(self, email: str) -> bool:
        """
        Quick check if email is likely from an academic institution.
        
        Args:
            email: Email address to check
            
        Returns:
            True if likely academic, False otherwise
        """
        try:
            domain = email.split('@')[1].lower()
            
            # Quick checks
            if domain in self.known_domains:
                return True
            
            for tld in self.edu_tlds:
                if domain.endswith(tld):
                    return True
            
            return False
            
        except IndexError:
            return False
    
    async def validate_institution_name(self, institution: str) -> bool:
        """
        Validate if institution name appears legitimate.
        
        Args:
            institution: Institution name to validate
            
        Returns:
            True if valid institution name
        """
        if not institution or len(institution) < 3:
            return False
        
        # Check against known institution names
        known_names = set(self.known_domains.values())
        if institution in known_names:
            return True
        
        # Check for common academic keywords
        academic_keywords = [
            'university', 'college', 'institute', 'academy',
            'school', 'polytechnic', 'research', 'laboratory'
        ]
        
        institution_lower = institution.lower()
        return any(keyword in institution_lower for keyword in academic_keywords)