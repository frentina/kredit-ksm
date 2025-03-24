from django.urls import include, path
from . import views
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.views.generic import TemplateView

urlpatterns = [
    #path('', views.index, name='index'),
    path('main', views.MainApp.as_view(), name = 'main'),
    path('start-message', views.start_message, name = 'start-message'),
    path('count-ksm', views.KPRCalculator.as_view(), name='count-KPR'),
    path('login', views.LoginView.as_view(), name ="login"),
    path('add-data', views.add_data, name="add-data")
]