from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

# from core.constants import NUM_QUESTIONS
from core.demographic_choices import DC
from core.models import Demographic, Response, Question, Score, Gender_Score, Race_Score, \
    Religion_Score, Sexual_Orientation_Score, Disability_Score, Culture_Score, Class_Score, POWER_PERSPECTIVES

def generate_vbar(x, top, title):
    from bokeh.embed import components
    from bokeh.models import FactorRange, ColumnDataSource
    from bokeh.plotting import figure

    source = ColumnDataSource(data=dict(x=x, y=top))
    p = figure(x_range=FactorRange(factors=x), plot_height=250, title=title, 
                toolbar_location=None, tools="hover", tooltips="@x: @y")
    p.vbar(x='x', top='y', width=.9, source=source)
    p.sizing_mode = "scale_both"
    p.xaxis.major_label_orientation = .5
    return components(p)

def generate_vbar_stack(x, top, title, demographic_number):
    from bokeh.embed import components
    from bokeh.models import FactorRange, ColumnDataSource, Legend
    from bokeh.plotting import figure

    demo_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 
    colors = get_color_palette(len(demo_choices))
    p = figure(x_range=FactorRange(factors=x), plot_height=250, title=title, 
                toolbar_location=None, tools="hover", tooltips="$name: @$name")
    v = p.vbar_stack(demo_choices, x='x', width=0.9, color=colors, source=ColumnDataSource(top))
    p.xaxis.major_label_orientation = .5
    legend = Legend(items=[(x, [v[i]]) for i, x in enumerate(demo_choices)])
    p.add_layout(legend, 'right')
    p.sizing_mode = "scale_both"
    return components(p)

def get_color_palette(number_of_colors):
    from bokeh.palettes import d3, inferno

    if number_of_colors < 3:
        colors = d3['Category20'][3]
        while number_of_colors < len(colors):
            colors.pop(0)
    elif number_of_colors > 20:
        colors = inferno(number_of_colors)
    else:
        colors = d3['Category20'][number_of_colors]
    return colors


@method_decorator(staff_member_required, name='dispatch')
class VisualizationIndexView(TemplateView):
    template_name = 'visualization/index.html'

    def get_context_data(self, **kwargs):
        context = super(VisualizationIndexView, self).get_context_data(**kwargs)
        context['none_value'] = len(DemographicsVisualizationView.demographic_labels)+1
        return context

@method_decorator(staff_member_required, name='dispatch')
class ResponseIndexView(TemplateView):
    template_name = 'visualization/responseindex.html'

    def get_context_data(self, **kwargs):
        context = super(ResponseIndexView, self).get_context_data(**kwargs)
        context['none_value'] = len(DemographicsVisualizationView.demographic_labels)+1
        context['questions'] = Question.objects.all().order_by('number')
        return context


@method_decorator(staff_member_required, name='dispatch')
class DemographicsVisualizationView(View):

    # labels for graphs and dropdown
    demographic_labels = ["Age", "Religion", "Area", "Disability", "Socioeconomic", "Status", "Employment", \
        "Education", "Marital", "Race or Culture", "Perception", "Sexual Orientation", "Gender", "Gender Perception", \
        "Country of Birth", "State of Birth", "Current Location (Country)", "Current Location (State)", "Purpose", "Safety"]

    # options along x axis
    demographic_choices = [DC.AGE_CHOICES, DC.RELIGION_CHOICES, DC.AREA_CHOICES, DC.DISABILITY_CHOICES, DC.ECONOMIC_CHOICES, DC.ECONOMIC_CHOICES, DC.EMPLOYMENT_CHOICES, \
        DC.EDUCATION_CHOICES, DC.MARITAL_CHOICES, DC.RACE_CULTURE_CHOICES, DC.PERCEPTION_CHOICES, DC.SEXUAL_ORIENTATION_CHOICES, DC.GENDER_CHOICES, DC.GENDER_PERCEPTION_CHOICES, \
        DC.COB_CHOICES, DC.STATE_CHOICES, DC.COB_CHOICES, DC.STATE_CHOICES, DC.PURPOSE_CHOICES, DC.SAFETY_CHOICES]

    # field name on demographic object
    demographic_fields = ["age", "religion", "area", "disability", "socioeconomic", "status", "employment", \
        "education", "marital", "race_or_culture", "perception", "sexual_orientation", "gender", "gender_perception", \
        "country_of_birth", "country_of_birth_state", "clocation", "cstate", "purpose", "safety"]

    @staticmethod
    def get_demographic_field_counts(self, demographic_number):
        data = Demographic.objects.all()
        choices = self.demographic_choices[demographic_number]
        counts = [0] * len(choices)
        for i in data:
            for j in range(len(counts)):
                if getattr(i, self.demographic_fields[demographic_number]) == choices[j][0]:
                    counts[j] = counts[j] + 1
        return counts
    
    def get(self, request, **kwargs):
        demographic_number = kwargs.get('demographic_number')
        counts = self.get_demographic_field_counts(self, demographic_number)
        choices = self.demographic_choices[demographic_number]
        x_labels = [i[0] for i in choices]
        script, div = generate_vbar(x_labels, counts, self.demographic_labels[demographic_number])
        context = dict(script=script, div=div, demographic_labels=self.demographic_labels, \
            none_value=len(DemographicsVisualizationView.demographic_labels)+1, demographics="active", \
            selected=self.demographic_labels[demographic_number], range=range(0, len(self.demographic_labels)))
        return render(request, 'visualization/demographics.html', context)

    def post(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse('visualization:demographics', kwargs=dict(demographic_number=request.POST['demographic_number'])))



