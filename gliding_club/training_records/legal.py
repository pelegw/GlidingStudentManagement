from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class PrivacyPolicyView(TemplateView):
    template_name = 'training_records/legal/privacy_policy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Privacy Policy'
        return context

class TermsOfServiceView(TemplateView):
    template_name = 'training_records/legal/terms_of_service.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Terms of Service'
        return context

class DataDeletionView(TemplateView):
    """Required by Meta for data deletion requests"""
    template_name = 'training_records/legal/data_deletion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Data Deletion Request'
        return context