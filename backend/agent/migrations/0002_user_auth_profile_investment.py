"""Migration 0002 — User, AuthToken, FinancialProfile, Investment + FK em Case."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0001_initial"),
    ]

    operations = [
        # ── User ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="User",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name",       models.CharField(max_length=120)),
                ("email",      models.EmailField(unique=True)),
                ("password",   models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        # ── AuthToken ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="AuthToken",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token",      models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user",       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tokens", to="agent.user")),
            ],
        ),
        # ── FinancialProfile ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="FinancialProfile",
            fields=[
                ("id",                   models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pix_limit",            models.DecimalField(decimal_places=2, default=1000.0, max_digits=12)),
                ("credit_limit",         models.DecimalField(decimal_places=2, default=500.0, max_digits=12)),
                ("credit_limit_changed", models.BooleanField(default=False)),
                ("updated_at",           models.DateTimeField(auto_now=True)),
                ("user",                 models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to="agent.user")),
            ],
        ),
        # ── Investment ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Investment",
            fields=[
                ("id",              models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name",            models.CharField(max_length=120)),
                ("type",            models.CharField(
                    choices=[
                        ("tesouro_selic","Tesouro Selic"),("tesouro_ipca","Tesouro IPCA+"),
                        ("cdb","CDB"),("lci","LCI"),("lca","LCA"),
                        ("fundo_renda_fixa","Fundo Renda Fixa"),
                        ("fundo_multimercado","Fundo Multimercado"),
                        ("acoes","Ações"),("outro","Outro"),
                    ],
                    default="outro", max_length=30,
                )),
                ("balance",         models.DecimalField(decimal_places=2, default=0.0, max_digits=14)),
                ("pending_deposit", models.DecimalField(decimal_places=2, default=0.0, max_digits=14)),
                ("created_at",      models.DateTimeField(auto_now_add=True)),
                ("updated_at",      models.DateTimeField(auto_now=True)),
                ("user",            models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="investments", to="agent.user")),
            ],
            options={"ordering": ["name"]},
        ),
        # ── Case: adiciona FK para User ───────────────────────────────────────
        migrations.AddField(
            model_name="case",
            name="user",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases",
                to="agent.user",
            ),
        ),
    ]
