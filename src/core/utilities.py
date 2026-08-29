import io
import logging
from collections import OrderedDict
from datetime import datetime
from django.templatetags.static import static
from django.contrib.staticfiles import finders
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import HorizontalBarChart3D, VerticalBarChart3D
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import portrait, landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas  # for pdf report generation
from reportlab.platypus import Table, TableStyle, Paragraph, ListFlowable

from .calculate_group import calculate, calculate_leverage
from .models import *


def generate_graph():
    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 1.8 * inch
    bc.width = 2.8 * inch
    bc.strokeColor = colors.black
    bc.bars[0].fillColor = Color(100, 0, 0, alpha=.3)
    bc.barLabelFormat = '%s'
    bc.barLabels.nudge = 10
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 10
    bc.valueAxis.visibleGrid = 1
    bc.categoryAxis.labels.boxAnchor = 'nw'
    bc.categoryAxis.labels.dx = -30
    bc.categoryAxis.labels.dy = -35
    bc.categoryAxis.labels.angle = 45
    bc.categoryAxis.categoryNames = ['Sensitivity', 'Oneness', 'Strength', 'Appreciation', 'Leveraged']
    return bc


def generate_total_graph():
    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 1.8 * inch  # graph height
    bc.width = 2.8 * inch  # graph width
    bc.barLabelFormat = '%s'
    bc.barLabels.nudge = 10  # moves bar labels up a bit
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 10  # distance between gridlines
    bc.valueAxis.visibleGrid = 1  # makes grid visible.  Set to 0 to turn off
    bc.categoryAxis.labels.boxAnchor = 'nw'
    bc.categoryAxis.labels.dx = -30  # moves the x axis labels left a bit
    bc.categoryAxis.labels.dy = -35  # moves the x axis lables down a bit
    bc.categoryAxis.labels.angle = 45  # angle of text in labels
    bc.categoryAxis.categoryNames = ['Sensitivity', 'Oneness', 'Strength', 'Appreciation',
                                     'Leveraged']  # names of x axis categories
    return bc


