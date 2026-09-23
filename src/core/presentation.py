import io

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from .presentation_data import (
    calculate_primary_pattern_counts,
    calculate_primary_pattern_totals,
    calculate_group_primary_patterns,
    calculate_learning_edge_counts,
    calculate_group_anya_power_quotients,
    calculate_individual_anya_power_quotients,
    calculate_average_individual_anya_power_quotients,
    calculate_individual_power_quotients_by_area,
    calculate_area_extreme_counts,
    calculate_appreciation_totals_by_area,
    calculate_appreciation_4plus_counts,
    calculate_group_appreciation_summary,
)


def _add_textbox(slide, text, left, top, width, height, font_size=24, bold=False):
    """Add an editable text box to a PowerPoint slide."""
    shape = slide.shapes.add_textbox(
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )

    paragraph = shape.text_frame.paragraphs[0]
    paragraph.text = text

    run = paragraph.runs[0]
    run.font.size = Pt(font_size)
    run.font.bold = bold

    return shape


def generate_group_presentation(scores):
    """Generate an editable group PowerPoint presentation.

    This first renderer creates the Primary Pattern Distribution slide.
    """
    counts = calculate_primary_pattern_counts(scores)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "Primary Pattern Distribution",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    rows = (
        ("Sensitivity", counts["sensitivity"]),
        ("Oneness", counts["oneness"]),
        ("Strength", counts["strength"]),
    )

    top = 2.0

    for label, value in rows:
        _add_textbox(
            slide,
            label,
            left=2.0,
            top=top,
            width=4.0,
            height=0.6,
            font_size=24,
            bold=True,
        )

        display_value = (
            str(int(value))
            if float(value).is_integer()
            else f"{value:.2f}".rstrip("0").rstrip(".")
        )

        _add_textbox(
            slide,
            display_value,
            left=7.0,
            top=top,
            width=2.0,
            height=0.6,
            font_size=24,
            bold=True,
        )

        top += 1.1

    group_primary_patterns = calculate_group_primary_patterns(scores)
    learning_edges = calculate_learning_edge_counts(scores)

    primary_display = " / ".join(
        pattern.replace("_", " ").title()
        for pattern in group_primary_patterns
    )

    _add_textbox(
        slide,
        f"Group Primary Pattern: {primary_display}",
        left=8.2,
        top=1.4,
        width=4.2,
        height=0.7,
        font_size=20,
        bold=True,
    )

    _add_textbox(
        slide,
        "Learning Edges",
        left=8.2,
        top=2.4,
        width=4.0,
        height=0.6,
        font_size=20,
        bold=True,
    )

    learning_edge_labels = (
        ("Sensitivity", learning_edges["sensitivity"]),
        ("Oneness", learning_edges["oneness"]),
        ("Strength", learning_edges["strength"]),
    )

    edge_top = 3.2

    for label, value in learning_edge_labels:
        display_value = (
            str(int(value))
            if float(value).is_integer()
            else f"{value:.2f}".rstrip("0").rstrip(".")
        )

        _add_textbox(
            slide,
            f"{label}: {display_value}",
            left=8.2,
            top=edge_top,
            width=3.8,
            height=0.5,
            font_size=17,
        )

        edge_top += 0.7

    group_pattern_totals = calculate_primary_pattern_totals(scores)

    _add_textbox(
        slide,
        "Group Pattern Scores",
        left=8.2,
        top=5.25,
        width=4.0,
        height=0.5,
        font_size=18,
        bold=True,
    )

    pattern_score_rows = (
        ("Sensitivity", group_pattern_totals["sensitivity"]),
        ("Oneness", group_pattern_totals["oneness"]),
        ("Strength", group_pattern_totals["strength"]),
    )

    score_top = 5.8

    for label, value in pattern_score_rows:
        _add_textbox(
            slide,
            f"{label}: {value}",
            left=8.2,
            top=score_top,
            width=3.8,
            height=0.4,
            font_size=15,
        )

        score_top += 0.45

    # --------------------------------------------------------
    # Slide 2: Group A/NYA Power Quotient
    # --------------------------------------------------------
    anya = calculate_group_anya_power_quotients(scores)

    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "A/NYA Power Quotient",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    # Actualized Power intentionally appears on the LEFT.
    _add_textbox(
        slide,
        "Actualized Power",
        left=1.4,
        top=2.2,
        width=4.5,
        height=0.6,
        font_size=24,
        bold=True,
    )

    _add_textbox(
        slide,
        f"{anya['actualized']}%",
        left=1.4,
        top=3.0,
        width=4.5,
        height=1.0,
        font_size=36,
        bold=True,
    )

    # Not-Yet-Actualized Power intentionally appears on the RIGHT.
    _add_textbox(
        slide,
        "Not-Yet-Actualized Power",
        left=7.0,
        top=2.2,
        width=5.0,
        height=0.6,
        font_size=24,
        bold=True,
    )

    _add_textbox(
        slide,
        f"{anya['not_yet_actualized']}%",
        left=7.0,
        top=3.0,
        width=4.5,
        height=1.0,
        font_size=36,
        bold=True,
    )

    _add_textbox(
        slide,
        "Power presently being accessed and expressed",
        left=1.4,
        top=4.3,
        width=4.5,
        height=0.8,
        font_size=16,
    )

    _add_textbox(
        slide,
        "Power that exists but is not presently being accessed and expressed",
        left=7.0,
        top=4.3,
        width=5.0,
        height=1.0,
        font_size=16,
    )

    # --------------------------------------------------------
    # Slide 3: A/NYA by Sociocultural Area
    # --------------------------------------------------------
    individual_by_area = calculate_individual_power_quotients_by_area(scores)
    area_counts = calculate_area_extreme_counts(individual_by_area)

    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "A/NYA by Sociocultural Area",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    _add_textbox(
        slide,
        "Most Room for Growth",
        left=1.0,
        top=1.5,
        width=4.8,
        height=0.6,
        font_size=22,
        bold=True,
    )

    _add_textbox(
        slide,
        "Strongest Current Asset",
        left=7.0,
        top=1.5,
        width=5.0,
        height=0.6,
        font_size=22,
        bold=True,
    )

    area_labels = {
        "religion": "Religion",
        "disability": "Disability",
        "culture": "Culture",
        "gender": "Gender",
        "race": "Race",
        "class": "Class",
        "sexual_orientation": "Sexual Orientation",
    }

    top = 2.3

    for area_name, label in area_labels.items():
        growth_value = area_counts["most_room_for_growth"][area_name]
        asset_value = area_counts["strongest_current_asset"][area_name]

        growth_display = (
            str(int(growth_value))
            if float(growth_value).is_integer()
            else f"{growth_value:.2f}".rstrip("0").rstrip(".")
        )

        asset_display = (
            str(int(asset_value))
            if float(asset_value).is_integer()
            else f"{asset_value:.2f}".rstrip("0").rstrip(".")
        )

        _add_textbox(
            slide,
            f"{label}: {growth_display}",
            left=1.0,
            top=top,
            width=4.8,
            height=0.45,
            font_size=16,
        )

        _add_textbox(
            slide,
            f"{label}: {asset_display}",
            left=7.0,
            top=top,
            width=5.0,
            height=0.45,
            font_size=16,
        )

        top += 0.58

    # --------------------------------------------------------
    # Slide 4: Appreciation
    # --------------------------------------------------------
    appreciation_totals = calculate_appreciation_totals_by_area(scores)
    appreciation_4plus = calculate_appreciation_4plus_counts(scores)
    appreciation_summary = calculate_group_appreciation_summary(scores)

    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "Appreciation",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    _add_textbox(
        slide,
        (
            f"{appreciation_summary['observed']} out of "
            f"{appreciation_summary['possible']} possible"
        ),
        left=0.9,
        top=1.3,
        width=6.0,
        height=0.7,
        font_size=22,
        bold=True,
    )

    _add_textbox(
        slide,
        "Total Appreciation Points",
        left=1.0,
        top=2.1,
        width=4.5,
        height=0.5,
        font_size=18,
        bold=True,
    )

    _add_textbox(
        slide,
        "Individuals with Appreciation of 4 or more",
        left=7.0,
        top=2.1,
        width=5.2,
        height=0.7,
        font_size=18,
        bold=True,
    )

    area_labels = {
        "religion": "Religion",
        "disability": "Disability",
        "culture": "Culture",
        "gender": "Gender",
        "race": "Race",
        "class": "Class",
        "sexual_orientation": "Sexual Orientation",
    }

    top = 2.9

    for area_name, label in area_labels.items():
        _add_textbox(
            slide,
            f"{label}: {appreciation_totals[area_name]} / "
            f"{appreciation_summary['possible_per_area']}",
            left=1.0,
            top=top,
            width=4.5,
            height=0.42,
            font_size=16,
        )

        _add_textbox(
            slide,
            f"{label}: {appreciation_4plus[area_name]}",
            left=7.0,
            top=top,
            width=5.0,
            height=0.42,
            font_size=16,
        )

        top += 0.55

    # --------------------------------------------------------
    # Slide 5: Anonymous Individual A/NYA Distribution
    # --------------------------------------------------------
    individual_anya = calculate_individual_anya_power_quotients(scores)
    average_anya = calculate_average_individual_anya_power_quotients(scores)

    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "Individual A/NYA Distribution",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    _add_textbox(
        slide,
        "Actualized Power",
        left=1.0,
        top=1.6,
        width=3.0,
        height=0.5,
        font_size=18,
        bold=True,
    )

    _add_textbox(
        slide,
        "Not-Yet-Actualized Power",
        left=9.0,
        top=1.6,
        width=3.3,
        height=0.5,
        font_size=18,
        bold=True,
    )

    _add_textbox(
        slide,
        "Each point represents one respondent",
        left=4.1,
        top=1.6,
        width=4.8,
        height=0.5,
        font_size=16,
    )

    if average_anya:
        _add_textbox(
            slide,
            f'Group average: {average_anya["actualized"]}% Actualized / '
            f'{average_anya["not_yet_actualized"]}% Not-Yet-Actualized',
            left=3.2,
            top=2.0,
            width=6.5,
            height=0.45,
            font_size=14,
        )

    # Continuum: 100% Actualized on the left, 0% Actualized on the right.
    axis_left = 1.2
    axis_top = 4.0
    axis_width = 10.8
    axis_right = axis_left + axis_width

    # Neutral base line.
    axis = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(axis_left),
        Inches(axis_top),
        Inches(axis_width),
        Inches(0.05),
    )
    axis.fill.solid()
    axis.fill.fore_color.rgb = RGBColor(110, 110, 110)
    axis.line.fill.background()

    # Live group-average marker and blue segment.
    # Because the horizontal coordinate is NYA, the marker moves left
    # as Actualized Power increases.
    if average_anya:
        average_nya = average_anya["not_yet_actualized"]
        average_x = axis_left + (axis_width * (average_nya / 100.0))

        blue_width = max(0, axis_right - average_x)
        if blue_width:
            blue_segment = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(average_x),
                Inches(axis_top - 0.035),
                Inches(blue_width),
                Inches(0.12),
            )
            blue_segment.fill.solid()
            blue_segment.fill.fore_color.rgb = RGBColor(91, 155, 213)
            blue_segment.line.fill.background()

        average_marker = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(average_x - 0.025),
            Inches(axis_top - 0.48),
            Inches(0.05),
            Inches(0.95),
        )
        average_marker.fill.solid()
        average_marker.fill.fore_color.rgb = RGBColor(40, 40, 40)
        average_marker.line.fill.background()

    # Reference ticks show Actualized Power from left to right.
    for actualized in (100, 75, 50, 25, 0):
        nya = 100 - actualized
        tick_x = axis_left + (axis_width * (nya / 100.0))

        tick = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(tick_x - 0.01),
            Inches(axis_top - 0.06),
            Inches(0.02),
            Inches(0.18),
        )
        tick.fill.solid()
        tick.fill.fore_color.rgb = RGBColor(80, 80, 80)
        tick.line.fill.background()

        _add_textbox(
            slide,
            f"{actualized}%",
            left=tick_x - 0.28,
            top=axis_top + 0.18,
            width=0.56,
            height=0.35,
            font_size=13,
        )

    # Inward-pointing end-cap triangles.
    left_cap = slide.shapes.add_shape(
        MSO_SHAPE.ISOSCELES_TRIANGLE,
        Inches(axis_left - 0.18),
        Inches(axis_top - 0.07),
        Inches(0.18),
        Inches(0.18),
    )
    left_cap.rotation = 90
    left_cap.fill.solid()
    left_cap.fill.fore_color.rgb = RGBColor(80, 80, 80)
    left_cap.line.fill.background()

    right_cap = slide.shapes.add_shape(
        MSO_SHAPE.ISOSCELES_TRIANGLE,
        Inches(axis_right),
        Inches(axis_top - 0.07),
        Inches(0.18),
        Inches(0.18),
    )
    right_cap.rotation = 270
    right_cap.fill.solid()
    right_cap.fill.fore_color.rgb = RGBColor(80, 80, 80)
    right_cap.line.fill.background()

    # One anonymous dot per respondent.
    # Identical scores stack vertically rather than being staggered arbitrarily.
    stack_counts = {}

    for person in individual_anya:
        nya = person["not_yet_actualized"]
        x_position = axis_left + (axis_width * (nya / 100.0))

        stack_key = round(float(nya), 1)
        stack_index = stack_counts.get(stack_key, 0)
        stack_counts[stack_key] = stack_index + 1

        y_position = 3.45 - (stack_index * 0.28)

        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(x_position - 0.09),
            Inches(y_position),
            Inches(0.18),
            Inches(0.18),
        )
        dot.line.fill.background()

    _add_textbox(
        slide,
        "100% Actualized  <-------------------->  Not-Yet-Actualized (0% Actualized)",
        left=1.2,
        top=5.0,
        width=10.8,
        height=0.5,
        font_size=14,
    )

    # --------------------------------------------------------
    # Slide 6: Integration
    # Conceptual framing only — intentionally no Integration score.
    # --------------------------------------------------------
    slide = prs.slides.add_slide(blank_layout)

    _add_textbox(
        slide,
        "Integration: Being Home in Ourselves",
        left=0.8,
        top=0.5,
        width=11.7,
        height=0.7,
        font_size=28,
        bold=True,
    )

    _add_textbox(
        slide,
        "Integration is having access to mind, heart, and courage "
        "without being governed by any one of them.",
        left=1.2,
        top=1.55,
        width=10.8,
        height=0.9,
        font_size=20,
    )

    _add_textbox(slide, "MIND\nSensitivity", left=1.0, top=3.0,
                 width=3.2, height=0.9, font_size=18, bold=True)

    _add_textbox(slide, "HEART\nOneness", left=5.05, top=3.0,
                 width=3.2, height=0.9, font_size=18, bold=True)

    _add_textbox(slide, "COURAGE\nStrength", left=9.05, top=3.0,
                 width=3.2, height=0.9, font_size=18, bold=True)

    _add_textbox(
        slide,
        "Sovereignty: conscious agency and coordination",
        left=2.4,
        top=4.45,
        width=8.6,
        height=0.6,
        font_size=19,
        bold=True,
    )

    _add_textbox(
        slide,
        "Integration is being home in ourselves.\n"
        "Actualization is what becomes possible from home.",
        left=2.0,
        top=5.45,
        width=9.4,
        height=0.9,
        font_size=18,
    )

    output = io.BytesIO()
    prs.save(output)
    output.seek(0)

    return output
