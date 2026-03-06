"""Slack Web API client with retries and failure logging."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import SlackOrgConfig


SLACK_API_BASE = "https://slack.com/api"


class SlackApiError(RuntimeError):
    """Raised when a Slack API call fails after retries."""


class SlackApiClient:
    """Minimal Slack Web API wrapper based on stdlib HTTP calls."""

    def __init__(self, config: SlackOrgConfig):
        self.config = config
        self.config.ensure_parent_dirs()

    def _http_post_json(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{SLACK_API_BASE}/{method}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        req = Request(url=url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _record_failure(
        self,
        method: str,
        payload: Dict[str, Any],
        reason: str,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "reason": reason,
            "payload_preview": {
                "channel": payload.get("channel"),
                "name": payload.get("name"),
                "thread_ts": payload.get("thread_ts"),
                "text_preview": (payload.get("text", "") or "")[:120],
            },
            "response": response or {},
        }
        with self.config.failure_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _backoff_seconds(self, attempt: int) -> float:
        return self.config.base_backoff_seconds * (2**attempt) + random.uniform(0.0, 0.35)

    def call(
        self,
        method: str,
        payload: Optional[Dict[str, Any]] = None,
        notify_errors_channel: bool = True,
    ) -> Dict[str, Any]:
        payload = payload or {}
        if self.config.dry_run:
            return {"ok": True, "dry_run": True, "method": method, "payload": payload}
        if not self.config.bot_token:
            raise SlackApiError("Missing SLACK_BOT_TOKEN")

        last_reason = "unknown_error"
        last_response: Dict[str, Any] = {}
        for attempt in range(self.config.max_retries):
            try:
                response = self._http_post_json(method=method, payload=payload)
            except HTTPError as exc:
                last_reason = f"http_error:{exc.code}"
                retry_after = (exc.headers or {}).get("Retry-After", "")
                sleep_for = float(retry_after) if retry_after else self._backoff_seconds(attempt)
                time.sleep(sleep_for)
                continue
            except URLError as exc:
                last_reason = f"url_error:{exc.reason}"
                time.sleep(self._backoff_seconds(attempt))
                continue
            except Exception as exc:  # noqa: BLE001
                last_reason = f"exception:{exc}"
                time.sleep(self._backoff_seconds(attempt))
                continue

            last_response = response
            if response.get("ok"):
                return response

            slack_error = str(response.get("error", "unknown_error"))
            last_reason = slack_error

            if slack_error in {
                "ratelimited",
                "internal_error",
                "fatal_error",
                "request_timeout",
                "service_unavailable",
            }:
                time.sleep(self._backoff_seconds(attempt))
                continue
            break

        self._record_failure(method=method, payload=payload, reason=last_reason, response=last_response)
        if notify_errors_channel and method != "chat.postMessage":
            self._post_failure_to_errors_channel(method=method, reason=last_reason)
        raise SlackApiError(f"Slack API call failed for {method}: {last_reason}")

    def _post_failure_to_errors_channel(self, method: str, reason: str) -> None:
        # Local import avoids cyclic deps during bootstrap.
        from .channel_registry import ChannelRegistry

        registry = ChannelRegistry(
            channel_map_path=self.config.channel_map_path,
            registry_path=self.config.channel_registry_path,
        )
        errors_channel_id = registry.get_channel_id("shared_ops.errors") or registry.get_channel_id(
            self.config.errors_channel_name
        )
        if not errors_channel_id:
            return
        text = (
            "[SLACK API FAILURE]\n"
            f"Method: {method}\n"
            f"Reason: {reason}\n"
            f"Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}"
        )
        try:
            self.call(
                "chat.postMessage",
                {"channel": errors_channel_id, "text": text},
                notify_errors_channel=False,
            )
        except Exception:  # noqa: BLE001
            return

    def chat_post_message(self, channel: str, text: str, thread_ts: str = "") -> Dict[str, Any]:
        payload: Dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        return self.call("chat.postMessage", payload)

    def conversations_create(self, name: str, is_private: bool = False) -> Dict[str, Any]:
        return self.call("conversations.create", {"name": name, "is_private": is_private})

    def conversations_list(
        self,
        cursor: str = "",
        limit: int = 1000,
        types: str = "public_channel,private_channel",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "exclude_archived": True,
            "limit": limit,
            "types": types,
        }
        if cursor:
            payload["cursor"] = cursor
        return self.call("conversations.list", payload)
