"""views_closeout -- admin endpoint for manual wire-receipt entry.

Path: POST /broker/api/wire-received/

Body (JSON or form):
    deal_id     -- UUID of the Deal
    amount      -- number, the wire amount in USD
    wire_date   -- ISO date "YYYY-MM-DD" or any datetime parseable string
    reference   -- optional, the bank reference / memo
    source      -- optional, "manual" | "csv" | "plaid", default "manual"
    agent       -- optional, agent name to stamp on DealEvent

Auth: staff_or_internal_required. Admin only -- this writes a CommissionRecord.

Returns JSON of services_closeout.reconcile_wire().
"""
from __future__ import annotations

import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from hive_dashboard.security import staff_or_internal_required

from .services_closeout import reconcile_wire


def _read_body(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


@csrf_exempt
@require_POST
@staff_or_internal_required
def api_wire_received(request):
    data = _read_body(request)
    deal_id = (data.get("deal_id") or "").strip()
    amount = data.get("amount")
    wire_date = (data.get("wire_date") or "").strip()
    reference = (data.get("reference") or "").strip()
    source = (data.get("source") or "manual").strip()
    agent = (data.get("agent") or "Backend Hand").strip()

    if not deal_id or amount in (None, "") or not wire_date:
        return HttpResponseBadRequest(
            json.dumps({"ok": False, "error": "deal_id, amount, wire_date are required"}),
            content_type="application/json",
        )

    res = reconcile_wire(
        deal_id, amount, wire_date,
        agent=agent, reference=reference, source=source,
    )
    status = 200 if res.get("ok") else 404
    return JsonResponse(res, status=status)
