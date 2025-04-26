from django.urls import path
from . import views

urlpatterns = [
    path('', views.process_prompt, name='process_prompt'),
]