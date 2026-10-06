from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

import base64
import re
import unicodedata


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

flow = None


def get_authorization_url():
    global flow

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/oauth2callback",
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    return authorization_url, state


def finish_authorization(code):
    global flow

    if flow is None:
        raise Exception("Authorization flow was not started.")

    flow.fetch_token(code=code)

    credentials = flow.credentials

    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())

    return credentials


def get_gmail_service():
    from google.oauth2.credentials import Credentials

    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES,
    )

    return build("gmail", "v1", credentials=credentials)


def get_recent_emails():
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q='newer_than:30d (receipt OR "order confirmation" OR "order confirmed" OR "purchase confirmation" OR "order number" OR "order #" OR "thank you for your order") -category:promotions',
        maxResults=20,
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:
        # full includes the message body. metadata only stored headers,
        # which left emails.json without anything to extract.
        email = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full",
        ).execute()

        headers = email["payload"]["headers"]

        subject = ""
        sender = ""

        for header in headers:
            if header["name"] == "Subject":
                subject = header["value"]
            elif header["name"] == "From":
                sender = header["value"]

        emails.append(email)

    return emails


def get_email_text(email):
    headers = email["payload"]["headers"]

    subject = ""
    sender = ""

    for header in headers:
        if header["name"].lower() == "subject":
            subject = header["value"]
        elif header["name"].lower() == "from":
            sender = header["value"]

    def get_body(payload):
        data = payload.get("body", {}).get("data")

        if data:
            return base64.urlsafe_b64decode(data).decode(
                "utf-8", errors="ignore"
            )

        for part in payload.get("parts", []):
            body = get_body(part)
            if body and body.strip().lower() not in ["undefined", "null"]:
                return body

        return ""

    body = get_body(email["payload"])

    if "<html" in body.lower() or "<body" in body.lower():
        soup = BeautifulSoup(body, "html.parser")
        body = soup.get_text(separator=" ", strip=True)

    return {
        "subject": subject,
        "from": sender,
        "body": body,
    }


def get_pdf_text(email):
    """Read text from PDF attachments. Download from Gmail if the file is not in the message."""
    texts = []

    def walk(part):
        filename = part.get("filename") or ""
        mime = (part.get("mimeType") or "").lower()

        if mime == "application/pdf" or filename.lower().endswith(".pdf"):
            text = read_pdf(attachment_bytes(email, part))
            if text.strip():
                texts.append(text.strip())

        for child in part.get("parts") or []:
            walk(child)

    try:
        walk(email.get("payload") or {})
    except Exception as error:
        print(f"Could not read a PDF attachment: {error}")
        return ""

    return "\n".join(texts)


def attachment_bytes(email, part):
    body = part.get("body") or {}
    data = body.get("data")

    if data:
        return base64.urlsafe_b64decode(data)

    attachment_id = body.get("attachmentId")
    message_id = email.get("id")

    if not attachment_id or not message_id:
        return b""

    service = get_gmail_service()
    result = service.users().messages().attachments().get(
        userId="me",
        messageId=message_id,
        id=attachment_id,
    ).execute()

    data = result.get("data")
    if not data:
        return b""

    return base64.urlsafe_b64decode(data)


def read_pdf(data):
    if not data:
        return ""

    from io import BytesIO
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages)


if __name__ == "__main__":
    import json

    emails = get_recent_emails()

    with open("emails.json", "w") as f:
        json.dump(emails, f, indent=2)

    print("Saved emails to emails.json")