from __future__ import annotations

import argparse
import json
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def _default_client_secret() -> Path:
    return Path(__file__).resolve().parent / "secrets" / "google_client_secret.json"


def _default_token_path() -> Path:
    return Path(__file__).resolve().parent / "secrets" / "google_docs_token.json"


def _fallback_redirect_uri() -> str:
    return "http://localhost:8765/"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Google Docs OAuth token for the XLM bot")
    parser.add_argument("--client-secret", default=str(_default_client_secret()))
    parser.add_argument("--token-file", default=str(_default_token_path()))
    parser.add_argument("--redirect-uri", default="")
    args = parser.parse_args()

    client_secret = Path(args.client_secret).expanduser()
    token_file = Path(args.token_file).expanduser()
    if not client_secret.exists():
        print(f"Missing Google client secret: {client_secret}")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception as exc:
        print(f"google-auth-oauthlib unavailable: {exc}")
        return 1

    redirect_uri = str(args.redirect_uri or "").strip()
    if not redirect_uri:
        try:
            payload = json.loads(client_secret.read_text(encoding="utf-8"))
            section = payload.get("installed") or payload.get("web") or {}
            redirects = section.get("redirect_uris") or []
            if redirects:
                redirect_uri = str(redirects[0]).strip()
        except Exception:
            redirect_uri = ""
    if not redirect_uri:
        redirect_uri = _fallback_redirect_uri()
        print(
            "No redirect URI found in client secret. "
            f"Using fallback {redirect_uri}. "
            "This URI must be added to the OAuth client in Google Cloud Console first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    print(f"Using redirect URI: {redirect_uri}")
    print("Open this URL in a browser, complete consent, and paste the redirected URL here:")
    print(auth_url)
    redirected = input("Redirected URL: ").strip()
    if not redirected:
        print("No redirected URL provided.")
        return 1

    flow.fetch_token(authorization_response=redirected)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(flow.credentials.to_json(), encoding="utf-8")
    print(f"Saved token to {token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
