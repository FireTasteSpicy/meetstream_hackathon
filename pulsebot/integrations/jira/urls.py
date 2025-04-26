from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.jira_webhook, name='jira_webhook'),
    path('auth/', views.jira_auth, name='jira_auth'),
]