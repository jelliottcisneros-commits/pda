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

