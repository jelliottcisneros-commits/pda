import tempfile

from django.core.files.storage import FileSystemStorage
from django.test import TestCase

from core.models import (
    AccessCode,
    Class_Score,
    CoreGroupuser,
    Culture_Score,
    Disability_Score,
    Gender_Score,
    Group,
    Race_Score,
    Religion_Score,
    Score,
    Sexual_Orientation_Score,
)
from core.tests.utils import create_assessment, create_user
from core.utilities import group_result


class GroupPdfTests(TestCase):
    def test_group_result_creates_named_pdf(self):
        with tempfile.TemporaryDirectory() as media_root:
            pdf_field = Group._meta.get_field("PDF")
            original_storage = pdf_field.storage
            pdf_field.storage = FileSystemStorage(
                location=media_root,
                base_url="/media/",
            )

            try:
                accesscode = AccessCode.objects.create(
                    name="Local Group Test",
                    code="!PDFTEST",
                    uses_left=1,
                )
                user = create_user()
                assessment = create_assessment(user)

                CoreGroupuser.objects.create(
                    user=user,
                    accesscode=accesscode,
                    assessment=assessment,
                )

                score = Score.objects.create(
                    assessment=assessment,
                    sensitivity_total=10,
                    oneness_total=20,
                    strength_total=30,
                    appreciation_total=40,
                    leveraged_total=50,
                )

                for subscore_model in (
                    Religion_Score,
                    Disability_Score,
                    Culture_Score,
                    Gender_Score,
                    Race_Score,
                    Class_Score,
                    Sexual_Orientation_Score,
                ):
                    subscore_model.objects.create(
                        score=score,
                        sensitivity=1,
                        oneness=2,
                        strength=3,
                        appreciation=4,
                        leveraged=5,
                    )

                group_result(assessment.id)

                group = Group.objects.get(accesscode=accesscode)

                self.assertEqual(
                    group.PDF.name,
                    "group_pdfs/Local_Group_Test_1_group_results.pdf",
                )
                self.assertTrue(
                    group.PDF.storage.exists(group.PDF.name)
                )
                self.assertGreater(group.PDF.size, 0)

            finally:
                pdf_field.storage = original_storage
