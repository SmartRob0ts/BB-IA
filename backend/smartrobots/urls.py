"""URL configuration for SmartRobots BB IA backend."""

from django.urls import path

from agent import views
from agent import auth_views

urlpatterns = [
    # ── Chat com o agente BB IA ──────────────────────────────────────────────
    path("api/chat/",       views.chat,       name="chat"),
    path("api/chat/reset/", views.chat_reset, name="chat-reset"),

    # ── CRUD de casos (fila do gerente) ───────────────────────────────────────
    path("api/cases/",              views.cases_list,  name="cases-list"),
    path("api/cases/<str:token>/",  views.case_detail, name="case-detail"),

    # ── Autenticação ──────────────────────────────────────────────────────────
    path("api/auth/register/", auth_views.register, name="auth-register"),
    path("api/auth/login/",    auth_views.login,    name="auth-login"),
    path("api/auth/logout/",   auth_views.logout,   name="auth-logout"),
    path("api/auth/me/",       auth_views.me,        name="auth-me"),

    # ── Perfil financeiro ─────────────────────────────────────────────────────
    path("api/profile/",       auth_views.profile,   name="profile"),

    # ── Investimentos ─────────────────────────────────────────────────────────
    path("api/investments/",          auth_views.investments_list,   name="investments-list"),
    path("api/investments/<int:inv_id>/", auth_views.investment_detail, name="investment-detail"),
]
