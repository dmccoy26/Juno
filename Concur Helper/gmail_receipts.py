"""Fetch messages from a Gmail search and run the receipt matcher."""

import argparse
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from receipt_helper import write_plan


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service(client, token):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = Credentials.from_authorized_user_file(token, SCOPES) if token.exists() else None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            credentials = InstalledAppFlow.from_client_secrets_file(
                client, SCOPES
            ).run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(token, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(credentials.to_json())
    return build("gmail", "v1", credentials=credentials)


def fetch_messages(messages, query, directory):
    page = None
    while True:
        response = messages.list(userId="me", q=query, pageToken=page).execute()
        for record in response.get("messages", []):
            message_id = record["id"]
            if not message_id.isalnum():
                raise ValueError("Unexpected Gmail message ID")
            raw = messages.get(userId="me", id=message_id, format="raw").execute()["raw"]
            payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            (directory / (message_id + ".eml")).write_bytes(payload)
        page = response.get("nextPageToken")
        if not page:
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Gmail search expression")
    parser.add_argument("expenses", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--client", type=Path, default=Path("local/gmail-client.json"))
    parser.add_argument("--token", type=Path, default=Path("local/gmail-token.json"))
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("Enter a Gmail search query")
    messages = gmail_service(args.client, args.token).users().messages()
    with TemporaryDirectory() as temp:
        mailbox = Path(temp)
        fetch_messages(messages, args.query, mailbox)
        print(write_plan(mailbox, args.expenses, args.output, source_prefix="gmail:"))


if __name__ == "__main__":
    main()
