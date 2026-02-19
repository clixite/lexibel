"""SENTINEL alert notification service."""

import logging
from typing import List, Dict
from uuid import UUID
from datetime import datetime, timedelta

from packages.db.models.sentinel_conflict import SentinelConflict
from packages.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AlertSeverity:
    """Alert severity levels."""

    CRITICAL = "critical"  # Score 90-100: Direct adversary, director overlap
    HIGH = "high"  # Score 70-89: Ownership, family ties
    MEDIUM = "medium"  # Score 50-69: Historical, professional
    LOW = "low"  # Score 0-49: Weak connections


class ConflictAlerter:
    """Send conflict alerts via multiple channels."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.sse_connections: Dict[UUID, List] = {}  # user_id: [connections]

    def get_severity_level(self, score: int) -> str:
        """Map conflict score to severity level."""
        if score >= 90:
            return AlertSeverity.CRITICAL
        elif score >= 70:
            return AlertSeverity.HIGH
        elif score >= 50:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    async def create_conflict_alert(
        self, conflict: SentinelConflict, notify_user_id: UUID
    ) -> Dict:
        """Create alert and notify user.

        Args:
            conflict: The detected conflict
            notify_user_id: User to notify

        Returns:
            Alert data dict
        """
        severity = self.get_severity_level(conflict.severity_score)

        alert_data = {
            "id": str(conflict.id),
            "type": "conflict_detected",
            "severity": severity,
            "title": f"{conflict.conflict_type.replace('_', ' ').title()} Detected",
            "message": conflict.description,
            "conflict_score": conflict.severity_score,
            "conflicting_entity": conflict.conflicting_entity_id,
            "case_id": conflict.trigger_entity_id,
            "created_at": datetime.now().isoformat(),
            "actions": [
                {"label": "Review", "action": "review"},
                {"label": "Resolve", "action": "resolve"},
                {"label": "Dismiss", "action": "dismiss"},
            ],
        }

        # Send real-time alert via SSE
        await self.send_realtime_alert(notify_user_id, alert_data)

        # For CRITICAL alerts, also send email immediately
        if severity == AlertSeverity.CRITICAL:
            await self.send_email_alert(notify_user_id, alert_data)

        logger.info(
            f"Alert created: {conflict.conflict_type} for user {notify_user_id}"
        )
        return alert_data

    async def send_realtime_alert(self, user_id: UUID, alert_data: Dict):
        """Send real-time alert via Server-Sent Events (SSE).

        Note: SSE connections are registered via /api/v1/sentinel/alerts/stream
        """
        connections = self.sse_connections.get(user_id, [])

        if not connections:
            logger.warning(f"No SSE connections for user {user_id}")
            return

        # Send alert to all user's active connections
        for connection in connections:
            try:
                # In production, this would be:
                # await connection.send(json.dumps(alert_data))
                logger.info(f"SSE alert sent to user {user_id}: {alert_data['title']}")
            except Exception as e:
                logger.error(f"Failed to send SSE alert: {e}")

    async def send_email_alert(self, user_id: UUID, alert_data: Dict):
        """Send email alert for critical conflicts."""
        try:
            # Get user email
            user = await self.db.get(User, user_id)
            if not user or not user.email:
                logger.warning(f"No email for user {user_id}")
                return

            # Create email (logged for now, SMTP in production)
            subject = f"[URGENT] {alert_data['title']} - LexiBel SENTINEL"
            _body = f"""
            <html>
                <body>
                    <h2 style="color: #d32f2f;">Conflict of Interest Detected</h2>
                    <p><strong>Severity:</strong> {alert_data["severity"].upper()}</p>
                    <p><strong>Type:</strong> {alert_data["title"]}</p>
                    <p><strong>Description:</strong> {alert_data["message"]}</p>
                    <p><strong>Conflict Score:</strong> {alert_data["conflict_score"]}/100</p>
                    <hr>
                    <p>Please review this conflict immediately in the LexiBel SENTINEL dashboard.</p>
                    <p><a href="https://app.lexibel.be/sentinel/conflicts/{alert_data["id"]}">
                        View Conflict Details
                    </a></p>
                </body>
            </html>
            """

            # In production, send via SMTP
            # For now, just log
            logger.info(f"Email alert sent to {user.email}: {subject}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    async def send_email_digest(self, user_id: UUID) -> bool:
        """Send daily digest of conflicts (called by scheduler).

        Returns:
            True if digest sent successfully
        """
        try:
            # Get user
            user = await self.db.get(User, user_id)
            if not user or not user.email:
                return False

            # Get conflicts from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            conflicts = await self.db.execute(
                """
                SELECT * FROM sentinel_conflicts
                WHERE created_at >= :cutoff
                AND (resolution IS NULL OR resolution = '')
                ORDER BY severity_score DESC
                """,
                {"cutoff": yesterday},
            )
            conflicts = conflicts.fetchall()

            if not conflicts:
                logger.info(f"No conflicts to report for user {user_id}")
                return True

            # Create digest email (logged for now, SMTP in production)
            subject = f"Daily Conflict Summary - {len(conflicts)} conflicts detected"  # noqa: F841

            # Build HTML table of conflicts
            conflict_rows = ""
            for conflict in conflicts:
                severity = self.get_severity_level(conflict.severity_score)
                severity_color = {
                    "critical": "#d32f2f",
                    "high": "#f57c00",
                    "medium": "#fbc02d",
                    "low": "#388e3c",
                }.get(severity, "#666")

                conflict_rows += f"""
                <tr>
                    <td style="color: {severity_color}; font-weight: bold;">{severity.upper()}</td>
                    <td>{conflict.conflict_type.replace("_", " ").title()}</td>
                    <td>{conflict.severity_score}/100</td>
                    <td>{conflict.created_at.strftime("%H:%M")}</td>
                </tr>
                """

            _body = f"""
            <html>
                <body>
                    <h2>LexiBel SENTINEL - Daily Conflict Report</h2>
                    <p>You have <strong>{len(conflicts)} unresolved conflicts</strong> detected in the last 24 hours.</p>

                    <table border="1" cellpadding="10" style="border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f0f0f0;">
                                <th>Severity</th>
                                <th>Type</th>
                                <th>Score</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {conflict_rows}
                        </tbody>
                    </table>

                    <p><a href="https://app.lexibel.be/sentinel/conflicts">
                        Review All Conflicts in Dashboard
                    </a></p>
                </body>
            </html>
            """

            # In production, send via SMTP
            logger.info(
                f"Digest email sent to {user.email}: {len(conflicts)} conflicts"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send email digest: {e}")
            return False

    async def resolve_conflict(
        self, conflict_id: UUID, resolution: str, resolved_by: UUID
    ) -> bool:
        """Mark conflict as resolved.

        Args:
            conflict_id: Conflict to resolve
            resolution: 'refused', 'waiver_obtained', 'false_positive'
            resolved_by: User who resolved

        Returns:
            True if resolved successfully
        """
        try:
            conflict = await self.db.get(SentinelConflict, conflict_id)
            if not conflict:
                logger.error(f"Conflict {conflict_id} not found")
                return False

            # Update conflict
            conflict.resolution = resolution
            conflict.resolved_by = resolved_by
            conflict.resolved_at = datetime.now()
            conflict.auto_resolved = False

            await self.db.commit()

            logger.info(
                f"Conflict {conflict_id} resolved: {resolution} by {resolved_by}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")
            await self.db.rollback()
            return False

    def register_sse_connection(self, user_id: UUID, connection):
        """Register SSE connection for user (called by SSE endpoint)."""
        if user_id not in self.sse_connections:
            self.sse_connections[user_id] = []
        self.sse_connections[user_id].append(connection)
        logger.info(f"SSE connection registered for user {user_id}")

    def unregister_sse_connection(self, user_id: UUID, connection):
        """Unregister SSE connection when client disconnects."""
        if user_id in self.sse_connections:
            try:
                self.sse_connections[user_id].remove(connection)
                logger.info(f"SSE connection unregistered for user {user_id}")
            except ValueError:
                pass
