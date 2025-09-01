# Update training_records/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import User
import logging
import requests

logger = logging.getLogger(__name__)

class NoNewUsersAdapter(DefaultAccountAdapter):
    """Prevent new user registration through regular signup"""
    
    def is_open_for_signup(self, request):
        return False  # Disable regular signup completely

class ExistingUsersOnlySocialAdapter(DefaultSocialAccountAdapter):
    """Only allow social login for existing users"""
    
    def is_open_for_signup(self, request, sociallogin):
        return False  # Disable social signup
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.
        """
        if sociallogin.is_existing:
            return  # User already exists, proceed normally
            
        # Try to extract email from multiple possible locations
        email = None
        provider = sociallogin.account.provider
        
        # Log the raw data for debugging
        logger.info(f"Social login attempt - Provider: {provider}")
        logger.info(f"Extra data: {sociallogin.account.extra_data}")
        logger.info(f"Email addresses: {getattr(sociallogin, 'email_addresses', 'None')}")
        
        # Method 1: From extra_data
        if hasattr(sociallogin.account, 'extra_data'):
            extra_data = sociallogin.account.extra_data
            email = (
                extra_data.get('email') or 
                extra_data.get('mail') or  # Microsoft sometimes uses 'mail'
                extra_data.get('userPrincipalName') or  # Microsoft UPN
                extra_data.get('preferred_username')  # Microsoft preferred username
            )
            
        # Method 2: From sociallogin.email_addresses (if available)
        if not email and hasattr(sociallogin, 'email_addresses'):
            if sociallogin.email_addresses:
                email = sociallogin.email_addresses[0].email
                
        # Method 3: From user attribute (for some providers)
        if not email and hasattr(sociallogin, 'user') and sociallogin.user:
            email = getattr(sociallogin.user, 'email', None)
            
        # Method 4: For Microsoft, try alternative extraction
        if not email and provider == 'microsoft':
            email = self._extract_microsoft_email(sociallogin)
        
        logger.info(f"Extracted email: {email}")
        
        if not email:
            # No email provided by social provider
            messages.error(
                request, 
                f"No email address received from {provider.title()}. "
                f"Please ensure your {provider.title()} account has a verified email address, "
                "or contact your administrator."
            )
            raise ImmediateHttpResponse(
                HttpResponseRedirect(reverse('login'))
            )
        
        try:
            # Try to get user by email - handle multiple users case
            users = User.objects.filter(email__iexact=email)
            if users.count() == 1:
                existing_user = users.first()
                # Connect this social account to the existing user
                sociallogin.connect(request, existing_user)
                messages.success(
                    request,
                    f"Successfully linked your {provider.title()} account to your existing account."
                )
                return
            elif users.count() > 1:
                # Multiple users with same email - need admin intervention
                messages.error(
                    request, 
                    f"Multiple accounts found for email '{email}'. "
                    "Please contact your administrator to resolve this issue."
                )
                raise ImmediateHttpResponse(
                    HttpResponseRedirect(reverse('login'))
                )
            # If count is 0, fall through to "no user found" error below
                
        except User.DoesNotExist:
            pass
        
        # No existing user found - block the login
        messages.error(
            request, 
            f"No account found for email '{email}'. Please contact your administrator "
            "to create an account first, then you can link your social media account."
        )
        raise ImmediateHttpResponse(
            HttpResponseRedirect(reverse('login'))
        )
    
    def _extract_microsoft_email(self, sociallogin):
        """
        Try to extract email from Microsoft-specific fields
        """
        try:
            extra_data = sociallogin.account.extra_data
            
            # Try different Microsoft field names
            potential_emails = [
                extra_data.get('mail'),
                extra_data.get('userPrincipalName'),
                extra_data.get('preferred_username'),
                extra_data.get('unique_name'),
                extra_data.get('upn'),
            ]
            
            for email in potential_emails:
                if email and '@' in email:
                    return email
                    
        except Exception as e:
            logger.error(f"Error extracting Microsoft email: {e}")
            
        return None
    
    def save_user(self, request, sociallogin, form=None):
        """Override to prevent new user creation"""
        # This should never be called due to our pre_social_login check,
        # but just in case, raise an error
        raise ImmediateHttpResponse(
            HttpResponseRedirect(reverse('login'))
        )