import base64
import sys
import types
import unittest
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

# Provide stub modules for Google APIs when the real packages are unavailable.
if "googleapiclient.discovery" not in sys.modules:
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.Resource = MagicMock()
    discovery.build = MagicMock()
    sys.modules["googleapiclient.discovery"] = discovery

if "googleapiclient.errors" not in sys.modules:
    errors = types.ModuleType("googleapiclient.errors")

    class HttpError(Exception):
        pass

    errors.HttpError = HttpError
    sys.modules["googleapiclient.errors"] = errors

if "google.auth.transport.requests" not in sys.modules:
    transport = types.ModuleType("google.auth.transport.requests")
    transport.Request = MagicMock()
    sys.modules["google.auth.transport.requests"] = transport

if "google.oauth2.credentials" not in sys.modules:
    credentials = types.ModuleType("google.oauth2.credentials")
    credentials.Credentials = MagicMock()
    sys.modules["google.oauth2.credentials"] = credentials

if "google_auth_oauthlib.flow" not in sys.modules:
    flow = types.ModuleType("google_auth_oauthlib.flow")
    flow.InstalledAppFlow = MagicMock()
    sys.modules["google_auth_oauthlib.flow"] = flow

if "openai" not in sys.modules:
    openai_mod = types.ModuleType("openai")
    openai_mod.OpenAI = MagicMock()
    sys.modules["openai"] = openai_mod

import mail


class TestCreateDraft(unittest.TestCase):
    def test_create_draft_constructs_body(self):
        service = MagicMock()
        create_mock = service.users.return_value.drafts.return_value.create
        execute_mock = create_mock.return_value.execute
        execute_mock.return_value = {"id": "draft1"}

        result = mail.create_draft(
            service,
            "me",
            "to@example.com",
            "Hello",
            "Body",
            thread_id="t123",
        )

        msg = MIMEText("Body")
        msg["to"] = "to@example.com"
        msg["from"] = "me"
        msg["subject"] = "Hello"
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        expected_body = {"message": {"raw": encoded, "threadId": "t123"}}

        create_mock.assert_called_once_with(userId="me", body=expected_body)
        execute_mock.assert_called_once_with()
        self.assertEqual(result, {"id": "draft1"})


class TestGenerateReply(unittest.TestCase):
    @patch("openai.OpenAI")
    def test_generate_reply_uses_client(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        response_mock = MagicMock()
        response_mock.choices = [MagicMock(message=MagicMock(content="Hi"))]
        mock_client.chat.completions.create.return_value = response_mock

        result = mail.generate_reply("sender@example.com", "Test")

        mock_openai.assert_called_once_with()
        mock_client.chat.completions.create.assert_called_once()
        self.assertEqual(result, "Hi")

    def test_generate_reply_without_openai(self):
        with patch.dict("sys.modules", {"openai": None}):
            result = mail.generate_reply("sender@example.com", "Test")
        self.assertEqual(result, "Thank you for your email.")


class TestCheckUnreadAndDraft(unittest.TestCase):
    @patch("mail.time.sleep", side_effect=StopIteration)
    @patch("mail.create_draft")
    @patch("mail.generate_reply", return_value="AI reply")
    def test_check_unread_and_draft(self, mock_generate_reply, mock_create_draft, mock_sleep):
        service = MagicMock()
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "m1"}]
        }
        service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test"},
                ]
            },
            "threadId": "t1",
        }

        with self.assertRaises(StopIteration):
            mail.check_unread_and_draft(service)

        service.users.return_value.messages.return_value.list.assert_called_once_with(
            userId="me", labelIds=["UNREAD"], maxResults=10
        )
        mock_generate_reply.assert_called_once_with("sender@example.com", "Test")
        mock_create_draft.assert_called_once_with(
            service,
            "me",
            "sender@example.com",
            "Re: Test",
            "AI reply",
            thread_id="t1",
        )


if __name__ == "__main__":
    unittest.main()
