"""Multi-channel notification helpers (Slack, Teams, etc.)."""
from __future__ import annotations

from typing import Dict, Optional

import httpx

from ..config import get_settings


def _post_json(url: str, payload: Dict) -> Dict:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
    return {'success': True, 'status_code': response.status_code}


def send_slack_message(message: str, *, webhook_url: Optional[str] = None) -> Dict:
    settings = get_settings()
    url = webhook_url or settings.slack_webhook_url
    if not url:
        return {'success': False, 'message': 'Slack webhook not configured'}
    try:
        return _post_json(url, {"text": message})
    except httpx.HTTPError as exc:
        return {'success': False, 'message': str(exc)}


def send_teams_message(message: str, *, webhook_url: Optional[str] = None) -> Dict:
    settings = get_settings()
    url = webhook_url or settings.teams_webhook_url
    if not url:
        return {'success': False, 'message': 'Teams webhook not configured'}
    try:
        return _post_json(url, {"text": message})
    except httpx.HTTPError as exc:
        return {'success': False, 'message': str(exc)}


def format_alert_markdown(alert: Dict) -> str:
    """Generate a concise markdown summary for chat tools."""
    title = alert.get('message') or alert.get('ai_recommendation') or 'Inventory Alert'
    sku = alert.get('sku', 'N/A')
    buffer_days = alert.get('buffer_days')
    severity = alert.get('severity', 'INFO')
    loss = alert.get('loss_per_day')
    recommended_qty = alert.get('recommended_quantity')

    lines = [f"[{severity}] {title}", f"SKU: {sku}"]
    if buffer_days is not None:
        lines.append(f"Buffer Days: {buffer_days}")
    if recommended_qty:
        lines.append(f"Recommended Qty: {recommended_qty}")
    if loss:
        lines.append(f"Loss/Day: ${loss:,.0f}")

    return "\n".join(lines)