def group_result(item):
    assessment = Assessment.objects.get(pk=item)
    user_id = assessment.user.id
    group = CoreGroupuser.objects.get(user=user_id)
    accesscode_id = group.accesscode.id
    accesscode_group_name = AccessCode.objects.get(pk=accesscode_id).name
    # count_group = CoreGroupuser.objects.filter(accesscode=accesscode_id).count()
    all_accesscode = CoreGroupuser.objects.filter(accesscode=accesscode_id)
    all_assessment_id = list()
    all_score_id = list()
    for assessment_item in all_accesscode:
        assessment_id = assessment_item.assessment.id
        all_assessment_id.append(assessment_id)
        score_id = Score.objects.get(assessment=assessment_id)
        all_score_id.append(score_id)

    count_group = len(all_assessment_id)
    # buffer is basically a bytestream treated like a file
    buffer = io.BytesIO()
    # canvas is what reportlab draws on
    p = canvas.Canvas(buffer)
    # page 1 - graphs
    # PDF generation starts here:
    # switch to landscape
    p.setPageSize(landscape(letter))

    p.translate(.75 * inch, inch)
    # religion graph
    religion_drawing = Drawing(2.8 * inch, 1.8 * inch)
    religion_data = calculate("Religion_Score", all_score_id)
    religion = generate_graph()
    religion.data = religion_data

    religion_title = String(1.4 * inch, 1.7 * inch, "Religion", textAnchor='middle')
    religion_title.fontName = 'Times-Bold'
    religion_title.fontSize = 13
    religion_drawing.add(religion_title)
    religion_drawing.add(religion)

    renderPDF.draw(religion_drawing, p, 0, 5 * inch, showBoundary=False)

    # disability graph
    disability_drawing = Drawing(3 * inch, 2 * inch)
    disability_data = calculate("Disability_Score", all_score_id)
    disability = generate_graph()
    disability.data = disability_data
    disability_title = String(1.4 * inch, 1.7 * inch, "Disability", textAnchor='middle')
    disability_title.fontName = 'Times-Bold'
    disability_title.fontSize = 13
    disability_drawing.add(disability_title)
    disability_drawing.add(disability)
    renderPDF.draw(disability_drawing, p, 3.25 * inch, 5 * inch, showBoundary=False)

    # culture graph
    culture_drawing = Drawing(3 * inch, 2 * inch)
    culture_data = calculate("Culture_Score", all_score_id)
    culture = generate_graph()
    culture.data = culture_data
    culture_title = String(1.4 * inch, 1.7 * inch, "Culture", textAnchor='middle')
    culture_title.fontName = 'Times-Bold'
    culture_title.fontSize = 13
    culture_drawing.add(culture_title)
    culture_drawing.add(culture)
    renderPDF.draw(culture_drawing, p, 6.5 * inch, 5 * inch, showBoundary=False)

    # gender graph
    gender_drawing = Drawing(3 * inch, 2 * inch)
    gender_data = calculate("Gender_Score", all_score_id)
    gender = generate_graph()
    gender.data = gender_data
    gender_title = String(1.4 * inch, 1.7 * inch, "Gender", textAnchor='middle')
    gender_title.fontName = 'Times-Bold'
    gender_title.fontSize = 13
    gender_drawing.add(gender_title)
    gender_drawing.add(gender)
    renderPDF.draw(gender_drawing, p, 0 * inch, 2.5 * inch, showBoundary=False)

    # race graph
    race_drawing = Drawing(3 * inch, 2 * inch)
    race_data = calculate("Race_Score", all_score_id)
    race = generate_graph()
    race.data = race_data
    race_title = String(1.4 * inch, 1.7 * inch, "Race", textAnchor='middle')
    race_title.fontName = 'Times-Bold'
    race_title.fontSize = 13
    race_drawing.add(race_title)
    race_drawing.add(race)
    renderPDF.draw(race_drawing, p, 3.25 * inch, 2.5 * inch, showBoundary=False)

    # class graph
    class_drawing = Drawing(3 * inch, 2 * inch)
    class_data = calculate("Class_Score", all_score_id)
    class_graph = generate_graph()
    class_graph.data = class_data
    class_title = String(1.4 * inch, 1.7 * inch, "Class", textAnchor='middle')
    class_title.fontName = 'Times-Bold'
    class_title.fontSize = 13
    class_drawing.add(class_title)
    class_drawing.add(class_graph)
    renderPDF.draw(class_drawing, p, 6.5 * inch, 2.5 * inch, showBoundary=False)

    # sexual orientation graph
    sexual_orientation_drawing = Drawing(3 * inch, 2 * inch)
    sexual_orientation_data = calculate("Sexual_Orientation_Score", all_score_id)
    sexual_orientation_graph = generate_graph()
    sexual_orientation_graph.data = sexual_orientation_data
    sexual_orientation_title = String(1.4 * inch, 1.7 * inch, "Sexual Orientation", textAnchor='middle')
    sexual_orientation_title.fontName = 'Times-Bold'
    sexual_orientation_title.fontSize = 13
    sexual_orientation_drawing.add(sexual_orientation_title)
    sexual_orientation_drawing.add(sexual_orientation_graph)
    renderPDF.draw(sexual_orientation_drawing, p, 0 * inch, 0 * inch, showBoundary=False)

    # Image: logo on bottom of page
    p.drawInlineImage(finders.find("core/img/pda_pdf_logo.jpg") or "core/img/pda_pdf_logo.jpg", 3.6 * inch, -.25 * inch, 2 * inch, 2 * inch)

    # total across all graph
    total_drawing = Drawing(3 * inch, 2 * inch)
    total_data = calculate("Total_Score", all_score_id)
    total_graph = generate_total_graph()
    total_graph.data = total_data
    total_title = String(1.4 * inch, 1.6 * inch, "Total across all", textAnchor='middle')
    total_title.fontName = 'Times-Bold'
    total_title.fontSize = 13
    total_drawing.add(total_title)
    total_drawing.add(total_graph)
    renderPDF.draw(total_drawing, p, 6.5 * inch, 0 * inch, showBoundary=False)

    p.showPage()

    # page 2 - more graphs
    p.translate(.25 * inch, -.25 * inch)

    percentage = calculate_leverage(all_score_id)
    remaining_percentage = round((100-percentage), 1)
    data = [[str(percentage) + r"%", "conflicts with leveraged perspective", str(remaining_percentage) + r"% aligned with a leveraged perspective."]]
    table = Table(data, rowHeights=.16 * inch)
    table.wrapOn(p, 9 * inch, .16 * inch)
    # table.drawOn(p, 0, .56 * inch)
    table.drawOn(p, 150, .56 * inch)

    # right half of page
    # p.drawString(5.25 * inch, 8.5 * inch, "Intersectional Data: Total Points Across All Sociocultural Locations")
    p.drawString(2.5 * inch, 8.5 * inch, "Intersectional Data: Total Points Across All Sociocultural Locations")
    data = [
        ["", "religion", "disability", "culture", "gender", "race", "class", "lgbtq+"],
        ["sensitivity", religion_data[0][0], disability_data[0][0], culture_data[0][0], gender_data[0][0],
         race_data[0][0], class_data[0][0], sexual_orientation_data[0][0]],
        ["oneness", religion_data[0][1], disability_data[0][1], culture_data[0][1], gender_data[0][1],
         race_data[0][1], class_data[0][1], sexual_orientation_data[0][1]],
        ["strength",  religion_data[0][2], disability_data[0][2], culture_data[0][2], gender_data[0][2],
         race_data[0][2], class_data[0][2], sexual_orientation_data[0][2]],
        ["appreciation", religion_data[0][3], disability_data[0][3], culture_data[0][3], gender_data[0][3],
         race_data[0][3], class_data[0][3], sexual_orientation_data[0][3]],
        ["leveraged", religion_data[0][4], disability_data[0][4], culture_data[0][4], gender_data[0][4],
         race_data[0][4], class_data[0][4], sexual_orientation_data[0][4]]
    ]
    table = Table(data, rowHeights=.16 * inch)
    table.wrapOn(p, 5.25 * inch, 1.44 * inch)
    # table.drawOn(p, 5.25 * inch, 7.24 * inch)
    table.drawOn(p, 2.5 * inch, 7.24 * inch)

    # radar chart
    d = Drawing(5.25 * inch, 2.8 * inch)
    spider = SpiderChart()
    spider.width = 3.5 * inch
    spider.height = 2.5 * inch

    spider.labels = ["leveraged", "sensitivity", "oneness", "appreciation", "strength"]
    spider.data = [
        (religion_data[0][4], religion_data[0][0], religion_data[0][1], religion_data[0][3], religion_data[0][2]),
        (disability_data[0][4], disability_data[0][0], disability_data[0][1], disability_data[0][3], disability_data[0][2]),
        (culture_data[0][4], culture_data[0][0], culture_data[0][1], culture_data[0][3], culture_data[0][2]),
        (gender_data[0][4], gender_data[0][0], gender_data[0][1], gender_data[0][3], gender_data[0][2]),
        (race_data[0][4], race_data[0][0], race_data[0][1], race_data[0][3], race_data[0][2]),
        (class_data[0][4], class_data[0][0], class_data[0][1], class_data[0][3], class_data[0][2]),  # class_score
        (sexual_orientation_data[0][4], sexual_orientation_data[0][0], sexual_orientation_data[0][1], sexual_orientation_data[0][3], sexual_orientation_data[0][2])  # Sexual_Orientation_Score
    ]
    spider.direction = 'clockwise'

    # sets colors for radar graph lines
    spider.strands[0].strokeColor = colors.blue
    spider.strands[1].strokeColor = colors.red
    spider.strands[2].strokeColor = colors.green
    spider.strands[3].strokeColor = colors.purple
    spider.strands[4].strokeColor = colors.turquoise
    spider.strands[5].strokeColor = colors.orange
    spider.strands[6].strokeColor = colors.blueviolet

    # sets width of radar graph lines
    spider.strands.strokeWidth = 2

    d.add(spider)

    # legend for radar graph
    legend = Legend()
    legend.x = -1.2 * inch
    legend.y = 2.2 * inch
    legend.columnMaximum = 7
    legend.boxAnchor = 'nw'
    cols = [colors.blue, colors.red, colors.green, colors.purple, colors.turquoise, colors.orange, colors.blueviolet]
    categories = ("Religion", "Disability", "Culture", "Gender", "Race", "Class", "Sexual Orientation")
    legend.colorNamePairs = list(zip(cols, categories))
    d.add(legend)

    # renderPDF.draw(d, p, 6.75 * inch, 4.5 * inch, showBoundary=False)
    renderPDF.draw(d, p, 4 * inch, 4 * inch, showBoundary=False)
    # bar graph of unacknowledged power quotient
    d = Drawing(5.25 * inch, 2.8 * inch)
    data = [
        [percentage],
        [remaining_percentage]
    ]
    bc = HorizontalBarChart()
    bc.data = data
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 10
    bc.barWidth = .1 * inch
    bc.width = 4.5 * inch
    bc.height = 1.5 * inch
    # bc.zDepth = 0.04 * inch  # 3D-only; disabled for 2D ReportLab workaround
    bc.barLabelArray = [
        str(percentage) + r"%",
        str(remaining_percentage) + r"%"
    ]
    bc.barLabelFormat = "%s"
    bc.barLabels.fontName = 'Helvetica-Bold'
    bc.barLabels.fontSize = 18
    # centers labels within respective bars
    bc.barLabels[0].dx = -4.5 * float(percentage / 200) * inch
    bc.barLabels[1].dx = -4.5 * float((100 - percentage) / 200) * inch
    bc.bars[0].fillColor = colors.lightgrey
    bc.bars[1].fillColor = colors.darkgrey
    bc.categoryAxis.style = 'stacked'
    d.add(bc)
    # renderPDF.draw(d, p, 5.1 * inch, 1.5 * inch, showBoundary=False)
    renderPDF.draw(d, p, 2.5 * inch, 1.5 * inch, showBoundary=False)
    # title for unacknowledged power quotient chart
    p.setFont("Helvetica-Bold", 14)
    # p.drawString(5.5 * inch, 3.75 * inch, "* Unknown/Unacknowledged Power Quotient")
    p.drawString(3 * inch, 3.5 * inch, "* Unknown/Unacknowledged Power Quotient")

    p.showPage()

    # page 3
    p.translate(inch, inch)
    locations = ["Religion", "Disability", "Culture", "Gender", "Race", "Class", "LGBQ+"]
    responses = ["strongly agree", "agree more than disagree", "agree and disagree about the same",
                 "disagree more than agree", "strongly disagree"]
    # page  - point calculation table
    se_totals = [0, 0, 0, 0, 0]
    o_totals = [0, 0, 0, 0, 0]
    s_totals = [0, 0, 0, 0, 0]
    a_totals = [0, 0, 0, 0, 0]
    l_totals = [0, 0, 0, 0, 0]

    # utility to track which column is currently being edited
    column_num = 0

    # totals for far right column

    # create a table for each social_location, left to right
    for location in locations:
        # table data, to be appended to.  Starts with header
        data = [[location],
                ["", "mr", "mrp"]]
        # merge first row columns
        style = TableStyle([
            ('SPAN', (0, 0), (2, 0)),
        ])
        se_loc_total = 0
        o_loc_total = 0
        s_loc_total = 0
        a_loc_total = 0
        l_loc_total = 0
        # utility to multiply number of responses by point value
        # decremented at end of loop
        multiplier = 4
        # utility to see what index to add to in totals lists
        # incremented at end of loop
        response_num = 0  # 0 = a, 1 = b, ...
        for response in responses:
            data.append([str(multiplier) + " points"])
            # count the number of responses for each perspective matching the current response
            se = Response.objects.filter(assessment__in=all_assessment_id, power_perspective="Sensitivity", response=response,
                                         sociocultural_location=location).count()
            o = Response.objects.filter(assessment__in=all_assessment_id, power_perspective="Oneness", response=response,
                                        sociocultural_location=location).count()
            s = Response.objects.filter(assessment__in=all_assessment_id, power_perspective="Strength", response=response,
                                        sociocultural_location=location).count()
            a = Response.objects.filter(assessment__in=all_assessment_id, power_perspective="Appreciation", response=response,
                                        sociocultural_location=location).count()
            l = Response.objects.filter(assessment__in=all_assessment_id, power_perspective="Leveraged", response=response,
                                        sociocultural_location=location).count()
            # multiply by number of points for this response
            # append totals to data, i.e. add a row
            total = multiplier * (se + o + s + a + l)
            data.append(['se', se, se * multiplier])
            data.append(['o', o, o * multiplier])
            data.append(['s', s, s * multiplier])
            data.append(['a', a, a * multiplier])
            data.append(['l', l, l * multiplier])
            data.append(['', 'total', total])

            # add to totals for this location
            se_loc_total += se * multiplier
            o_loc_total += o * multiplier
            s_loc_total += s * multiplier
            a_loc_total += a * multiplier
            l_loc_total += l * multiplier

            # add this for all together total
            se_totals[response_num] += se * multiplier
            o_totals[response_num] += o * multiplier
            s_totals[response_num] += s * multiplier
            a_totals[response_num] += a * multiplier
            l_totals[response_num] += l * multiplier

            # decrement multiplier and increment response_num
            multiplier -= 1
            response_num += 1

        # totals at bottom of table
        data.append([location, "", "pts"])

        data.append(["sensitivity", "", se_loc_total])
        data.append(["oneness", "", o_loc_total])
        data.append(["strength", "", s_loc_total])
        data.append(["appreciation", "", a_loc_total])
        data.append(["leveraged", "", l_loc_total])

        # merge cells in totals rows
        style.add('SPAN', (0, -6), (1, -6))
        style.add('SPAN', (0, -5), (1, -5))
        style.add('SPAN', (0, -4), (1, -4))
        style.add('SPAN', (0, -3), (1, -3))
        style.add('SPAN', (0, -2), (1, -2))
        style.add('SPAN', (0, -1), (1, -1))

        # add outline to table
        style.add('BOX', (0, 0), (-1, -1), 2, colors.black),
        # add colors for point header rows
        style.add('BACKGROUND', (0, 2), (-1, 2), colors.yellow)
        style.add('BACKGROUND', (0, 9), (-1, 9), colors.green)
        style.add('BACKGROUND', (0, 16), (-1, 16), colors.purple)
        style.add('BACKGROUND', (0, 23), (-1, 23), colors.HexColor("#EC491E"))
        style.add('BACKGROUND', (0, 30), (-1, 30), colors.HexColor("#4E89D9"))
        # add lines to divide headers
        style.add('LINEABOVE', (0, 37), (-1, 37), 1, colors.black)
        style.add('LINEABOVE', (0, 2), (-1, 2), 1, colors.black)

        # make a table - one table for each social location, pushed together to look like columns
        table = Table(data, colWidths=.4266 * inch, rowHeights=.18 * inch)
        table.setStyle(style)
        table.wrapOn(p, 1.28 * inch, 8.5 * inch)
        table.drawOn(p, 1.28 * column_num * inch, -.5 * inch)
        column_num += 1

    # totals column on far right
    data = [[""],
            ["pttl"]]
    for i in range(0, 5):
        data.append([""])  # response line
        data.append([se_totals[i]])
        data.append([o_totals[i]])
        data.append([s_totals[i]])
        data.append([a_totals[i]])
        data.append([l_totals[i]])
        data.append([""])  # total line
    data.append(["total"])
    # sums all totals from every location
    data.append([sum(se_totals)])
    data.append([sum(o_totals)])
    data.append([sum(s_totals)])
    data.append([sum(a_totals)])
    data.append([sum(l_totals)])
    table = Table(data, colWidths=.4266 * inch, rowHeights=.18 * inch)
    style = TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, colors.black)
    ])
    table.setStyle(style)
    table.wrapOn(p, .4266 * inch, 8.5 * inch)
    table.drawOn(p, 8.96 * inch, -.5 * inch)
    p.showPage()

    # finalizes PDF
    p.save()
    buffer.seek(0)
    # string to represent our filename
    naming = accesscode_group_name + "_" + str(count_group) + "_group_results.pdf"
    pdf = buffer.getvalue()
    # save the PDF to the S3 bucket!
    groups = Group.objects.filter(accesscode=accesscode_id)
    if len(groups) > 0:
        groups.delete()

    blank_groups = Group()
    blank_groups.accesscode = AccessCode.objects.get(pk=accesscode_id)
    blank_groups.PDF.save(naming, buffer)
    blank_groups.save()
    # PDF generation ends here


