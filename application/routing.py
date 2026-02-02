from django.urls import re_path
from .consumers import AutomationConsumer

websocket_urlpatterns = [
    re_path(r"ws/automation/(?P<application_id>\d+)/$", AutomationConsumer.as_asgi()),
]
