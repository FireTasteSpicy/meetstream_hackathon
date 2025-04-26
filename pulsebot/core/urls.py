from django.urls import path
from .api_docs import api_docs

urlpatterns = [
    path('', api_docs, name='api_docs'),
]