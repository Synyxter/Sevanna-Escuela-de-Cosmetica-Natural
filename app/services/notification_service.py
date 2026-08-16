"""Notification orchestration — schedules transactional emails.

Kept separate from business flows so that email delivery is a side effect that
never blocks or fails a payment/enrollment (Rule 10).
"""

from __future__ import annotations

from fastapi import BackgroundTasks

from app.models.course import Course
from app.models.user import User
from app.services import email_templates
from app.services.email_service import send_email_background


class NotificationService:
    @staticmethod
    def schedule_purchase_confirmation(
        background: BackgroundTasks, *, user: User, course: Course
    ) -> None:
        subject, html, text = email_templates.purchase_confirmation_email(
            full_name=user.full_name,
            course_title=course.title,
            modality=course.modality.value,
            whatsapp_url=course.whatsapp_group_url,
            google_meet_url=course.google_meet_url,
        )
        background.add_task(
            send_email_background,
            to=user.email,
            subject=subject,
            html_body=html,
            text_body=text,
            template="purchase_confirmation",
            related_entity_id=course.id,
        )
