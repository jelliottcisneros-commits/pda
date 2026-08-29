from django.conf import settings
from django.contrib.auth.models import User as AuthUser
from django.core.management.base import BaseCommand, CommandError

from core.models import AccessCode, POWER_PERSPECTIVES, Question, SOCIOCULTURAL_LOCATIONS


class Command(BaseCommand):
    help = "Seed local-only data so the legacy PDA app can be explored after a fresh migrate."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument("--access-code", default="LOCALTEST")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_local_data is only intended for DEBUG/local environments.")

        username = options["username"]
        password = options["password"]
        email = options["email"]
        access_code = options["access_code"]

        if not AuthUser.objects.filter(username=username).exists():
            AuthUser.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS("Created local superuser %s" % username))
        else:
            self.stdout.write("Local superuser %s already exists" % username)

        AccessCode.objects.get_or_create(
            code=access_code,
            defaults={"name": "Local test access", "uses_left": -1},
        )

        locations = [value for value, _label in SOCIOCULTURAL_LOCATIONS]
        perspectives = [value for value, _label in POWER_PERSPECTIVES]

        created = 0
        for number in range(1, 71):
            _question, was_created = Question.objects.get_or_create(
                number=number,
                defaults={
                    "title": "Local placeholder statement %d" % number,
                    "sociocultural_location": locations[(number - 1) % len(locations)],
                    "primary_power_perspective": perspectives[(number - 1) % len(perspectives)],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded local data: admin=%s, access_code=%s, questions_created=%d, total_questions=%d"
                % (username, access_code, created, Question.objects.count())
            )
        )
