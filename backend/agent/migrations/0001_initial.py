"""Migration inicial — cria a tabela Case."""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="Case",
            fields=[
                ("id",          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token",       models.CharField(max_length=20, unique=True)),
                ("owner",       models.CharField(default="Cliente desta sessão", max_length=120)),
                ("intent",      models.CharField(max_length=120)),
                ("description", models.TextField()),
                ("information", models.JSONField(default=list)),
                ("actions",     models.TextField(blank=True)),
                ("documents",   models.TextField(blank=True)),
                ("reason",      models.TextField(blank=True)),
                ("priority",    models.CharField(choices=[("high","Alta"),("medium","Normal"),("low","Baixa")], default="medium", max_length=10)),
                ("status",      models.CharField(choices=[("waiting","Aguardando"),("active","Em atendimento"),("done","Concluído")], default="waiting", max_length=10)),
                ("notes",       models.TextField(blank=True)),
                ("demo",        models.BooleanField(default=False)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
