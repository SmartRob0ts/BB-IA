"""
Views de autenticação e perfil financeiro — BB IA.

Endpoints:
  POST /api/auth/register/         — cadastro
  POST /api/auth/login/            — login → retorna token
  POST /api/auth/logout/           — invalida token
  GET  /api/auth/me/               — dados do usuário autenticado

  GET  /api/profile/               — limites do cliente
  PATCH /api/profile/              — atualiza limite PIX e/ou cartão (cartão: 1 vez)

  GET  /api/investments/           — lista investimentos do cliente
  POST /api/investments/           — cria novo investimento
  GET  /api/investments/<id>/      — detalhe
  PATCH /api/investments/<id>/     — atualiza saldo / depósito pendente
  DELETE /api/investments/<id>/    — remove investimento
"""

import hashlib
import hmac
from django.contrib.auth.hashers import make_password, check_password
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import AuthToken, Card, FinancialProfile, Investment, User

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return make_password(plain)



def _get_user(request) -> User | None:
    """Extrai o usuário autenticado a partir do header Authorization: Token <tok>."""
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth.startswith("Token "):
        return None
    raw = auth[6:].strip()
    try:
        at = AuthToken.objects.select_related("user").get(token=raw)
        return at.user
    except AuthToken.DoesNotExist:
        return None


def _require_auth(request):
    """Retorna (user, None) ou (None, JsonResponse 401)."""
    user = _get_user(request)
    if user is None:
        return None, JsonResponse({"error": "Não autenticado."}, status=401)
    return user, None


def _cors_ok(methods="GET, POST, PATCH, DELETE, OPTIONS"):
    r = JsonResponse({})
    r["Access-Control-Allow-Origin"]  = "*"
    r["Access-Control-Allow-Methods"] = methods
    r["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return r


def _json_body(request):
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "JSON inválido."}, status=400)


# ─── Auth: register ───────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def register(request):
    if request.method == "OPTIONS":
        return _cors_ok("POST, OPTIONS")

    body, err = _json_body(request)
    if err:
        return err

    name     = (body.get("name") or "").strip()
    email    = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()

    if not name or not email or not password:
        return JsonResponse({"error": "Nome, e-mail e senha são obrigatórios."}, status=400)
    if len(password) < 6:
        return JsonResponse({"error": "A senha deve ter pelo menos 6 caracteres."}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "E-mail já cadastrado."}, status=409)

    user = User.objects.create(
        name=name,
        email=email,
        password=_hash_password(password),
    )
    # Cria perfil financeiro inicial
    FinancialProfile.objects.create(user=user)

    token_obj = AuthToken.generate(user)
    return JsonResponse({
        "token": token_obj.token,
        "user":  user.to_dict(),
    }, status=201)


# ─── Auth: login ──────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login(request):
    if request.method == "OPTIONS":
        return _cors_ok("POST, OPTIONS")

    body, err = _json_body(request)
    if err:
        return err

    email    = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"error": "E-mail ou senha incorretos."}, status=401)

    legacy = len(user.password) == 64 and all(c in "0123456789abcdef" for c in user.password)
    valid = hmac.compare_digest(user.password, hashlib.sha256(password.encode()).hexdigest()) if legacy else check_password(password, user.password)
    if not valid:
        return JsonResponse({"error": "E-mail ou senha incorretos."}, status=401)

    if legacy:
        user.password = make_password(password)
        user.save(update_fields=["password"])
    token_obj = AuthToken.generate(user)
    return JsonResponse({
        "token": token_obj.token,
        "user":  user.to_dict(),
    })


# ─── Auth: logout ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def logout(request):
    if request.method == "OPTIONS":
        return _cors_ok("POST, OPTIONS")

    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Token "):
        AuthToken.objects.filter(token=auth[6:].strip()).delete()
    return JsonResponse({"ok": True})


# ─── Auth: me ─────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def me(request):
    if request.method == "OPTIONS":
        return _cors_ok("GET, OPTIONS")

    user, err = _require_auth(request)
    if err:
        return err

    profile = getattr(user, "profile", None)
    return JsonResponse({
        "user":    user.to_dict(),
        "profile": profile.to_dict() if profile else None,
    })


# ─── Profile ──────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET", "PATCH", "OPTIONS"])
def profile(request):
    if request.method == "OPTIONS":
        return _cors_ok("GET, PATCH, OPTIONS")

    user, err = _require_auth(request)
    if err:
        return err

    prof, _ = FinancialProfile.objects.get_or_create(user=user)

    if request.method == "GET":
        return JsonResponse({"profile": prof.to_dict()})

    # PATCH
    body, err = _json_body(request)
    if err:
        return err

    errors = []

    # Limite PIX — sempre editável
    if "pix_limit" in body:
        try:
            val = float(body["pix_limit"])
            if val < 0:
                errors.append("Limite PIX não pode ser negativo.")
            elif val > 50_000:
                errors.append("Limite PIX não pode exceder R$ 50.000.")
            else:
                prof.pix_limit = val
        except (TypeError, ValueError):
            errors.append("pix_limit inválido.")

    # Limite cartão — só uma vez pelo cliente
    if "credit_limit" in body:
        if prof.credit_limit_changed:
            errors.append(
                "O limite do cartão de crédito já foi alterado uma vez. "
                "Para solicitar novo aumento, converse com o agente."
            )
        else:
            try:
                val = float(body["credit_limit"])
                if val < 0:
                    errors.append("Limite do cartão não pode ser negativo.")
                elif val > 100_000:
                    errors.append("Limite do cartão não pode exceder R$ 100.000.")
                else:
                    prof.credit_limit = val
                    prof.credit_limit_changed = True
            except (TypeError, ValueError):
                errors.append("credit_limit inválido.")

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    prof.save()
    return JsonResponse({"profile": prof.to_dict()})


