# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gmail_quickstart]
import os.path
import base64
import time
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def create_draft(service, user_id, to_addr, subject, body_text, thread_id=None):
  """Create a draft message."""
  message = MIMEText(body_text)
  message["to"] = to_addr
  message["from"] = user_id
  message["subject"] = subject
  encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
  body = {"message": {"raw": encoded}}
  if thread_id:
    body["message"]["threadId"] = thread_id
  return service.users().drafts().create(userId=user_id, body=body).execute()


def check_unread_and_draft(service):
  """Poll unread messages every 10 minutes and create a draft reply."""
  while True:
    results = service.users().messages().list(
        userId="me", labelIds=["UNREAD"], maxResults=10
    ).execute()
    messages = results.get("messages", [])
    for msg_meta in messages:
      msg = service.users().messages().get(
          userId="me",
          id=msg_meta["id"],
          format="metadata",
          metadataHeaders=["From", "Subject"],
      ).execute()
      headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
      sender = headers.get("From", "")
      subject = headers.get("Subject", "")
      create_draft(
          service,
          "me",
          sender,
          f"Re: {subject}",
          "Thank you for your email.",
          thread_id=msg.get("threadId"),
      )
    time.sleep(600)


def main():
  """Check unread messages and draft a response every 10 minutes."""
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("gmail", "v1", credentials=creds)
    check_unread_and_draft(service)
  except HttpError as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()
# [END gmail_quickstart]