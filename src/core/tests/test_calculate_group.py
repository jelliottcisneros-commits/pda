from types import SimpleNamespace

from django.test import TestCase

from core.calculate_group import calculate, calculate_leverage
from core.models import Score
from core.tests.utils import create_assessment, create_user


class CalculateGroupTests(TestCase):
    def test_calculate_leverage_known_group_result(self):
        user1 = create_user()
        user2 = create_user(dict(first_name='James', last_name='Madison', email='jm@example.com', phone='555-555-5555'))
        assessment1 = create_assessment(user1)
        assessment2 = create_assessment(user2)

        score1 = Score.objects.create(
            assessment=assessment1,
            sensitivity_total=10,
            oneness_total=20,
            strength_total=30,
            appreciation_total=40,
            leveraged_total=50,
        )
        score2 = Score.objects.create(
            assessment=assessment2,
            sensitivity_total=20,
            oneness_total=30,
            strength_total=40,
            appreciation_total=50,
            leveraged_total=40,
        )

        result = calculate_leverage([score1, score2])

        self.assertEqual(result, 46.8)

        total_result = calculate("Total_Score", [score1, score2])
        self.assertEqual(total_result, [(26.8, 44.6, 62.5, 80.4, 80.4)])


    def test_religion_group_percent_known_result(self):
        item1 = SimpleNamespace(Religion_Score=SimpleNamespace(sensitivity=2, oneness=4, strength=6, appreciation=8, leveraged=0))
        item2 = SimpleNamespace(Religion_Score=SimpleNamespace(sensitivity=4, oneness=6, strength=8, appreciation=2, leveraged=4))

        result = calculate("Religion_Score", [item1, item2])

        self.assertEqual(result, [(37.5, 62.5, 87.5, 62.5, 25.0)])
