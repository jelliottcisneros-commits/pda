from types import SimpleNamespace
from unittest import TestCase

from core.presentation_data import calculate_primary_pattern_counts, calculate_primary_pattern_totals, calculate_appreciation_totals_by_area, calculate_appreciation_4plus_counts, calculate_power_quotients_by_area, calculate_group_power_quotients, calculate_individual_power_quotients, calculate_individual_power_quotients_by_area, calculate_area_extreme_counts, calculate_group_anya_power_quotients, calculate_individual_anya_power_quotients, calculate_group_primary_patterns, calculate_learning_edge_counts, calculate_group_appreciation_summary


class PresentationDataTests(TestCase):
    def test_primary_pattern_counts_share_ties(self):
        scores = [
            # Clear Sensitivity
            SimpleNamespace(
                sensitivity_total=50,
                oneness_total=30,
                strength_total=20,
            ),
            # Two-way Oneness / Strength tie
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=40,
                strength_total=40,
            ),
            # Three-way tie
            SimpleNamespace(
                sensitivity_total=30,
                oneness_total=30,
                strength_total=30,
            ),
            # Clear Strength
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=25,
                strength_total=45,
            ),
        ]

        result = calculate_primary_pattern_counts(scores)

        self.assertAlmostEqual(result["sensitivity"], 1 + (1 / 3))
        self.assertAlmostEqual(result["oneness"], 0.5 + (1 / 3))
        self.assertAlmostEqual(result["strength"], 1.5 + (1 / 3))
        self.assertAlmostEqual(sum(result.values()), 4.0)

    def test_primary_pattern_totals(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=20,
                strength_total=30,
            ),
            SimpleNamespace(
                sensitivity_total=15,
                oneness_total=25,
                strength_total=35,
            ),
        ]

        result = calculate_primary_pattern_totals(scores)

        self.assertEqual(result, {
            "sensitivity": 25,
            "oneness": 45,
            "strength": 65,
        })

    def test_appreciation_totals_by_area(self):
        scores = [
            SimpleNamespace(
                Religion_Score=SimpleNamespace(appreciation=5),
                Disability_Score=SimpleNamespace(appreciation=4),
                Culture_Score=SimpleNamespace(appreciation=3),
                Gender_Score=SimpleNamespace(appreciation=2),
                Race_Score=SimpleNamespace(appreciation=6),
                Class_Score=SimpleNamespace(appreciation=1),
                Sexual_Orientation_Score=SimpleNamespace(appreciation=7),
            ),
            SimpleNamespace(
                Religion_Score=SimpleNamespace(appreciation=2),
                Disability_Score=SimpleNamespace(appreciation=3),
                Culture_Score=SimpleNamespace(appreciation=4),
                Gender_Score=SimpleNamespace(appreciation=5),
                Race_Score=SimpleNamespace(appreciation=1),
                Class_Score=SimpleNamespace(appreciation=6),
                Sexual_Orientation_Score=SimpleNamespace(appreciation=2),
            ),
        ]

        result = calculate_appreciation_totals_by_area(scores)

        self.assertEqual(result, {
            "religion": 7,
            "disability": 7,
            "culture": 7,
            "gender": 7,
            "race": 7,
            "class": 7,
            "sexual_orientation": 9,
        })

    def test_appreciation_4plus_counts_by_area(self):
        scores = [
            SimpleNamespace(
                Religion_Score=SimpleNamespace(appreciation=5),
                Disability_Score=SimpleNamespace(appreciation=4),
                Culture_Score=SimpleNamespace(appreciation=3),
                Gender_Score=SimpleNamespace(appreciation=2),
                Race_Score=SimpleNamespace(appreciation=6),
                Class_Score=SimpleNamespace(appreciation=1),
                Sexual_Orientation_Score=SimpleNamespace(appreciation=7),
            ),
            SimpleNamespace(
                Religion_Score=SimpleNamespace(appreciation=2),
                Disability_Score=SimpleNamespace(appreciation=3),
                Culture_Score=SimpleNamespace(appreciation=4),
                Gender_Score=SimpleNamespace(appreciation=5),
                Race_Score=SimpleNamespace(appreciation=1),
                Class_Score=SimpleNamespace(appreciation=6),
                Sexual_Orientation_Score=SimpleNamespace(appreciation=2),
            ),
            SimpleNamespace(
                Religion_Score=SimpleNamespace(appreciation=4),
                Disability_Score=SimpleNamespace(appreciation=2),
                Culture_Score=SimpleNamespace(appreciation=7),
                Gender_Score=SimpleNamespace(appreciation=1),
                Race_Score=SimpleNamespace(appreciation=4),
                Class_Score=SimpleNamespace(appreciation=5),
                Sexual_Orientation_Score=SimpleNamespace(appreciation=3),
            ),
        ]

        result = calculate_appreciation_4plus_counts(scores)

        self.assertEqual(result, {
            "religion": 2,
            "disability": 1,
            "culture": 2,
            "gender": 1,
            "race": 2,
            "class": 2,
            "sexual_orientation": 1,
        })

    def test_power_quotients_by_area(self):
        scores = [
            SimpleNamespace(
                Religion_Score=SimpleNamespace(
                    sensitivity=2, oneness=4, strength=6,
                    appreciation=8, leveraged=0,
                ),
                Disability_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Culture_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Gender_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Race_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Class_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Sexual_Orientation_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
            ),
            SimpleNamespace(
                Religion_Score=SimpleNamespace(
                    sensitivity=4, oneness=6, strength=8,
                    appreciation=2, leveraged=4,
                ),
                Disability_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Culture_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Gender_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Race_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Class_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Sexual_Orientation_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
            ),
        ]

        result = calculate_power_quotients_by_area(scores)

        self.assertEqual(result["religion"], {
            "apq": 35.0,
            "uupq": 65.0,
        })

        self.assertEqual(result["race"], {
            "apq": 100.0,
            "uupq": 0.0,
        })

        self.assertEqual(set(result.keys()), {
            "religion",
            "disability",
            "culture",
            "gender",
            "race",
            "class",
            "sexual_orientation",
        })

    def test_group_power_quotients(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=20,
                strength_total=30,
                appreciation_total=40,
                leveraged_total=50,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=30,
                strength_total=40,
                appreciation_total=50,
                leveraged_total=40,
            ),
        ]

        result = calculate_group_power_quotients(scores)

        self.assertEqual(result, {
            "apq": 53.2,
            "uupq": 46.8,
        })

    def test_individual_power_quotients(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=20,
                strength_total=30,
                appreciation_total=40,
                leveraged_total=50,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=30,
                strength_total=40,
                appreciation_total=50,
                leveraged_total=40,
            ),
        ]

        result = calculate_individual_power_quotients(scores)

        self.assertEqual(result, [
            {
                "person_index": 1,
                "apq": 62.1,
                "uupq": 37.9,
            },
            {
                "person_index": 2,
                "apq": 44.3,
                "uupq": 55.7,
            },
        ])


    def test_individual_power_quotients_by_area_uses_anya_language(self):
        scores = [
            SimpleNamespace(
                Religion_Score=SimpleNamespace(
                    sensitivity=2, oneness=4, strength=6,
                    appreciation=8, leveraged=0,
                ),
                Disability_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Culture_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Gender_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Race_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Class_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
                Sexual_Orientation_Score=SimpleNamespace(
                    sensitivity=0, oneness=0, strength=0,
                    appreciation=0, leveraged=8,
                ),
            ),
        ]

        result = calculate_individual_power_quotients_by_area(scores)

        self.assertEqual(result[0]["person_index"], 1)

        self.assertEqual(result[0]["areas"]["religion"], {
            "actualized": 30.0,
            "not_yet_actualized": 70.0,
        })

        self.assertEqual(result[0]["areas"]["race"], {
            "actualized": 100.0,
            "not_yet_actualized": 0.0,
        })

        self.assertEqual(set(result[0]["areas"].keys()), {
            "religion",
            "disability",
            "culture",
            "gender",
            "race",
            "class",
            "sexual_orientation",
        })

    def test_area_extreme_counts_share_ties(self):
        individual_results = [
            {
                "person_index": 1,
                "areas": {
                    "religion": {"actualized": 20.0, "not_yet_actualized": 80.0},
                    "disability": {"actualized": 80.0, "not_yet_actualized": 20.0},
                    "culture": {"actualized": 50.0, "not_yet_actualized": 50.0},
                    "gender": {"actualized": 50.0, "not_yet_actualized": 50.0},
                    "race": {"actualized": 50.0, "not_yet_actualized": 50.0},
                    "class": {"actualized": 50.0, "not_yet_actualized": 50.0},
                    "sexual_orientation": {
                        "actualized": 50.0,
                        "not_yet_actualized": 50.0,
                    },
                },
            },
            {
                "person_index": 2,
                "areas": {
                    "religion": {"actualized": 40.0, "not_yet_actualized": 60.0},
                    "disability": {"actualized": 40.0, "not_yet_actualized": 60.0},
                    "culture": {"actualized": 90.0, "not_yet_actualized": 10.0},
                    "gender": {"actualized": 90.0, "not_yet_actualized": 10.0},
                    "race": {"actualized": 60.0, "not_yet_actualized": 40.0},
                    "class": {"actualized": 60.0, "not_yet_actualized": 40.0},
                    "sexual_orientation": {
                        "actualized": 60.0,
                        "not_yet_actualized": 40.0,
                    },
                },
            },
        ]

        result = calculate_area_extreme_counts(individual_results)

        self.assertEqual(result["most_room_for_growth"], {
            "religion": 1.5,
            "disability": 0.5,
            "culture": 0.0,
            "gender": 0.0,
            "race": 0.0,
            "class": 0.0,
            "sexual_orientation": 0.0,
        })

        self.assertEqual(result["strongest_current_asset"], {
            "religion": 0.0,
            "disability": 1.0,
            "culture": 0.5,
            "gender": 0.5,
            "race": 0.0,
            "class": 0.0,
            "sexual_orientation": 0.0,
        })

    def test_group_anya_power_quotients(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=20,
                strength_total=30,
                appreciation_total=40,
                leveraged_total=50,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=30,
                strength_total=40,
                appreciation_total=50,
                leveraged_total=40,
            ),
        ]

        result = calculate_group_anya_power_quotients(scores)

        self.assertEqual(result, {
            "actualized": 53.2,
            "not_yet_actualized": 46.8,
        })

    def test_individual_anya_power_quotients(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=20,
                strength_total=30,
                appreciation_total=40,
                leveraged_total=50,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=30,
                strength_total=40,
                appreciation_total=50,
                leveraged_total=40,
            ),
        ]

        result = calculate_individual_anya_power_quotients(scores)

        self.assertEqual(result, [
            {
                "person_index": 1,
                "actualized": 62.1,
                "not_yet_actualized": 37.9,
            },
            {
                "person_index": 2,
                "actualized": 44.3,
                "not_yet_actualized": 55.7,
            },
        ])


    def test_group_primary_patterns_preserve_ties(self):
        scores = [
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=10,
                strength_total=30,
            ),
            SimpleNamespace(
                sensitivity_total=30,
                oneness_total=20,
                strength_total=10,
            ),
        ]

        result = calculate_group_primary_patterns(scores)

        self.assertEqual(result, ["sensitivity"])

        tied_scores = [
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=30,
                strength_total=10,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=10,
                strength_total=30,
            ),
            SimpleNamespace(
                sensitivity_total=20,
                oneness_total=20,
                strength_total=20,
            ),
        ]

        tied_result = calculate_group_primary_patterns(tied_scores)

        self.assertEqual(
            tied_result,
            ["sensitivity", "oneness", "strength"],
        )

    def test_learning_edge_counts_preserve_primary_pattern_ties(self):
        scores = [
            # Sensitivity primary -> Strength learning edge
            SimpleNamespace(
                sensitivity_total=50,
                oneness_total=30,
                strength_total=20,
            ),
            # Oneness / Strength tie:
            # 0.5 -> Sensitivity edge
            # 0.5 -> Oneness edge
            SimpleNamespace(
                sensitivity_total=10,
                oneness_total=40,
                strength_total=40,
            ),
            # Three-way tie:
            # 1/3 to each corresponding learning edge
            SimpleNamespace(
                sensitivity_total=30,
                oneness_total=30,
                strength_total=30,
            ),
        ]

        result = calculate_learning_edge_counts(scores)

        self.assertAlmostEqual(
            result["sensitivity"],
            0.5 + (1 / 3),
        )
        self.assertAlmostEqual(
            result["oneness"],
            0.5 + (1 / 3),
        )
        self.assertAlmostEqual(
            result["strength"],
            1.0 + (1 / 3),
        )
        self.assertAlmostEqual(sum(result.values()), 3.0)


    def test_group_appreciation_summary(self):
        scores = [
            SimpleNamespace(appreciation_total=40),
            SimpleNamespace(appreciation_total=50),
            SimpleNamespace(appreciation_total=30),
        ]

        result = calculate_group_appreciation_summary(scores)

        self.assertEqual(result, {
            "observed": 120,
            "possible": 168,
        })
