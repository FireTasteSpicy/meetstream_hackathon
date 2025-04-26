"""pulsebot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('api/github/', include('integrations.github.urls')),
    path('api/jira/', include('integrations.jira.urls')),
    path('api/followup/', include('output_generator.followup.urls')),
    path('api/standup/', include('output_generator.standup.urls')),
    path('api/digest/', include('output_generator.digest.urls')),
    path('api/prompt/', include('orchestration.prompt_manager.urls')),
]
