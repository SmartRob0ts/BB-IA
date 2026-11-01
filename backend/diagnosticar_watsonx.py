"""Execute com o mesmo Python usado para iniciar o Django."""
import importlib.metadata
import os
import re
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartrobots.settings")
    try:
        import django
        django.setup()
        from django.conf import settings
    except Exception as exc:
        print("Não foi possível carregar o backend:", type(exc).__name__)
        print("Coloque este arquivo ao lado de manage.py e use o Python do ambiente do backend.")
        return 1
    secrets = [settings.WATSONX_API_KEY, settings.SECRET_KEY]

    def clean(value):
        text = str(value)
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[SEGREDO OCULTADO]")
        text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[OCULTADO]", text)
        text = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[TOKEN OCULTADO]", text)
        text = re.sub(r'(?i)([\"\']?(?:access_token|refresh_token|apikey|api_key|authorization)[\"\']?\s*[:=]\s*[\"\']?)[^\s,}\"\']+', r'\1[OCULTADO]', text)
        return text[:6000]

    print("Python:", sys.version.split()[0])
    for package in ("Django", "ibm-watsonx-ai", "python-dotenv"):
        try:
            print(package + ":", importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            print(package + ": NÃO INSTALADO neste Python")
    for field in ("WATSONX_URL", "WATSONX_PROJECT_ID", "WATSONX_MODEL_ID"):
        print(field + ":", clean(getattr(settings, field)))
    print("Chave IBM:", "preenchida (valor oculto)" if settings.WATSONX_API_KEY else "AUSENTE")
    print("Verificando importação e enviando uma mensagem curta ao modelo...")
    try:
        from agent.watsonx_service import reply
        text = reply([{"role": "user", "content": "Responda apenas: OK"}])
        print("SUCESSO: a IBM retornou uma resposta de texto.")
        print("O teste não registra atendimento nem altera o banco.")
        return 0
    except Exception as exc:
        print("FALHA:", type(exc).__name__)
        print(clean(exc))
        print("Oculte qualquer informação privada remanescente antes de compartilhar esta saída.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
