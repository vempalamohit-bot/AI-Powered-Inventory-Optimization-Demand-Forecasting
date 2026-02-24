"""Background scheduler that distributes AI alerts across channels."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import SessionLocal
from ..database.models import NotificationLog
from ..models.ai_alert_system import AIAlertSystem
from . import email_service_sendgrid
from .notification_service import format_alert_markdown, send_slack_message, send_teams_message


class AlertScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self.settings = get_settings()
        self.last_run_at: datetime | None = None
        self.last_run_status: Dict | None = None

    async def start(self) -> None:
        if not self.settings.alert_scheduler_enabled:
            return
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            await self._run_once()
            await asyncio.sleep(self.settings.alert_scheduler_interval_seconds)

    async def _run_once(self) -> None:
        self.last_run_at = datetime.utcnow()
        db = SessionLocal()
        try:
            alerts = AIAlertSystem.generate_live_alerts(db, limit=50)
            stats = self._dispatch_alerts(db, alerts)
            self.last_run_status = {
                'alerts_considered': len(alerts),
                'dispatch_counts': stats,
                'timestamp': self.last_run_at.isoformat()
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            self.last_run_status = {'error': str(exc), 'timestamp': self.last_run_at.isoformat()}
        finally:
            db.close()

    def _dispatch_alerts(self, db: Session, alerts: List[Dict]) -> Dict[str, int]:
        counts = {'email': 0, 'slack': 0, 'teams': 0}
        for alert in alerts:
            alert_key = alert.get('alert_id') or f"alert::{alert.get('product_id')}"
            severity = (alert.get('severity') or 'INFO').upper()

            if alert.get('send_email') and not self._recently_sent(db, alert_key, 'EMAIL'):
                email_subject = alert.get('email_subject') or f"{severity} ALERT: {alert.get('product_name', 'Inventory')}"
                body = alert.get('natural_language_summary') or alert.get('ai_insight') or alert.get('message')
                if body:
                    email_result = email_service_sendgrid.send_custom_alert(
                        None,
                        email_subject,
                        body,
                        db=db,
                        alert_key=alert_key
                    )
                    if email_result.get('success'):
                        counts['email'] += 1

            if severity in {'CRITICAL', 'HIGH'}:
                markdown = format_alert_markdown(alert)
                if not self._recently_sent(db, alert_key, 'SLACK'):
                    result = send_slack_message(markdown)
                    email_service_sendgrid.log_notification(
                        db,
                        channel='SLACK',
                        subject=markdown.split('\n', 1)[0],
                        recipients=['slack_webhook'],
                        status='SENT' if result.get('success') else 'FAILED',
                        error_message=None if result.get('success') else result.get('message'),
                        payload={'alert_key': alert_key}
                    )
                    if result.get('success'):
                        counts['slack'] += 1
                if not self._recently_sent(db, alert_key, 'TEAMS'):
                    result = send_teams_message(markdown)
                    email_service_sendgrid.log_notification(
                        db,
                        channel='TEAMS',
                        subject=markdown.split('\n', 1)[0],
                        recipients=['teams_webhook'],
                        status='SENT' if result.get('success') else 'FAILED',
                        error_message=None if result.get('success') else result.get('message'),
                        payload={'alert_key': alert_key}
                    )
                    if result.get('success'):
                        counts['teams'] += 1
        return counts

    def _recently_sent(self, db: Session, alert_key: str, channel: str) -> bool:
        if not alert_key:
            return False
        window_start = datetime.utcnow() - timedelta(minutes=self.settings.alert_dedupe_window_minutes)
        exists = db.query(NotificationLog).filter(
            NotificationLog.alert_key == alert_key,
            NotificationLog.channel == channel,
            NotificationLog.status == 'SENT',
            NotificationLog.created_at >= window_start
        ).first()
        return exists is not None

    def status(self) -> Dict:
        return {
            'enabled': self.settings.alert_scheduler_enabled,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_run_status': self.last_run_status
        }


def get_alert_scheduler() -> AlertScheduler:
    return alert_scheduler


alert_scheduler = AlertScheduler()