# ─── Investments ──────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def investments_list(request):
    if request.method == "OPTIONS":
        return _cors_ok()

    user, err = _require_auth(request)
    if err:
        return err

    if request.method == "GET":
        qs = Investment.objects.filter(user=user)
        return JsonResponse({"investments": [i.to_dict() for i in qs]})

    # POST — cria novo investimento
    body, err = _json_body(request)
    if err:
        return err

    name = (body.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "Nome do investimento é obrigatório."}, status=400)

    valid_types = {c[0] for c in Investment.TYPE_CHOICES}
    inv_type = body.get("type", "outro")
    if inv_type not in valid_types:
        inv_type = "outro"

    try:
        balance = float(body.get("balance", 0))
        if balance < 0:
            return JsonResponse({"error": "Saldo não pode ser negativo."}, status=400)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Saldo inválido."}, status=400)

    inv = Investment.objects.create(
        user=user,
        name=name,
        type=inv_type,
        balance=balance,
    )
    return JsonResponse({"investment": inv.to_dict()}, status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE", "OPTIONS"])
def investment_detail(request, inv_id: int):
    if request.method == "OPTIONS":
        return _cors_ok()

    user, err = _require_auth(request)
    if err:
        return err

    try:
        inv = Investment.objects.get(pk=inv_id, user=user)
    except Investment.DoesNotExist:
        return JsonResponse({"error": "Investimento não encontrado."}, status=404)

    if request.method == "GET":
        return JsonResponse({"investment": inv.to_dict()})

    if request.method == "DELETE":
        inv.delete()
        return JsonResponse({"ok": True})

    # PATCH — atualiza saldo e/ou depósito pendente
    body, err = _json_body(request)
    if err:
        return err

    errors = []
    if "balance" in body:
        try:
            val = float(body["balance"])
            if val < 0:
                errors.append("Saldo não pode ser negativo.")
            else:
                inv.balance = val
        except (TypeError, ValueError):
            errors.append("balance inválido.")

    if "pending_deposit" in body:
        try:
            val = float(body["pending_deposit"])
            if val < 0:
                errors.append("Depósito pendente não pode ser negativo.")
            else:
                inv.pending_deposit = val
        except (TypeError, ValueError):
            errors.append("pending_deposit inválido.")

    if "name" in body:
        name = (body["name"] or "").strip()
        if name:
            inv.name = name

    if "type" in body:
        valid_types = {c[0] for c in Investment.TYPE_CHOICES}
        if body["type"] in valid_types:
            inv.type = body["type"]

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    inv.save()
    return JsonResponse({"investment": inv.to_dict()})


# ─── Cards ────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def cards_list(request):
    """GET: lista cartões do cliente. POST: adiciona novo cartão."""
    if request.method == "OPTIONS":
        return _cors_ok()

    user, err = _require_auth(request)
    if err:
        return err

    if request.method == "GET":
        qs = Card.objects.filter(user=user)
        return JsonResponse({"cards": [c.to_dict() for c in qs]})

    # POST — adiciona novo cartão
    body, err = _json_body(request)
    if err:
        return err

    nickname = (body.get("nickname") or "").strip()
    if not nickname:
        return JsonResponse({"error": "Apelido do cartão é obrigatório."}, status=400)
    if len(nickname) > 60:
        return JsonResponse({"error": "Apelido deve ter no máximo 60 caracteres."}, status=400)

    last4 = str(body.get("last4") or "").strip()
    if not last4.isdigit() or len(last4) != 4:
        return JsonResponse({"error": "Informe os últimos 4 dígitos do cartão."}, status=400)

    valid_brands = {c[0] for c in Card.BRAND_CHOICES}
    brand = body.get("brand", "outro")
    if brand not in valid_brands:
        brand = "outro"

    if Card.objects.filter(user=user).count() >= 10:
        return JsonResponse({"error": "Limite de 10 cartões por conta atingido."}, status=400)

    card = Card.objects.create(user=user, nickname=nickname, brand=brand, last4=last4)
    return JsonResponse({"card": card.to_dict()}, status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE", "OPTIONS"])
def card_detail(request, card_id: int):
    """GET: detalhes. PATCH: bloquear/desbloquear. DELETE: remover."""
    if request.method == "OPTIONS":
        return _cors_ok()

    user, err = _require_auth(request)
    if err:
        return err

    try:
        card = Card.objects.get(pk=card_id, user=user)
    except Card.DoesNotExist:
        return JsonResponse({"error": "Cartão não encontrado."}, status=404)

    if request.method == "GET":
        return JsonResponse({"card": card.to_dict()})

    if request.method == "DELETE":
        card.delete()
        return JsonResponse({"ok": True})

    # PATCH — permite apenas alteração do campo blocked (e nickname)
    body, err = _json_body(request)
    if err:
        return err

    allowed = {"blocked", "nickname"}
    if set(body) - allowed:
        return JsonResponse({"error": "Campos inválidos. Permitido: blocked, nickname."}, status=400)

    if "blocked" in body:
        if not isinstance(body["blocked"], bool):
            return JsonResponse({"error": "blocked deve ser true ou false."}, status=400)
        card.blocked = body["blocked"]

    if "nickname" in body:
        nickname = (body["nickname"] or "").strip()
        if not nickname or len(nickname) > 60:
            return JsonResponse({"error": "Apelido inválido."}, status=400)
        card.nickname = nickname

    card.save()
    return JsonResponse({"card": card.to_dict()})
