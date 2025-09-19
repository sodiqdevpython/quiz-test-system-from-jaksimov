from django.urls import path
from .views import (
    RegisterView, ChangePasswordView, UpdateEmailView,
    ForgotPasswordView, ResetPasswordView
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("update-email/", UpdateEmailView.as_view(), name="update_email"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
]
