"""
AI Chat Service

This service handles AI-powered chat functionality for security education.
Specifically designed to help employees who clicked phishing links understand
cybersecurity concepts and prevention methods.
"""
import os
import logging
from typing import List, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)

# Try to import OpenAI - gracefully handle if not installed
try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False
    logger.warning("OpenAI library not available. AI chat features will be disabled.")


class AIPhishingSecurityChat:
    """
    AI Chat service specialized for phishing security education.
    Only responds to cybersecurity and phishing-related questions.
    """

    def __init__(self):
        self.client = None
        if openai_available:
            api_key = current_app.config.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                logger.warning("OpenAI API key not found. AI chat will use fallback responses.")

    def get_system_prompt(self) -> str:
        """
        Return the system prompt that restricts AI to only cybersecurity topics.
        """
        return """You are a cybersecurity education assistant specializing in phishing prevention and email security.

Your role is to help employees who have clicked on phishing links understand:
- What phishing is and how it works
- How to identify phishing emails and suspicious links
- Best practices for email security
- Steps to take if they've been phished
- General cybersecurity awareness

IMPORTANT RESTRICTIONS:
- ONLY respond to questions related to cybersecurity, phishing, email security, and data protection
- If asked about anything else (personal advice, general topics, other subjects), politely redirect to cybersecurity topics
- Be encouraging and educational, not judgmental about security mistakes
- Provide practical, actionable advice
- Keep responses concise but informative
- If you're unsure if a topic is cybersecurity-related, err on the side of redirection

Example redirect response: "I'm here to help with cybersecurity and phishing prevention questions. Let's focus on keeping you and your organization safe online. Is there something specific about email security or phishing you'd like to learn about?"
"""

    def is_security_related_question(self, message: str) -> bool:
        """
        Check if the question is related to cybersecurity topics.
        This is a simple keyword-based filter as a backup.
        """
        security_keywords = [
            'phishing', 'email', 'security', 'password', 'link', 'attachment',
            'virus', 'malware', 'hack', 'scam', 'fraud', 'suspicious',
            'cyber', 'data', 'privacy', 'protection', 'safe', 'secure',
            'threat', 'attack', 'breach', 'firewall', 'antivirus',
            'two-factor', '2fa', 'authentication', 'encryption', 'backup',
            'social engineering', 'spear phishing', 'ransomware'
        ]

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in security_keywords)

    def get_fallback_response(self, message: str) -> Dict[str, Any]:
        """
        Provide fallback responses when OpenAI is not available.
        """
        message_lower = message.lower()

        # Common phishing questions and responses
        if any(word in message_lower for word in ['phishing', 'phish']):
            if 'what is' in message_lower or 'define' in message_lower:
                return {
                    'response': """Phishing is a type of cyber attack where criminals try to trick you into revealing sensitive information like passwords, credit card numbers, or personal data. They typically do this by:

• Sending fake emails that look like they're from legitimate companies
• Creating fake websites that mimic real ones
• Using urgent or threatening language to pressure you into acting quickly
• Including malicious links or attachments

The key is to always verify the sender and be suspicious of unsolicited requests for personal information.""",
                    'suggestions': [
                        "How can I identify phishing emails?",
                        "What should I do if I clicked a phishing link?",
                        "How can I protect myself from phishing?"
                    ]
                }
            elif 'identify' in message_lower or 'recognize' in message_lower:
                return {
                    'response': """Here are key signs of phishing emails:

🚨 **Red Flags:**
• Generic greetings ("Dear Customer" instead of your name)
• Urgent language ("Act now!" "Account will be closed!")
• Misspelled domain names (amazom.com instead of amazon.com)
• Poor grammar and spelling errors
• Requests for sensitive information via email
• Suspicious attachments or links

🔍 **Always verify:**
• Hover over links to see the real destination
• Check the sender's email address carefully
• Contact the company directly if unsure
• Look for HTTPS and proper certificates on websites""",
                    'suggestions': [
                        "What should I do if I clicked a phishing link?",
                        "How can I report phishing emails?",
                        "What are some common phishing tactics?"
                    ]
                }

        elif any(word in message_lower for word in ['clicked', 'click']):
            return {
                'response': """If you clicked a phishing link, here's what to do immediately:

⚡ **Immediate Actions:**
1. **Don't panic** - You're taking the right steps by asking for help
2. **Disconnect** from the internet if possible
3. **Don't enter any information** on the suspicious website
4. **Close the browser** or tab immediately

🛡️ **Next Steps:**
1. **Change passwords** for any accounts that might be compromised
2. **Run antivirus scans** on your device
3. **Report the incident** to your IT security team
4. **Monitor accounts** for unusual activity
5. **Enable two-factor authentication** where possible

Remember: Clicking a link doesn't automatically compromise your security - the real risk comes from entering information on malicious sites.""",
                'suggestions': [
                    "How do I change my passwords securely?",
                    "What is two-factor authentication?",
                    "How can I scan for malware?"
                ]
            }

        elif any(word in message_lower for word in ['password', 'passwords']):
            return {
                'response': """Here's how to create and manage secure passwords:

🔐 **Strong Password Guidelines:**
• At least 12 characters long
• Mix of uppercase, lowercase, numbers, and symbols
• Avoid personal information (birthdays, names, etc.)
• Don't reuse passwords across multiple accounts
• Consider using passphrases (e.g., "Coffee!Morning@Beach2024")

🛠️ **Best Practices:**
• Use a password manager to generate and store passwords
• Enable two-factor authentication (2FA) whenever possible
• Change passwords immediately if you suspect compromise
• Don't share passwords via email or text
• Use different passwords for work and personal accounts""",
                'suggestions': [
                    "What is two-factor authentication?",
                    "How do password managers work?",
                    "What should I do if my password was stolen?"
                ]
            }

        elif any(word in message_lower for word in ['2fa', 'two-factor', 'authentication']):
            return {
                'response': """Two-Factor Authentication (2FA) adds an extra layer of security:

🔒 **What is 2FA?**
2FA requires two forms of verification:
1. Something you know (password)
2. Something you have (phone, authenticator app, hardware token)

📱 **Common 2FA Methods:**
• **Text messages (SMS)** - codes sent to your phone
• **Authenticator apps** - Google Authenticator, Authy, Microsoft Authenticator
• **Hardware tokens** - physical devices like YubiKey
• **Biometrics** - fingerprint, face recognition

✅ **Why use 2FA?**
Even if someone steals your password, they still can't access your account without the second factor. It's one of the most effective ways to protect your accounts.""",
                'suggestions': [
                    "Which 2FA method is most secure?",
                    "How do I set up 2FA on my accounts?",
                    "What if I lose my 2FA device?"
                ]
            }

        # Check if question is security-related
        elif self.is_security_related_question(message):
            return {
                'response': """I'm here to help with cybersecurity questions! While I can provide general guidance on this topic, I'd recommend being more specific about what you'd like to know.

Some areas I can help with:
• Identifying and preventing phishing attacks
• Email security best practices
• Password security and two-factor authentication
• What to do if you've been targeted by cybercriminals
• General cybersecurity awareness tips

What specific cybersecurity topic would you like to learn about?""",
                'suggestions': [
                    "How can I identify phishing emails?",
                    "What should I do if I clicked a phishing link?",
                    "How can I create strong passwords?",
                    "What is two-factor authentication?"
                ]
            }

        else:
            # Non-security related question
            return {
                'response': """I'm a cybersecurity education assistant, so I can only help with questions about online security, phishing prevention, and protecting your digital information.

Since you're here because of a phishing simulation, let's focus on keeping you safe online! Here are some topics I can help with:

• Understanding how phishing attacks work
• Learning to identify suspicious emails and links
• Best practices for password security
• Steps to take if you've been targeted by cybercriminals
• Two-factor authentication and other security measures

What would you like to learn about cybersecurity today?""",
                'suggestions': [
                    "How can I identify phishing emails?",
                    "What should I do if I clicked a phishing link?",
                    "How can I create strong passwords?",
                    "What is two-factor authentication?"
                ]
            }

    def get_ai_response(self, message: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get AI response using OpenAI API or fallback responses.
        """
        try:
            if not self.client:
                return self.get_fallback_response(message)

            # Prepare conversation history
            messages = [{"role": "system", "content": self.get_system_prompt()}]

            if conversation_history:
                for msg in conversation_history[-10:]:  # Keep last 10 messages for context
                    messages.append({
                        "role": "user" if msg.get('is_user') else "assistant",
                        "content": msg.get('message', '')
                    })

            messages.append({"role": "user", "content": message})

            # Make API call
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            ai_response = response.choices[0].message.content
            if ai_response:
                ai_response = ai_response.strip()
            else:
                ai_response = "I apologize, but I'm having trouble generating a response right now. Please try asking your question again."

            # Generate context-appropriate suggestions
            suggestions = self._generate_suggestions(message, ai_response)

            return {
                'response': ai_response,
                'suggestions': suggestions
            }

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return self.get_fallback_response(message)

    def _generate_suggestions(self, user_message: str, ai_response: str) -> List[str]:
        """
        Generate follow-up suggestions based on the conversation context.
        """
        message_lower = user_message.lower()

        # Context-aware suggestions
        if 'phishing' in message_lower:
            return [
                "How can I report phishing emails?",
                "What are common phishing tactics?",
                "How do I protect my organization from phishing?"
            ]
        elif 'password' in message_lower:
            return [
                "What is two-factor authentication?",
                "How do password managers work?",
                "How often should I change passwords?"
            ]
        elif 'clicked' in message_lower or 'link' in message_lower:
            return [
                "How do I scan for malware?",
                "Should I report this to IT?",
                "How can I prevent this in the future?"
            ]
        elif '2fa' in message_lower or 'authentication' in message_lower:
            return [
                "Which 2FA method is most secure?",
                "How do I set up 2FA?",
                "What if I lose my 2FA device?"
            ]
        else:
            # Default suggestions
            return [
                "How can I identify phishing emails?",
                "What should I do if I clicked a phishing link?",
                "How can I create strong passwords?",
                "What is two-factor authentication?"
            ]
