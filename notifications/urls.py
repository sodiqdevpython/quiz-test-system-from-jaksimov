from django.urls import path
from django.views.generic import TemplateView
from .views import SaveTokenView

urlpatterns = [
    path("save-token/", SaveTokenView.as_view(), name="save_token"),
    path("push-test/", TemplateView.as_view(template_name="push-test.html")),
]
