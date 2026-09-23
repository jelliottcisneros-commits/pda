from core.calculate_group import calculate_category_power_quotients, calculate_power_quotients

def calculate_primary_pattern_counts(scores):
    """Return weighted counts for the three primary patterns.

    Each person contributes a total of 1.0:
    - clear highest pattern: 1.0
    - two-way tie: 0.5 / 0.5
    - three-way tie: 1/3 each
    """
    counts = {
        "sensitivity": 0.0,
        "oneness": 0.0,
        "strength": 0.0,
    }

    for score in scores:
        values = {
            "sensitivity": score.sensitivity_total,
            "oneness": score.oneness_total,
            "strength": score.strength_total,
        }

        highest = max(values.values())
        tied_patterns = [
            pattern
            for pattern, value in values.items()
            if value == highest
        ]

        share = 1.0 / len(tied_patterns)

        for pattern in tied_patterns:
            counts[pattern] += share

    return counts

def calculate_primary_pattern_totals(scores):
    """Return group totals for the three primary patterns."""
    return {
        "sensitivity": sum(score.sensitivity_total for score in scores),
        "oneness": sum(score.oneness_total for score in scores),
        "strength": sum(score.strength_total for score in scores),
    }

def calculate_appreciation_totals_by_area(scores):
    """Return total Appreciation points for each sociocultural location."""
    area_fields = {
        "religion": "Religion_Score",
        "disability": "Disability_Score",
        "culture": "Culture_Score",
        "gender": "Gender_Score",
        "race": "Race_Score",
        "class": "Class_Score",
        "sexual_orientation": "Sexual_Orientation_Score",
    }

    return {
        area_name: sum(
            getattr(score, model_field).appreciation
            for score in scores
        )
        for area_name, model_field in area_fields.items()
    }

def calculate_appreciation_4plus_counts(scores):
    """Return counts of people with Appreciation >= 4 by sociocultural location."""
    area_fields = {
        "religion": "Religion_Score",
        "disability": "Disability_Score",
        "culture": "Culture_Score",
        "gender": "Gender_Score",
        "race": "Race_Score",
        "class": "Class_Score",
        "sexual_orientation": "Sexual_Orientation_Score",
    }

    return {
        area_name: sum(
            1
            for score in scores
            if getattr(score, model_field).appreciation >= 4
        )
        for area_name, model_field in area_fields.items()
    }

def calculate_power_quotients_by_area(scores):
    """Return APQ/UUPQ percentages for each sociocultural location."""
    area_fields = {
        "religion": "Religion_Score",
        "disability": "Disability_Score",
        "culture": "Culture_Score",
        "gender": "Gender_Score",
        "race": "Race_Score",
        "class": "Class_Score",
        "sexual_orientation": "Sexual_Orientation_Score",
    }

    return {
        area_name: calculate_category_power_quotients(model_field, scores)
        for area_name, model_field in area_fields.items()
    }

def calculate_group_power_quotients(scores):
    """Return overall group APQ/UUPQ percentages."""
    maximum_total = 56 * len(scores)

    return calculate_power_quotients(
        sensitivity_total=sum(score.sensitivity_total for score in scores),
        oneness_total=sum(score.oneness_total for score in scores),
        strength_total=sum(score.strength_total for score in scores),
        appreciation_total=sum(score.appreciation_total for score in scores),
        leveraged_total=sum(score.leveraged_total for score in scores),
        maximum_total=maximum_total,
    )

def calculate_individual_power_quotients(scores):
    """Return anonymous individual APQ/UUPQ values for the continuum."""
    results = []

    for person_index, score in enumerate(scores, start=1):
        quotients = calculate_power_quotients(
            sensitivity_total=score.sensitivity_total,
            oneness_total=score.oneness_total,
            strength_total=score.strength_total,
            appreciation_total=score.appreciation_total,
            leveraged_total=score.leveraged_total,
            maximum_total=56,
        )

        results.append({
            "person_index": person_index,
            "apq": quotients["apq"],
            "uupq": quotients["uupq"],
        })

    return results



def calculate_individual_power_quotients_by_area(scores):
    """Return anonymous individual A/NYA values for all sociocultural areas.

    The underlying quotient math is unchanged:
    - Actualized = existing APQ
    - Not-Yet-Actualized = existing UUPQ
    """
    area_fields = {
        "religion": "Religion_Score",
        "disability": "Disability_Score",
        "culture": "Culture_Score",
        "gender": "Gender_Score",
        "race": "Race_Score",
        "class": "Class_Score",
        "sexual_orientation": "Sexual_Orientation_Score",
    }

    results = []

    for person_index, score in enumerate(scores, start=1):
        areas = {}

        for area_name, model_field in area_fields.items():
            quotients = calculate_category_power_quotients(
                model_field,
                [score],
            )

            areas[area_name] = {
                "actualized": quotients["apq"],
                "not_yet_actualized": quotients["uupq"],
            }

        results.append({
            "person_index": person_index,
            "areas": areas,
        })

    return results


