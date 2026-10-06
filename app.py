from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from gmail import (
    get_authorization_url,
    finish_authorization,
    get_recent_emails,
)

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Shopping Agent is running!"}


@app.get("/authorize")
def authorize():
    authorization_url, state = get_authorization_url()
    return RedirectResponse(authorization_url)


@app.get("/oauth2callback")
def oauth2callback(code: str):
    finish_authorization(code)
    return {
        "message": "Gmail connected successfully!"
    }


@app.get("/emails")
def emails():
    return {
        "emails": get_recent_emails()
    }