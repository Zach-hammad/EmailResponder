import os.path
import base64
import time
import argparse
import logging
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def create_draft(
    service: Resource,
    user_id: str,
    to_addr: str,
    subject: str,
    body_text: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a draft message."""
    message = MIMEText(body_text)
    message["to"] = to_addr
    message["from"] = user_id
    message["subject"] = subject
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body: Dict[str, Any] = {"message": {"raw": encoded}}
    if thread_id:
        body["message"]["threadId"] = thread_id
    return service.users().drafts().create(userId=user_id, body=body).execute()


def generate_reply(sender: str, subject: str) -> str:
    """Generate a reply body using the OpenAI API."""
    try:
        import openai
        client = openai.OpenAI()
    except Exception as exc:  # pragma: no cover - only triggered if openai missing
        logging.error("Failed to import openai: %s", exc)
        return "Thank you for your email."

    prompt = (
        f"Write a short polite reply to an email from {sender} with subject \"{subject}\"."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logging.error("Failed to generate reply: %s", exc)
        return "Thank you for your email."


def check_unread_and_draft(service: Resource, interval: int = 600, max_results: int = 10) -> None:
    """Poll unread messages and create draft replies."""
    while True:
        try:
            results = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["UNREAD"], maxResults=max_results)
                .execute()
            )
            messages = results.get("messages", [])
            for msg_meta in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_meta["id"],
                        format="metadata",
                        metadataHeaders=["From", "Subject"],
                    )
                    .execute()
                )
                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                sender = headers.get("From", "")
                subject = headers.get("Subject", "")
                body = generate_reply(sender, subject)
                create_draft(
                    service,
                    "me",
                    sender,
                    f"Re: {subject}",
                    body,
                    thread_id=msg.get("threadId"),
                )
        except HttpError as error:
            logging.error("Failed to poll Gmail: %s", error)
        time.sleep(interval)


def main() -> None:
    """Check unread messages and draft a response."""
    parser = argparse.ArgumentParser(
        description="Check unread messages and draft a response"
    )
    parser.add_argument(
        "--interval", type=int, default=600, help="Polling interval in seconds"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum messages to fetch per poll",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    creds: Credentials | None = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        check_unread_and_draft(service, interval=args.interval, max_results=args.max_results)
    except HttpError as error:
        logging.error("An error occurred: %s", error)


if __name__ == "__main__":
    main()
