from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/signup/", views.SignupView.as_view(), name="auth-signup"),
    path("auth/verify/", views.VerifyEmailView.as_view(), name="auth-verify"),
    path("auth/verify/resend/", views.ResendVerificationView.as_view(), name="auth-verify-resend"),
    path("auth/captcha/", views.CaptchaKeysView.as_view(), name="auth-captcha"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/password/forgot/", views.ForgotPasswordView.as_view(), name="auth-forgot"),
    path("auth/password/reset/", views.ResetPasswordView.as_view(), name="auth-reset"),
    path("auth/2fa/", views.TwoFactorView.as_view(), name="auth-2fa"),
    path("auth/2fa/setup/", views.TwoFactorSetupView.as_view(), name="auth-2fa-setup"),
    path("auth/2fa/confirm/", views.TwoFactorConfirmView.as_view(), name="auth-2fa-confirm"),
    path("auth/2fa/disable/", views.TwoFactorDisableView.as_view(), name="auth-2fa-disable"),
    path("auth/2fa/verify/", views.TwoFactorVerifyView.as_view(), name="auth-2fa-verify"),
    path("auth/2fa/recovery-codes/", views.RecoveryCodesView.as_view(), name="auth-2fa-recovery"),
    path("auth/sso/", views.SsoProvidersView.as_view(), name="auth-sso"),
    path("auth/identities/", views.IdentitiesView.as_view(), name="auth-identities"),
    path("auth/identities/<str:provider>/", views.IdentityView.as_view(), name="auth-identity"),
    path("auth/me/export/", views.ExportView.as_view(), name="auth-export"),
    path("auth/me/delete/", views.DeleteAccountView.as_view(), name="auth-delete"),
]