@method_decorator(staff_member_required, name='dispatch')
class ResponsesVisualizationView(View):

    @staticmethod
    def get_response_with_demographic_counts(self, response_objects, demographic_number):
        demographic_objects = Demographic.objects.all()
        response_choices = [response_choice[0] for response_choice in Response.RESPONSE_CHOICES]
        demo_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 

        count_dict = { 'x' : response_choices }
        for d in demo_choices:
            count_dict[d] = [0] * len(Response.RESPONSE_CHOICES)

        for i in response_objects:
            demographic = demographic_objects.filter(assessment=i.assessment)
            # go through each demographic object connected to the same assessment
            for d in demographic:
                if i.response == response_choices[0]:
                    count_dict[getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number])][0] += 1
                if i.response == response_choices[1]:
                    count_dict[getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number])][1] += 1
                if i.response == response_choices[2]:
                    count_dict[getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number])][2] += 1
                if i.response == response_choices[3]:
                    count_dict[getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number])][3] += 1
                if i.response == response_choices[4]:
                    count_dict[getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number])][4] += 1

        return count_dict


    @staticmethod
    def get_responses_counts(response_objects):
        response_choices = [response_choice[0] for response_choice in Response.RESPONSE_CHOICES]
        counts = [0, 0, 0, 0, 0]

        for i in response_objects:
            if i.response == response_choices[0]:
                counts[0] += 1
            if i.response == response_choices[1]:
                counts[1] += 1
            if i.response == response_choices[2]:
                counts[2] += 1
            if i.response == response_choices[3]:
                counts[3] += 1
            if i.response == response_choices[4]:
                counts[4] += 1
        return counts
    
    def get(self, request, *args, **kwargs):
        demographic_number = kwargs.get('demographic_number')
        question_number = kwargs.get('question_number')

        response_data = Response.objects.filter(question_number=question_number)
        response_choices = [response_choice[0] for response_choice in Response.RESPONSE_CHOICES]

        if demographic_number > len(DemographicsVisualizationView.demographic_labels):
            counts = self.get_responses_counts(response_data)
            title = "Responses to Statement " + str(question_number)
            script, div = generate_vbar(response_choices, counts, title)
        else:
            other_counts = self.get_response_with_demographic_counts(self, response_data, demographic_number)
            title = "Responses to Statement " + str(question_number) + " by " + DemographicsVisualizationView.demographic_labels[demographic_number]
            script, div = generate_vbar_stack(response_choices, other_counts, title, demographic_number)

        question = Question.objects.get(number=question_number)
        context = dict(script=script, div=div, current_number=question_number, demographic_number=demographic_number, \
            none_value=len(DemographicsVisualizationView.demographic_labels)+1, responses="active", \
            range=range(1, Question.objects.count()+1), demographic_labels=DemographicsVisualizationView.demographic_labels, question=question)
        return render(request, 'visualization/responses.html', context)

    def post(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse('visualization:responses', kwargs=dict(question_number=request.POST['question_number'], demographic_number=request.POST['demographic_number'])))


