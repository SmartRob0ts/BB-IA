"""Chat BB IA e atendimentos de simulação persistidos."""
import json
import logging
import re
import uuid
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .auth_views import _require_auth
from .models import Case, ChatSession
from . import watsonx_service

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = Path(__file__).with_name("system_prompt.txt").read_text(encoding="utf-8")


def _body(request):
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("JSON inválido.")
    if not isinstance(value, dict):
        raise ValueError("O corpo deve ser um objeto JSON.")
    return value


def _session_id(body):
    value = body.get("session_id")
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("session_id inválido.")
    return value


def _validate_case(data):
    if not isinstance(data, dict):
        raise ValueError("Resumo inválido.")
    result = {}
    for field in ("intent", "description", "actions", "documents", "reason"):
        value = data.get(field, "")
        if not isinstance(value, str) or len(value) > (120 if field == "intent" else 4000):
            raise ValueError("Resumo inválido.")
        result[field] = value.strip()
    if not result["intent"] or not result["description"]:
        raise ValueError("Resumo incompleto.")
    info = data.get("information", [])
    if not isinstance(info, list) or len(info) > 20 or any(not isinstance(x, str) or len(x) > 1000 for x in info):
        raise ValueError("Informações inválidas.")
    result["information"] = info
    result["priority"] = data.get("priority", "medium")
    if result["priority"] not in {"high", "medium", "low"}:
        raise ValueError("Prioridade inválida.")
    return result


def _parse_escalate(text):
    before, marker, after = text.partition("<!--ESCALATE-->")
    if not marker:
        return text, None
    match = re.fullmatch(r"\s*```json\s*(.*?)```\s*", after, re.DOTALL)
    try:
        data = _validate_case(json.loads(match.group(1))) if match else None
    except (ValueError, TypeError):
        data = None
    if data is None:
        return "Não consegui preparar o resumo do atendimento. Pode reformular seu pedido?", None
    return before.strip(), data


def _manager(user):
    return user.is_manager


def _scope(user):
    return Case.objects.all() if _manager(user) else Case.objects.filter(user=user)


def _create_case(user, data):
    # Identificador aleatório independente da ordem de gravação e do navegador.
    return Case.objects.create(token="AT-" + uuid.uuid4().hex[:16].upper(),
                               owner=user.name, user=user, demo=True, **data)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat(request):
    if request.method == "OPTIONS":
        return JsonResponse({})
    user, error = _require_auth(request)
    if error is not None:
        return error
    try:
        body = _body(request)
        sid = _session_id(body)
        message = body.get("message", "")
        if not isinstance(message, str) or len(message) > 4000:
            raise ValueError("Mensagem inválida (máximo 4000 caracteres).")
        action = body.get("action")
        if action not in (None, "confirm_case", "cancel_case"):
            raise ValueError("Ação inválida.")
        if action is None and not message.strip():
            raise ValueError("Informe uma mensagem.")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    session, _ = ChatSession.objects.get_or_create(user=user, session_id=sid)
    revision = session.revision
    if action is not None:
        with transaction.atomic():
            # Conditional update serializa confirmações e impede duplicação em retries.
            if not ChatSession.objects.filter(pk=session.pk, revision=revision).update(revision=revision + 1):
                return JsonResponse({"error": "Atendimento atualizado. Tente novamente."}, status=409)
            session.refresh_from_db()
            if action == "cancel_case":
                session.pending_case = None
                session.save(update_fields=["pending_case"])
                return JsonResponse({"reply": "Encaminhamento cancelado.", "escalated": False, "case": None})
            if session.case_id:
                case = session.case
            elif session.pending_case:
                case = _create_case(user, _validate_case(session.pending_case))
                session.case = case
                session.pending_case = None
                session.save(update_fields=["case", "pending_case"])
            else:
                return JsonResponse({"error": "Não há encaminhamento pendente."}, status=409)
        return JsonResponse({"reply": "Atendimento de simulação registrado. Protocolo: " + case.token,
                             "escalated": True, "case": case.to_dict()})
    if session.pending_case:
        return JsonResponse({"reply": "Confirme ou cancele o encaminhamento pendente antes de continuar.",
                             "pending_confirmation": True, "proposal": session.pending_case,
                             "escalated": False, "case": None})
    if session.case_id:
        return JsonResponse({"reply": "Este atendimento já foi registrado. Inicie uma nova solicitação para outro assunto.",
                             "escalated": True, "case": session.case.to_dict()})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + session.history[-20:] + [
        {"role": "user", "content": message.strip()}]
    try:
        raw = watsonx_service.reply(messages)
    except watsonx_service.ConfigurationError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except Exception:
        logger.warning("Falha na chamada ao watsonx.ai")
        return JsonResponse({"error": "Não foi possível consultar o BB IA. Tente novamente em instantes."}, status=502)
    text, proposal = _parse_escalate(raw)
    history = (session.history + [{"role": "user", "content": message.strip()},
                                 {"role": "assistant", "content": text}])[-20:]
    updated = ChatSession.objects.filter(pk=session.pk, revision=revision).update(
        history=history, pending_case=proposal, revision=revision + 1)
    if not updated:
        return JsonResponse({"error": "A conversa mudou durante a resposta. Tente novamente."}, status=409)
    if proposal:
        text = "Preparei uma solicitação de simulação: " + proposal["description"] + "\n\nDeseja registrar e gerar o protocolo?"
    return JsonResponse({"reply": text, "escalated": False, "case": None,
                         "pending_confirmation": proposal is not None, "proposal": proposal})


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def cases_list(request):
    if request.method == "OPTIONS":
        return JsonResponse({})
    user, error = _require_auth(request)
    if error is not None:
        return error
    if request.method == "GET":
        return JsonResponse({"cases": [c.to_dict() for c in _scope(user)], "can_manage": _manager(user)})
    return JsonResponse({"error": "Registre atendimentos pelo chat, após confirmação."}, status=405)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "OPTIONS"])
def case_detail(request, token):
    if request.method == "OPTIONS":
        return JsonResponse({})
    user, error = _require_auth(request)
    if error is not None:
        return error
    try:
        case = _scope(user).get(token=token)
    except Case.DoesNotExist:
        return JsonResponse({"error": "Atendimento não encontrado."}, status=404)
    if request.method == "PATCH":
        if not _manager(user):
            return JsonResponse({"error": "Acesso restrito ao gerente."}, status=403)
        try:
            body = _body(request)
            if set(body) - {"status", "notes"}:
                raise ValueError("Campos inválidos.")
            if "status" in body and body["status"] not in {"waiting", "active", "done"}:
                raise ValueError("Status inválido.")
            if "notes" in body and (not isinstance(body["notes"], str) or len(body["notes"]) > 4000):
                raise ValueError("Notas inválidas.")
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        for field, value in body.items():
            setattr(case, field, value)
        case.save()
    return JsonResponse({"case": case.to_dict()})


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat_reset(request):
    if request.method == "OPTIONS":
        return JsonResponse({})
    user, error = _require_auth(request)
    if error is not None:
        return error
    try:
        sid = _session_id(_body(request))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    # Invalida respostas em trânsito, mantendo protocolos já registrados.
    from django.db.models import F
    ChatSession.objects.filter(user=user, session_id=sid).update(
        history=[], pending_case=None, revision=F("revision") + 1)
    return JsonResponse({"ok": True})
