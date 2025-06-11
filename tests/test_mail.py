import base64
import unittest
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

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


class TestCheckUnreadAndDraft(unittest.TestCase):
    @patch("mail.time.sleep", side_effect=StopIteration)
    @patch("mail.create_draft")
    def test_check_unread_and_draft(self, mock_create_draft, mock_sleep):
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
        mock_create_draft.assert_called_once_with(
            service,
            "me",
            "sender@example.com",
            "Re: Test",
            "Thank you for your email.",
            thread_id="t1",
        )


if __name__ == "__main__":
    unittest.main()
