from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Question
from core.question_dump import parse_question_dump


class Command(BaseCommand):
    help = "Import core_question rows from a pg_dump --column-inserts export."

    def add_arguments(self, parser):
        parser.add_argument("dump_path", help="Path to a PostgreSQL dump containing core_question INSERT rows.")
        parser.add_argument(
            "--expected-count",
            type=int,
            default=70,
            help="Expected number of imported statements. Use 0 to skip this check.",
        )
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="Allow import when DEBUG is false. Intended only for carefully planned production maintenance.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate the dump without saving changes.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError("Refusing to import questions outside DEBUG without --allow-production.")

        dump_path = Path(options["dump_path"]).expanduser()
        if not dump_path.exists():
            raise CommandError("Dump file does not exist: %s" % dump_path)

        try:
            rows = parse_question_dump(dump_path)
        except ValueError as error:
            raise CommandError(str(error))
        expected_count = options["expected_count"]
        if expected_count and len(rows) != expected_count:
            raise CommandError("Expected %d rows, found %d." % (expected_count, len(rows)))

        numbers = sorted(row["number"] for row in rows)
        if len(numbers) != len(set(numbers)):
            raise CommandError("Dump contains duplicate question numbers.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Validated %d question rows from %s." % (len(rows), dump_path)))
            return

        with transaction.atomic():
            for row in rows:
                Question.objects.update_or_create(
                    number=row["number"],
                    defaults={
                        "title": row["title"],
                        "sociocultural_location": row["sociocultural_location"],
                        "primary_power_perspective": row["primary_power_perspective"],
                        "secondary_power_perspective": row["secondary_power_perspective"],
                        "secondary_demographic_type": row["secondary_demographic_type"],
                        "secondary_demographic_choice": row["secondary_demographic_choice"],
                    },
                )

        self.stdout.write(self.style.SUCCESS("Imported %d question rows from %s." % (len(rows), dump_path)))
