from django.core.management.base import BaseCommand, CommandError
from agent.models import User

class Command(BaseCommand):
    help = "Autoriza uma conta já cadastrada a operar o painel do gerente."
    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--revoke", action="store_true")
    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["email"].strip().lower())
        except User.DoesNotExist:
            raise CommandError("Cadastre a conta antes de conceder acesso.")
        user.is_manager = not options["revoke"]
        user.save(update_fields=["is_manager"])
        self.stdout.write("Permissão de gerente atualizada.")
