"""Cliente IBM isolado das rotas; nenhuma credencial vai ao navegador."""
from django.conf import settings

class ConfigurationError(Exception):
    pass

def reply(messages):
    values = [settings.WATSONX_API_KEY, settings.WATSONX_URL,
              settings.WATSONX_PROJECT_ID, settings.WATSONX_MODEL_ID]
    if not all(values):
        raise ConfigurationError("Configure WATSONX_API_KEY, WATSONX_URL, WATSONX_PROJECT_ID e WATSONX_MODEL_ID no backend.")
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    model = ModelInference(
        model_id=settings.WATSONX_MODEL_ID,
        credentials=Credentials(api_key=settings.WATSONX_API_KEY, url=settings.WATSONX_URL),
        project_id=settings.WATSONX_PROJECT_ID,
        params={"max_tokens": 900, "temperature": 0.2},
    )
    result = model.chat(messages=messages)
    text = result["choices"][0]["message"]["content"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Resposta vazia do modelo")
    return text
