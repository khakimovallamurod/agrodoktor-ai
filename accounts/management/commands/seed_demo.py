"""
Management command to create (or update) the demo user from .env credentials.
Idempotent: safe to run on every deploy. Does not create any sample scans.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the demo user using DEMO_USERNAME / DEMO_PASSWORD from .env."

    def handle(self, *args, **options):
        username = settings.DEMO_USERNAME
        password = settings.DEMO_PASSWORD
        if not password:
            raise CommandError(".env faylida DEMO_PASSWORD ko'rsatilmagan.")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": settings.DEMO_FIRST_NAME,
                "last_name": settings.DEMO_LAST_NAME,
                "is_active": True,
            },
        )
        user.set_password(password)
        user.save()

        action = "yaratildi" if created else "yangilandi"
        self.stdout.write(self.style.SUCCESS(f"Demo foydalanuvchi ({username}) {action}."))
