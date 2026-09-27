import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.models.telemetry import Telemetry
from app.models.vehicle import Vehicle


logger = logging.getLogger(__name__)


def send_route_deviation_alert(
    *,
    trip_id: int,
    vehicle: Vehicle,
    telemetry: Telemetry,
    distance_meters: float,
    threshold_meters: float,
    route_filename: str,
) -> bool:
    if not settings.email_enabled:
        logger.info("Route deviation email disabled for trip %s", trip_id)
        return False
    if not all((settings.smtp_host, settings.smtp_from_email, settings.route_alert_recipient_email)):
        logger.error("Route deviation email is enabled but SMTP settings are incomplete")
        return False

    message = EmailMessage()
    message["Subject"] = f"Route deviation alert - Trip #{trip_id}"
    message["From"] = settings.smtp_from_email
    message["To"] = settings.route_alert_recipient_email
    message.set_content(
        "Route deviation detected.\n\n"
        f"Trip ID: {trip_id}\n"
        f"Vehicle: {vehicle.name} ({vehicle.device_id})\n"
        f"Detected at: {telemetry.recorded_at.isoformat()}\n"
        f"Latitude: {telemetry.latitude}\n"
        f"Longitude: {telemetry.longitude}\n"
        f"Distance from planned route: {distance_meters:.1f} meters\n"
        f"Configured threshold: {threshold_meters:.1f} meters\n"
        f"Planned route file: {route_filename}\n"
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls(context=context)
                smtp.ehlo()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
        logger.info("Route deviation email sent for trip %s", trip_id)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Route deviation email failed for trip %s", trip_id)
        return False