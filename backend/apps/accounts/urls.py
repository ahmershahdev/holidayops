from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/signup/", views.SignupView.as_view(), name="auth-signup"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/password/forgot/", views.ForgotPasswordView.as_view(), name="auth-forgot"),
    path("auth/password/reset/", views.ResetPasswordView.as_view(), name="auth-reset"),
]