@method_decorator(staff_member_required, name='dispatch')
class ScoresVisualizationView(View):

    score_types = ["Overall Score", "Gender Score", "Race Score", "Religion Score", "Sexual Orientation Score", \
        "Disability Score", "Culture Score", "Class Score"]

    score_choices = ["Sensitivity", "Oneness", "Strength", "Appreciation", "Leveraged"]

    @staticmethod
    def get_score_counts_demo(self, score_objects, demo_choices, demographic_number):
        demographic_objects = Demographic.objects.all()
        count_dict = { 'x' : self.score_choices }
        for d in demo_choices:
            count_dict[d] = [0, 0, 0, 0, 0]

        for score in score_objects:
            demographics = demographic_objects.filter(assessment__score=score.score)
            # go through each demographic object connected to the same assessment
            for d in demographics:
                for j in range(len(demo_choices)):
                    if getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number]) == demo_choices[j]:
                        (count_dict[demo_choices[j]])[0] += score.sensitivity
                        (count_dict[demo_choices[j]])[1] += score.oneness
                        (count_dict[demo_choices[j]])[2] += score.strength
                        (count_dict[demo_choices[j]])[3] += score.appreciation
                        (count_dict[demo_choices[j]])[4] += score.leveraged
        
        return count_dict
    
    @staticmethod
    def get_score_counts_demo_overall(self, score_objects, demo_choices, demographic_number):
        demographic_objects = Demographic.objects.all()
        count_dict = { 'x' : self.score_choices }
        for d in demo_choices:
            count_dict[d] = [0, 0, 0, 0, 0]

        for score in score_objects:
            demographics = demographic_objects.filter(assessment=score.assessment)
            # go through each demographic object connected to the same assessment
            for d in demographics:
                for j in range(len(demo_choices)):
                    if getattr(d, DemographicsVisualizationView.demographic_fields[demographic_number]) == demo_choices[j]:
                        (count_dict[demo_choices[j]])[0] += score.sensitivity_total
                        (count_dict[demo_choices[j]])[1] += score.oneness_total
                        (count_dict[demo_choices[j]])[2] += score.strength_total
                        (count_dict[demo_choices[j]])[3] += score.appreciation_total
                        (count_dict[demo_choices[j]])[4] += score.leveraged_total
        
        return count_dict

    @staticmethod
    def get_score_counts(score_objects):
        counts = [0, 0, 0, 0, 0]
        for i in score_objects:
            counts[0] += i.sensitivity
            counts[1] += i.oneness
            counts[2] += i.strength
            counts[3] += i.appreciation
            counts[4] += i.leveraged
        return counts

    @staticmethod
    def get_score_counts_overall(score_objects):
        counts = [0, 0, 0, 0, 0]
        for i in score_objects:
            counts[0] += i.sensitivity_total
            counts[1] += i.oneness_total
            counts[2] += i.strength_total
            counts[3] += i.appreciation_total
            counts[4] += i.leveraged_total
        return counts
    
    
    def get(self, request, **kwargs):

        score_type = kwargs.get('score_type')
        demographic_number = kwargs.get('demographic_number')

        if score_type == "Gender Score":
            score_objects = Gender_Score.objects.all()
        elif score_type == "Race Score":
            score_objects = Race_Score.objects.all()
        elif score_type == "Religion Score":
            score_objects = Religion_Score.objects.all()
        elif score_type == "Sexual Orientation Score":
            score_objects = Sexual_Orientation_Score.objects.all()
        elif score_type == "Disability Score":
            score_objects = Disability_Score.objects.all()
        elif score_type == "Culture Score":
            score_objects = Culture_Score.objects.all()
        elif score_type == "Class Score":
            score_objects = Class_Score.objects.all()
        elif score_type == "Overall Score":
            score_objects = Score.objects.all()

      
        score_choices = self.score_choices
        
        if demographic_number > len(DemographicsVisualizationView.demographic_labels):
            if(score_type == "Overall Score"):
                counts = self.get_score_counts_overall(score_objects)
            else:
                counts = self.get_score_counts(score_objects)
            script, div = generate_vbar(score_choices, counts, score_type)
        else:    
            title = score_type + " by " + DemographicsVisualizationView.demographic_labels[demographic_number]
            demo_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 
            if(score_type == "Overall Score"):
                new_counts = self.get_score_counts_demo_overall(self, score_objects, demo_choices, demographic_number)
            else:
                new_counts = self.get_score_counts_demo(self, score_objects, demo_choices, demographic_number)
            script, div = generate_vbar_stack(score_choices, new_counts, title, demographic_number)

        context = dict(script=script, div=div, score_type_prev=score_type, \
            demographic_number=demographic_number, score_types=self.score_types, scores="active", \
            demographic_labels=DemographicsVisualizationView.demographic_labels, none_value=len(DemographicsVisualizationView.demographic_labels)+1)
        return render(request, 'visualization/scores.html', context)

    def post(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse('visualization:scores', kwargs=dict(score_type=request.POST['score_type'], demographic_number=request.POST['demographic_number'])))
