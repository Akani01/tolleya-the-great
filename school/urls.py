"""
URL configuration for school project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
import os


def ads_txt_view(request):
    ads_path = os.path.join(settings.BASE_DIR, 'static', 'ads.txt')
    try:
        with open(ads_path, 'r') as f:
            return HttpResponse(f.read(), content_type='text/plain')
    except FileNotFoundError:
        return HttpResponse("ads.txt not found", status=404)
    

urlpatterns = [
    path("", include('main_app.urls')),
    path("accounts/", include('allauth.urls')),
    #account
    path("ads.txt", ads_txt_view),
    path("result", include('result.urls')),
    path("quiz", include('quiz.urls')),
    path("job", include('job.urls')),
    path("questpaper", include('questpaper.urls')),
    path("application", include('application.urls')),
    path("photo", include('photo.urls')),
    path("college", include('college.urls')),
    path("bursary", include('bursary.urls')),
    path("accounts/", include("django.contrib.auth.urls")),
    path('admin/', admin.site.urls),
    
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

