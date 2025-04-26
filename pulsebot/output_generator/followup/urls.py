from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_personal_followup, name='personal_followup'),
    path('send-email/', views.send_followup_email, name='send_followup_email'),
    path('send-slack/', views.send_followup_slack, name='send_followup_slack'),
]