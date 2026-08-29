from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from core.question_dump import parse_question_dump


class ParseQuestionDumpTests(TestCase):
    def test_parse_pg_dump_column_inserts(self):
        with TemporaryDirectory() as directory:
            dump_path = Path(directory) / "core_question.sql"
            dump_path.write_text(
                "\n".join(
                    [
                        "-- PostgreSQL database dump",
                        "INSERT INTO public.core_question (id, number, title, sociocultural_location, primary_power_perspective, secondary_power_perspective, secondary_demographic_type, secondary_demographic_choice) VALUES (1, 1, 'I don''t know yet.', 'Religion', 'Sensitivity', NULL, NULL, NULL);",
                        "INSERT INTO public.core_question (id, number, title, sociocultural_location, primary_power_perspective, secondary_power_perspective, secondary_demographic_type, secondary_demographic_choice) VALUES (2, 2, 'Many paths…maybe.', 'Religion', 'Leveraged', 'Oneness', 'religion', 'Agnostic');",
                    ]
                ),
                encoding="utf-8",
            )

            rows = parse_question_dump(dump_path)

        self.assertEqual(2, len(rows))
        self.assertEqual("I don't know yet.", rows[0]["title"])
        self.assertIsNone(rows[0]["secondary_power_perspective"])
        self.assertEqual("Many paths…maybe.", rows[1]["title"])
        self.assertEqual("Oneness", rows[1]["secondary_power_perspective"])
