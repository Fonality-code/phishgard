"""
Link Analyzer Service

This service provides comprehensive analysis of URLs to detect potential phishing attempts.
It includes multiple detection methods and provides detailed security assessments.
"""
import re
import urllib.parse
import requests
import ssl
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class LinkAnalyzerService:
    """Service for analyzing URLs to detect potential phishing attempts"""

    def __init__(self):
        self.suspicious_domains = [
            # Common phishing domain patterns
            'bit.ly', 'tinyurl.com', 'short.link', 't.co',
            'goo.gl', 'ow.ly', 'tiny.cc', 'is.gd'
        ]

        self.legitimate_domains = [
            'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
            'facebook.com', 'twitter.com', 'linkedin.com', 'github.com',
            'stackoverflow.com', 'wikipedia.org', 'mozilla.org'
        ]

        self.phishing_keywords = [
            'verify', 'suspend', 'urgent', 'immediate', 'confirm',
            'update', 'secure', 'account', 'login', 'signin',
            'bank', 'paypal', 'amazon', 'microsoft', 'apple',
            'security', 'alert', 'warning', 'expired', 'limited'
        ]

    def analyze_url(self, url: str, user_context: Optional[str] = None,
                   user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive URL analysis for phishing detection

        Args:
            url: The URL to analyze
            user_context: Additional context provided by the user
            user_id: ID of the user performing the analysis

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Normalize and validate URL
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                return self._create_error_result("Invalid URL format")

            # Perform multiple analysis checks
            analysis_results = {
                'url': normalized_url,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'user_context': user_context,
                'risk_score': 0,
                'is_phishing': False,
                'confidence_level': 'Low',
                'threats_detected': [],
                'recommendations': [],
                'technical_details': {}
            }

            # URL structure analysis
            structure_analysis = self._analyze_url_structure(normalized_url)
            analysis_results['technical_details']['structure'] = structure_analysis
            analysis_results['risk_score'] += structure_analysis.get('risk_score', 0)

            # Domain analysis
            domain_analysis = self._analyze_domain(normalized_url)
            analysis_results['technical_details']['domain'] = domain_analysis
            analysis_results['risk_score'] += domain_analysis.get('risk_score', 0)

            # Content analysis (if accessible)
            content_analysis = self._analyze_content(normalized_url)
            analysis_results['technical_details']['content'] = content_analysis
            analysis_results['risk_score'] += content_analysis.get('risk_score', 0)

            # SSL/Security analysis
            security_analysis = self._analyze_security(normalized_url)
            analysis_results['technical_details']['security'] = security_analysis
            analysis_results['risk_score'] += security_analysis.get('risk_score', 0)

            # Determine final risk assessment
            analysis_results = self._calculate_final_assessment(analysis_results)

            # Log analysis for security tracking
            if user_id:
                logger.info(f"Link analysis performed by user {user_id}: {url} - Risk Score: {analysis_results['risk_score']}")

            return analysis_results

        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {str(e)}")
            return self._create_error_result(f"Analysis failed: {str(e)}")

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize and validate URL"""
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # Parse and validate
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc:
                return None

            return url.lower()
        except Exception:
            return None

    def _analyze_url_structure(self, url: str) -> Dict[str, Any]:
        """Analyze URL structure for suspicious patterns"""
        analysis = {
            'suspicious_patterns': [],
            'risk_score': 0,
            'details': {}
        }

        try:
            parsed = urllib.parse.urlparse(url)

            # Check for suspicious URL patterns
            if len(parsed.netloc) > 50:
                analysis['suspicious_patterns'].append('Unusually long domain name')
                analysis['risk_score'] += 15

            # Check for multiple subdomains
            subdomain_count = len(parsed.netloc.split('.')) - 2
            if subdomain_count > 2:
                analysis['suspicious_patterns'].append(f'Multiple subdomains ({subdomain_count})')
                analysis['risk_score'] += 10

            # Check for suspicious characters
            if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', parsed.netloc):
                analysis['suspicious_patterns'].append('IP address instead of domain name')
                analysis['risk_score'] += 25

            # Check for URL shorteners
            domain = parsed.netloc.lower()
            if any(shortener in domain for shortener in self.suspicious_domains):
                analysis['suspicious_patterns'].append('URL shortening service detected')
                analysis['risk_score'] += 20

            # Check for suspicious keywords in URL
            url_text = url.lower()
            found_keywords = [kw for kw in self.phishing_keywords if kw in url_text]
            if found_keywords:
                analysis['suspicious_patterns'].append(f'Suspicious keywords: {", ".join(found_keywords)}')
                analysis['risk_score'] += len(found_keywords) * 5

            # Check for homograph attacks (unicode lookalikes)
            if any(ord(char) > 127 for char in parsed.netloc):
                analysis['suspicious_patterns'].append('International characters in domain (possible homograph attack)')
                analysis['risk_score'] += 30

            analysis['details'] = {
                'domain': parsed.netloc,
                'path': parsed.path,
                'query_params': len(urllib.parse.parse_qs(parsed.query)),
                'has_fragment': bool(parsed.fragment)
            }

        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def _analyze_domain(self, url: str) -> Dict[str, Any]:
        """Analyze domain reputation and characteristics"""
        analysis = {
            'reputation': 'Unknown',
            'risk_score': 0,
            'details': {},
            'flags': []
        }

        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()

            # Check against known legitimate domains
            if any(legit in domain for legit in self.legitimate_domains):
                analysis['reputation'] = 'Legitimate'
                analysis['risk_score'] = 0
                analysis['flags'].append('Known legitimate domain')

            # Check for domain spoofing attempts
            for legit_domain in self.legitimate_domains:
                if self._is_domain_similar(domain, legit_domain):
                    analysis['flags'].append(f'Possible spoofing of {legit_domain}')
                    analysis['risk_score'] += 35

            # Check domain age (simplified - in production, use WHOIS data)
            analysis['details']['domain'] = domain
            analysis['details']['tld'] = domain.split('.')[-1] if '.' in domain else 'unknown'

            # Suspicious TLD check
            suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.click', '.download']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                analysis['flags'].append('Suspicious top-level domain')
                analysis['risk_score'] += 20

        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def _analyze_content(self, url: str) -> Dict[str, Any]:
        """Analyze webpage content for phishing indicators"""
        analysis = {
            'accessible': False,
            'risk_score': 0,
            'content_flags': [],
            'details': {}
        }

        try:
            # Try to fetch the webpage (with timeout and safety measures)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 PhishGuard Security Scanner'
            }

            response = requests.get(url, headers=headers, timeout=10, verify=False,
                                  allow_redirects=True, stream=True)

            if response.status_code == 200:
                analysis['accessible'] = True

                # Get only first 50KB to avoid memory issues
                content = response.content[:50000].decode('utf-8', errors='ignore')

                # Check for suspicious content patterns
                content_lower = content.lower()

                # Check for login forms
                if re.search(r'<input[^>]*type=["\']password["\']', content, re.IGNORECASE):
                    analysis['content_flags'].append('Password input field detected')
                    analysis['risk_score'] += 15

                # Check for urgent language
                urgent_phrases = ['act now', 'urgent', 'immediate action', 'verify now', 'suspend']
                found_urgent = [phrase for phrase in urgent_phrases if phrase in content_lower]
                if found_urgent:
                    analysis['content_flags'].append(f'Urgent language: {", ".join(found_urgent)}')
                    analysis['risk_score'] += 10

                # Check for brand impersonation
                brand_keywords = ['paypal', 'amazon', 'microsoft', 'apple', 'google', 'bank']
                found_brands = [brand for brand in brand_keywords if brand in content_lower]
                if found_brands:
                    analysis['content_flags'].append(f'Brand references: {", ".join(found_brands)}')
                    # Only add risk if domain doesn't match brand
                    domain = urllib.parse.urlparse(url).netloc.lower()
                    if not any(brand in domain for brand in found_brands):
                        analysis['risk_score'] += 20

                analysis['details'] = {
                    'status_code': response.status_code,
                    'content_length': len(content),
                    'redirects': len(response.history),
                    'final_url': response.url
                }

        except requests.exceptions.SSLError:
            analysis['content_flags'].append('SSL/TLS connection error')
            analysis['risk_score'] += 15
        except requests.exceptions.Timeout:
            analysis['content_flags'].append('Connection timeout')
            analysis['risk_score'] += 5
        except requests.exceptions.ConnectionError:
            analysis['content_flags'].append('Connection failed')
            analysis['risk_score'] += 10
        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def _analyze_security(self, url: str) -> Dict[str, Any]:
        """Analyze SSL/TLS security of the URL"""
        analysis = {
            'ssl_valid': False,
            'risk_score': 0,
            'security_flags': [],
            'details': {}
        }

        try:
            parsed = urllib.parse.urlparse(url)

            # Check if using HTTPS
            if parsed.scheme == 'https':
                analysis['details']['uses_https'] = True

                # Try to verify SSL certificate
                try:
                    hostname = parsed.netloc
                    context = ssl.create_default_context()

                    with socket.create_connection((hostname, 443), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                            cert = ssock.getpeercert()
                            analysis['ssl_valid'] = True
                            analysis['details']['ssl_certificate'] = {
                                'subject': dict(x[0] for x in cert['subject']),
                                'issuer': dict(x[0] for x in cert['issuer']),
                                'version': cert['version']
                            }

                except ssl.SSLError:
                    analysis['security_flags'].append('Invalid SSL certificate')
                    analysis['risk_score'] += 25
                except Exception:
                    analysis['security_flags'].append('SSL verification failed')
                    analysis['risk_score'] += 15

            else:
                analysis['details']['uses_https'] = False
                analysis['security_flags'].append('Not using HTTPS encryption')
                analysis['risk_score'] += 20

        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def _is_domain_similar(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are suspiciously similar (typosquatting)"""
        try:
            # Remove common prefixes and suffixes
            d1 = re.sub(r'^(www\.|m\.)', '', domain1)
            d2 = re.sub(r'^(www\.|m\.)', '', domain2)

            # Check for character substitution
            if len(d1) == len(d2):
                diff_count = sum(c1 != c2 for c1, c2 in zip(d1, d2))
                if diff_count == 1:  # Only one character different
                    return True

            # Check for character insertion/deletion
            if abs(len(d1) - len(d2)) == 1:
                shorter, longer = (d1, d2) if len(d1) < len(d2) else (d2, d1)
                for i in range(len(longer)):
                    if longer[:i] + longer[i+1:] == shorter:
                        return True

            return False

        except Exception:
            return False

    def _calculate_final_assessment(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate final risk assessment based on all analysis components"""
        risk_score = analysis_results['risk_score']

        # Determine risk level and confidence
        if risk_score >= 60:
            analysis_results['is_phishing'] = True
            analysis_results['confidence_level'] = 'High'
            analysis_results['risk_level'] = 'Critical'
            analysis_results['recommendations'] = [
                "🚨 DO NOT visit this link or enter any personal information",
                "This URL shows multiple indicators of a phishing attempt",
                "Report this link to your IT security team",
                "Delete any emails containing this link"
            ]
        elif risk_score >= 40:
            analysis_results['is_phishing'] = True
            analysis_results['confidence_level'] = 'Medium'
            analysis_results['risk_level'] = 'High'
            analysis_results['recommendations'] = [
                "⚠️ Exercise extreme caution with this link",
                "Multiple suspicious indicators detected",
                "Verify the sender through alternative means",
                "Do not enter passwords or personal information"
            ]
        elif risk_score >= 20:
            analysis_results['is_phishing'] = False
            analysis_results['confidence_level'] = 'Medium'
            analysis_results['risk_level'] = 'Medium'
            analysis_results['recommendations'] = [
                "⚡ Proceed with caution",
                "Some suspicious indicators detected",
                "Verify the website's legitimacy before entering sensitive data",
                "Check the URL carefully for typos or unusual patterns"
            ]
        else:
            analysis_results['is_phishing'] = False
            analysis_results['confidence_level'] = 'High'
            analysis_results['risk_level'] = 'Low'
            analysis_results['recommendations'] = [
                "✅ This link appears to be legitimate",
                "No significant security threats detected",
                "Always remain vigilant when entering personal information online"
            ]

        # Collect all threats detected
        threats = []
        for component in ['structure', 'domain', 'content', 'security']:
            details = analysis_results['technical_details'].get(component, {})
            if 'suspicious_patterns' in details:
                threats.extend(details['suspicious_patterns'])
            if 'flags' in details:
                threats.extend(details['flags'])
            if 'content_flags' in details:
                threats.extend(details['content_flags'])
            if 'security_flags' in details:
                threats.extend(details['security_flags'])

        analysis_results['threats_detected'] = threats

        return analysis_results

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result structure"""
        return {
            'error': True,
            'message': error_message,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'risk_score': 0,
            'is_phishing': False,
            'confidence_level': 'Unknown',
            'recommendations': [
                "Unable to analyze this URL",
                "Please check the URL format and try again",
                "If you received this link in an email, verify with the sender"
            ]
        }
