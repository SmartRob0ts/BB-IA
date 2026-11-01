import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from .models import User, AuthToken, Case, ChatSession
from .views import _parse_escalate
from .watsonx_service import ConfigurationError

PROPOSAL = {"intent": "Cartão", "description": "Cliente pede análise do cartão.",
            "information": ["Compra recusada"], "priority": "medium"}
RAW = 'Posso encaminhar.\n<!--ESCALATE-->\n```json\n' + json.dumps(PROPOSAL) + '\n```'

class ChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(name="Cliente", email="cliente@example.test", password="unused")
        self.other = User.objects.create(name="Outro", email="outro@example.test", password="unused")
        self.client.defaults["HTTP_AUTHORIZATION"] = "Token " + AuthToken.generate(self.user).token

    def post(self, **kwargs):
        return self.client.post("/api/chat/", data=json.dumps({"session_id": "test-session", **kwargs}), content_type="application/json")

    @patch("agent.watsonx_service.reply", return_value=RAW)
    def test_proposal_confirmation_and_retry(self, mock):
        response = self.post(message="Preciso de gerente")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["pending_confirmation"])
        self.assertFalse(Case.objects.exists())
        response = self.post(action="confirm_case")
        self.assertEqual(response.status_code, 200)
        token = response.json()["case"]["id"]
        self.assertEqual(self.post(action="confirm_case").json()["case"]["id"], token)
        self.assertEqual(Case.objects.count(), 1)
        self.assertEqual(Case.objects.get().user, self.user)
        self.assertEqual(mock.call_count, 1)

    @patch("agent.watsonx_service.reply", return_value=RAW)
    def test_cancel(self, mock):
        self.post(message="Gerente")
        self.assertEqual(self.post(action="cancel_case").status_code, 200)
        self.assertEqual(self.post(action="confirm_case").status_code, 409)
        self.assertFalse(Case.objects.exists())

    @patch("agent.watsonx_service.reply", side_effect=["Olá", "Como posso ajudar?"])
    def test_history_and_system_role(self, mock):
        self.post(message="Oi")
        self.post(message="Tenho uma dúvida")
        messages = mock.call_args.args[0]
        self.assertEqual([x["role"] for x in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[1]["content"], "Oi")

    @patch("agent.watsonx_service.reply", side_effect=ConfigurationError("Configure IBM"))
    def test_missing_config(self, mock):
        self.assertEqual(self.post(message="Olá").status_code, 503)
        self.assertEqual(ChatSession.objects.get().history, [])

    @patch("agent.watsonx_service.reply", side_effect=RuntimeError("secret-value"))
    def test_provider_failure_does_not_expose_details(self, mock):
        response = self.post(message="Olá")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-value", response.content.decode())

    def test_auth_and_validation(self):
        self.assertEqual(self.post(message=[]).status_code, 400)
        self.assertEqual(self.post(message="a" * 4001).status_code, 400)
        self.assertEqual(self.post(action="confirm_case").status_code, 409)
        self.client.defaults.clear()
        self.assertEqual(self.post(message="Olá").status_code, 401)
        self.assertEqual(self.client.get("/api/cases/").status_code, 401)

    def test_invalid_proposal(self):
        for value in ([], {**PROPOSAL, "priority": "critical"}, {**PROPOSAL, "information": "not a list"}):
            text = '<!--ESCALATE-->\n```json\n' + json.dumps(value) + '\n```'
            self.assertIsNone(_parse_escalate(text)[1])

    @patch("agent.watsonx_service.reply", return_value=RAW)
    def test_reset_discards_pending(self, mock):
        self.post(message="Gerente")
        self.client.post("/api/chat/reset/", json.dumps({"session_id": "test-session"}), content_type="application/json")
        self.assertIsNone(ChatSession.objects.get().pending_case)
        self.assertEqual(self.post(action="confirm_case").status_code, 409)

    def test_access_and_manager_updates(self):
        own = Case.objects.create(token="AT-OWN", user=self.user, intent="Conta", description="Teste")
        Case.objects.create(token="AT-OTHER", user=self.other, intent="Conta", description="Outro")
        data = self.client.get("/api/cases/").json()
        self.assertEqual([x["id"] for x in data["cases"]], [own.token])
        self.assertFalse(data["can_manage"])
        self.assertEqual(self.client.get("/api/cases/AT-OTHER/").status_code, 404)
        response = self.client.patch("/api/cases/AT-OWN/", json.dumps({"status":"done"}), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        manager = User.objects.create(name="Gerente", email="gerente@example.test", password="unused", is_manager=True)
        self.client.defaults["HTTP_AUTHORIZATION"] = "Token " + AuthToken.generate(manager).token
        self.assertEqual(len(self.client.get("/api/cases/").json()["cases"]), 2)
        self.assertEqual(self.client.patch("/api/cases/AT-OWN/", json.dumps({"status":"invalid"}), content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch("/api/cases/AT-OWN/", json.dumps({"status":"done", "notes":"Concluído"}), content_type="application/json").status_code, 200)
        own.refresh_from_db()
        self.assertEqual(own.status, "done")


class AuthMigrationTests(TestCase):
    def test_legacy_password_upgrade_and_no_manager_self_registration(self):
        import hashlib
        from django.contrib.auth.hashers import check_password
        user = User.objects.create(name="Antigo", email="antigo@example.test", password=hashlib.sha256(b"senha-antiga").hexdigest())
        response = self.client.post("/api/auth/login/", json.dumps({"email":user.email,"password":"senha-antiga"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(check_password("senha-antiga", user.password))
        response = self.client.post("/api/auth/register/", json.dumps({"name":"Novo","email":"novo@example.test","password":"senha-nova","is_manager":True}), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="novo@example.test")
        self.assertFalse(user.is_manager)
        self.assertTrue(check_password("senha-nova", user.password))

class AdapterTests(TestCase):
    @override_settings(WATSONX_API_KEY="test", WATSONX_URL="https://example.test", WATSONX_PROJECT_ID="project", WATSONX_MODEL_ID="model")
    def test_sdk_request_and_response_mapping(self):
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock
        from .watsonx_service import reply
        sdk = ModuleType("ibm_watsonx_ai")
        sdk.Credentials = MagicMock()
        models = ModuleType("ibm_watsonx_ai.foundation_models")
        models.ModelInference = MagicMock()
        models.ModelInference.return_value.chat.return_value = {"choices":[{"message":{"content":"Olá"}}]}
        messages = [{"role":"system","content":"Instruções"},{"role":"user","content":"Oi"}]
        with patch.dict(sys.modules, {"ibm_watsonx_ai":sdk,"ibm_watsonx_ai.foundation_models":models}):
            self.assertEqual(reply(messages), "Olá")
        models.ModelInference.return_value.chat.assert_called_once_with(messages=messages)
        self.assertEqual(models.ModelInference.call_args.kwargs["project_id"], "project")