def calculate_area_extreme_counts(individual_results):
    """Count strongest assets and greatest rooms for growth by area.

    Each person contributes exactly 1.0 to each result:
    - Most Room for Growth = highest Not-Yet-Actualized percentage
    - Strongest Current Asset = highest Actualized percentage

    Ties are shared evenly.
    """
    area_names = (
        "religion",
        "disability",
        "culture",
        "gender",
        "race",
        "class",
        "sexual_orientation",
    )

    most_room_for_growth = {
        area_name: 0.0
        for area_name in area_names
    }

    strongest_current_asset = {
        area_name: 0.0
        for area_name in area_names
    }

    for person in individual_results:
        areas = person["areas"]

        highest_nya = max(
            area["not_yet_actualized"]
            for area in areas.values()
        )

        growth_ties = [
            area_name
            for area_name, values in areas.items()
            if values["not_yet_actualized"] == highest_nya
        ]

        growth_share = 1.0 / len(growth_ties)

        for area_name in growth_ties:
            most_room_for_growth[area_name] += growth_share

        highest_actualized = max(
            area["actualized"]
            for area in areas.values()
        )

        asset_ties = [
            area_name
            for area_name, values in areas.items()
            if values["actualized"] == highest_actualized
        ]

        asset_share = 1.0 / len(asset_ties)

        for area_name in asset_ties:
            strongest_current_asset[area_name] += asset_share

    return {
        "most_room_for_growth": most_room_for_growth,
        "strongest_current_asset": strongest_current_asset,
    }


def calculate_group_anya_power_quotients(scores):
    """Return overall group A/NYA percentages using existing quotient math."""
    quotients = calculate_group_power_quotients(scores)

    return {
        "actualized": quotients["apq"],
        "not_yet_actualized": quotients["uupq"],
    }


def calculate_individual_anya_power_quotients(scores):
    """Return anonymous individual A/NYA percentages."""
    legacy_results = calculate_individual_power_quotients(scores)

    return [
        {
            "person_index": result["person_index"],
            "actualized": result["apq"],
            "not_yet_actualized": result["uupq"],
        }
        for result in legacy_results
    ]



def calculate_group_primary_patterns(scores):
    """Return the group's highest primary pattern or patterns.

    Only Sensitivity, Oneness, and Strength participate.
    Ties are preserved.
    """
    totals = calculate_primary_pattern_totals(scores)

    if not totals:
        return []

    highest = max(totals.values())

    return [
        pattern
        for pattern, value in totals.items()
        if value == highest
    ]


def calculate_learning_edge_counts(scores):
    """Return weighted group learning-edge counts.

    Primary pattern -> learning edge:
    - Sensitivity -> Strength
    - Strength -> Oneness
    - Oneness -> Sensitivity

    Each person contributes a total weight of 1.0.
    Primary-pattern ties are shared evenly.
    """
    learning_edge_for_primary = {
        "sensitivity": "strength",
        "strength": "oneness",
        "oneness": "sensitivity",
    }

    counts = {
        "sensitivity": 0.0,
        "oneness": 0.0,
        "strength": 0.0,
    }

    for score in scores:
        values = {
            "sensitivity": score.sensitivity_total,
            "oneness": score.oneness_total,
            "strength": score.strength_total,
        }

        highest = max(values.values())

        tied_patterns = [
            pattern
            for pattern, value in values.items()
            if value == highest
        ]

        share = 1.0 / len(tied_patterns)

        for primary_pattern in tied_patterns:
            learning_edge = learning_edge_for_primary[primary_pattern]
            counts[learning_edge] += share

    return counts


def calculate_group_appreciation_summary(scores):
    """Return observed and possible group Appreciation totals."""
    return {
        "observed": sum(score.appreciation_total for score in scores),
        "possible": 56 * len(scores),
        "possible_per_area": 8 * len(scores),
    }


def calculate_average_individual_anya_power_quotients(scores):
    """Return the arithmetic mean of anonymous individual A/NYA results."""
    individual_results = calculate_individual_anya_power_quotients(scores)

    if not individual_results:
        return None

    actualized = round(
        sum(result["actualized"] for result in individual_results)
        / len(individual_results),
        1,
    )

    return {
        "actualized": actualized,
        "not_yet_actualized": round(100.0 - actualized, 1),
    }
