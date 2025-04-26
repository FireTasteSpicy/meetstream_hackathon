from django.urls import path
from . import views

urlpatterns = [
    path('team/<int:team_id>/', views.generate_team_digest, name='generate_team_digest'),
]