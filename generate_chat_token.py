"""
Run once locally to authorise cloud@ascotwm.com for Google Chat access.
Stores the resulting token in Secret Manager as 'chat-token'.

Usage:
    python generate_chat_token.py path/to/client_secret.json
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from google.cloud import secretmanager

SCOPES = [
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
]

PROJECT_ID = "chimera-v4"
SECRET_ID = "chat-token"


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_chat_token.py path/to/client_secret.json")
        sys.exit(1)

    client_secrets_file = sys.argv[1]

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=8085, login_hint="cloud@ascotwm.com")

    token_data = json.dumps({
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    })

    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}"
    secret_name = f"{parent}/secrets/{SECRET_ID}"

    # Create secret if it doesn't exist
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": SECRET_ID,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Created secret '{SECRET_ID}'")
    except Exception:
        print(f"Secret '{SECRET_ID}' already exists, adding new version")

    # Add the token as a new version
    client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {"data": token_data.encode("utf-8")},
        }
    )
    print(f"Token stored in Secret Manager as '{SECRET_ID}' — done!")


if __name__ == "__main__":
    main()
