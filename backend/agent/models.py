import secrets
from django.db import models


class User(models.Model):
    """Cliente BB IA."""

    name       = models.CharField(max_length=120)
    email      = models.EmailField(unique=True)
    # Senha armazenada com hash (pbkdf2_sha256 via hashlib)
    password   = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_manager = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def to_dict(self):
        return {
            "id":    self.pk,
            "name":  self.name,
            "email": self.email,
        }


class AuthToken(models.Model):
    """Token de sessão gerado no login."""

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tokens")
    token      = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate(cls, user):
        tok = secrets.token_hex(32)
        return cls.objects.create(user=user, token=tok)

    def __str__(self):
        return f"Token({self.user.email})"


class FinancialProfile(models.Model):
    """Perfil financeiro do cliente — limites e flags de alteração."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Limite PIX (pode ser alterado livremente pelo cliente)
    pix_limit        = models.DecimalField(max_digits=12, decimal_places=2, default=1000.00)

    # Limite cartão de crédito — só pode ser alterado UMA vez pelo cliente
    # (depois disso o agente solicita análise de aumento)
    credit_limit         = models.DecimalField(max_digits=12, decimal_places=2, default=500.00)
    credit_limit_changed = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.email})"

    def to_dict(self):
        return {
            "pix_limit":            float(self.pix_limit),
            "credit_limit":         float(self.credit_limit),
            "credit_limit_changed": self.credit_limit_changed,
        }


class Investment(models.Model):
    """Produto de investimento na carteira do cliente."""

    TYPE_CHOICES = [
        ("tesouro_selic",    "Tesouro Selic"),
        ("tesouro_ipca",     "Tesouro IPCA+"),
        ("cdb",              "CDB"),
        ("lci",              "LCI"),
        ("lca",              "LCA"),
        ("fundo_renda_fixa", "Fundo Renda Fixa"),
        ("fundo_multimercado","Fundo Multimercado"),
        ("acoes",            "Ações"),
        ("outro",            "Outro"),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="investments")
    name         = models.CharField(max_length=120)
    type         = models.CharField(max_length=30, choices=TYPE_CHOICES, default="outro")
    balance      = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    # Valor que o agente vai adicionar (preenchido pelo agente via chat)
    pending_deposit = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    def to_dict(self):
        return {
            "id":              self.pk,
            "name":            self.name,
            "type":            self.type,
            "type_label":      self.get_type_display(),
            "balance":         float(self.balance),
            "pending_deposit": float(self.pending_deposit),
            "created_at":      self.created_at.isoformat(),
        }


class Case(models.Model):
    """Caso de atendimento gerado pelo agente de IA."""

    PRIORITY_CHOICES = [
        ("high",   "Alta"),
        ("medium", "Normal"),
        ("low",    "Baixa"),
    ]
    STATUS_CHOICES = [
        ("waiting", "Aguardando"),
        ("active",  "Em atendimento"),
        ("done",    "Concluído"),
    ]

    token       = models.CharField(max_length=20, unique=True)
    owner       = models.CharField(max_length=120, default="Cliente desta sessão")
    # Opcional: vincula o caso ao usuário autenticado
    user        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="cases")
    intent      = models.CharField(max_length=120)
    description = models.TextField()
    information = models.JSONField(default=list)
    actions     = models.TextField(blank=True)
    documents   = models.TextField(blank=True)
    reason      = models.TextField(blank=True)
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES,   default="waiting")
    notes       = models.TextField(blank=True)
    demo        = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.token} · {self.intent}"

    def to_dict(self):
        return {
            "id":          self.token,
            "owner":       self.owner,
            "intent":      self.intent,
            "description": self.description,
            "information": self.information,
            "actions":     self.actions,
            "documents":   self.documents,
            "reason":      self.reason,
            "priority":    self.priority,
            "status":      self.status,
            "notes":       self.notes,
            "demo":        self.demo,
            "ts":          self.created_at.isoformat(),
        }


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=80)
    history = models.JSONField(default=list)
    pending_case = models.JSONField(null=True, blank=True)
    case = models.ForeignKey(Case, null=True, blank=True, on_delete=models.SET_NULL)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "session_id"], name="unique_user_chat")]
