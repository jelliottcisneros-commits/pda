import random

from django.contrib.auth.models import User as AuthUser
from django.test import TestCase
from django.urls import reverse

# from core.constants import NUM_QUESTIONS
from core.models import Demographic, Response, Question, Gender_Score, Score, POWER_PERSPECTIVES
from core.tests.utils import is_function_wrapped_by_decorator, create_user, create_assessment, RESPONSE_DICT, \
    create_response
from visualization.views import VisualizationIndexView, DemographicsVisualizationView, ResponsesVisualizationView, ScoresVisualizationView

# HELPER FUNCTIONS
def filter_out_fields_without_choices(all_fields):
    return list(filter(lambda field: len(field.choices) > 0, all_fields))

def set_demographic_field(demographic, field):
    choices = field.choices
    random_ind = random.randrange(len(choices))
    random_choice = choices[random_ind]
    setattr(demographic, field.name, random_choice[0])
    return random_ind, random_choice



class VisualizationIndexViewTests(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.force_login(admin)

    def test_presence_of_staff_member_required_decorator(self):
        """Decorator should be present"""
        self.assertTrue(
            is_function_wrapped_by_decorator(function=VisualizationIndexView.dispatch,
                                             decorator_name='staff_member_required'))

    def test_valid_request(self):
        """Successfully render template visualization:index"""
        response = self.client.get(reverse('visualization:index'))
        self.assertContains(response, 'PDA Visualizations')

class ResponseIndexViewTests(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.force_login(admin)

    def test_presence_of_staff_member_required_decorator(self):
        """Decorator should be present"""
        self.assertTrue(
            is_function_wrapped_by_decorator(function=VisualizationIndexView.dispatch,
                                             decorator_name='staff_member_required'))

    def test_valid_request(self):
        """Successfully render template visualization:index"""
        response = self.client.get(reverse('visualization:responseindex'))
        self.assertContains(response, 'Responses')


class DemographicsVisualizationViewTests(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.force_login(admin)

    def test_presence_of_staff_member_required_decorator(self):
        """Decorator is present"""
        self.assertTrue(is_function_wrapped_by_decorator(function=DemographicsVisualizationView.dispatch,
                                                         decorator_name='staff_member_required'))

    def test_valid_get_request(self):
        """Successfully render template visualization:demographics"""
        response = self.client.get(reverse('visualization:demographics', kwargs=dict(demographic_number=1)))
        self.assertContains(response, 'Demographics')

    def test_valid_post_request(self):
        """Successfully redirect to visualization:demographics with demographic_number=request.POST['demographic_number']"""
        demographic_number=1
        response = self.client.post(
            reverse('visualization:demographics', kwargs=dict(demographic_number=demographic_number)),
            data=dict(demographic_number=demographic_number))
        expected_url = reverse('visualization:demographics', kwargs=dict(demographic_number=demographic_number))
        self.assertRedirects(response, expected_url)

    def test_static_method_get_demographic_field_counts(self):
        """Returned value reflects the database"""

        def initialize_demographic_field_to_counts_map(demographic_field_to_counts_map, fields):
            for field in fields:
                counts = [0] * len(field.choices)
                demographic_field_to_counts_map[field.name] = counts
        
        def set_demographic_field_and_increment_counts(demographic, field, counts):
            choices = field.choices
            random_ind = random.randrange(len(choices))
            random_choice = choices[random_ind]
            setattr(demographic, field.name, random_choice[0])  # set demographic field to choice
            if counts is not None:
                counts[random_ind] += 1  # increment count for choice

        fields = filter_out_fields_without_choices(Demographic._meta.fields)
        expected_demographic_field_to_counts_map = {}
        initialize_demographic_field_to_counts_map(
            demographic_field_to_counts_map=expected_demographic_field_to_counts_map, fields=fields)

        user = create_user()
        for i in range(100):
            assessment = create_assessment(user=user)
            demographic = Demographic(assessment=assessment)
            for field in fields:
                counts = expected_demographic_field_to_counts_map.get(field.name)
                set_demographic_field_and_increment_counts(demographic, field, counts)
            demographic.save()

        demographic_number = 0
        for expected_count in expected_demographic_field_to_counts_map.values():
            actual_by_field = DemographicsVisualizationView.get_demographic_field_counts(DemographicsVisualizationView, demographic_number)
            self.assertEqual(expected_count, actual_by_field)
            demographic_number += 1

class ResponsesVisualizationViewTests(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.force_login(admin)

    def test_presence_of_staff_member_required_decorator(self):
        """Decorator is present"""
        self.assertTrue(is_function_wrapped_by_decorator(function=ResponsesVisualizationView.dispatch,
                                                         decorator_name='staff_member_required'))

    def test_valid_get_request(self):
        """Successfully render template response-vis.html"""
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(reverse('visualization:responses', kwargs=dict(question_number=1, demographic_number=1)))
        self.assertContains(response, 'Response')

    def test_valid_get_request_less_than_3_colors(self):
        """Successfully render template response-vis.html"""
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(reverse('visualization:responses', kwargs=dict(question_number=1, demographic_number=13)))
        self.assertContains(response, 'Response')

    def test_valid_get_request_more_than_20_colors(self):
        """Successfully render template response-vis.html"""
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(reverse('visualization:responses', kwargs=dict(question_number=1, demographic_number=15)))
        self.assertContains(response, 'Response')

    def test_valid_post_request(self):
        """Successfully redirect to response-vis with question_num=request.POST['question_num']"""
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=2, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        current_question_number = 1
        question_number_in_post_body = current_question_number + 1
        demographic_number=len(DemographicsVisualizationView.demographic_labels)+1
        response = self.client.post(
            reverse('visualization:responses', kwargs=dict(question_number=current_question_number, demographic_number=demographic_number)),
            data=dict(question_number=question_number_in_post_body, demographic_number=demographic_number))
        expected_url = reverse('visualization:responses', kwargs=dict(question_number=question_number_in_post_body, demographic_number=demographic_number))
        self.assertRedirects(response, expected_url)

    def test_static_method_get_responses_counts(self):
        """Returned counts should reflect the database values (demographic type = None)"""

        def set_response_choice(assessment, response_dict):
            random_ind = random.randrange(len(Response.RESPONSE_CHOICES))
            random_response_choice = Response.RESPONSE_CHOICES[random_ind][0]
            response_dict['response'] = random_response_choice
            create_response(assessment, response_dict=response_dict)
            return random_response_choice, random_ind

        expected_responses_counts = [0] * len(Response.RESPONSE_CHOICES)
        question_number = 1
        user = create_user()
        response_dict = RESPONSE_DICT.copy()
        response_dict['question_number'] = question_number
        for i in range(100):
            assessment = create_assessment(user=user)
            random_response_choice, random_ind = set_response_choice(assessment, response_dict)
            expected_responses_counts[random_ind] += 1

        actual_response_counts = ResponsesVisualizationView.get_responses_counts(
            Response.objects.filter(question_number=question_number))
        self.assertEqual(expected_responses_counts, actual_response_counts)

    def test_static_method_get_response_with_demographic_counts(self):
        """Returned counts should reflect the database values (demographic type != None)"""

        def set_response_choice(assessment, response_dict):
            random_ind = random.randrange(len(Response.RESPONSE_CHOICES))
            random_response_choice = Response.RESPONSE_CHOICES[random_ind][0]
            response_dict['response'] = random_response_choice
            create_response(assessment, response_dict=response_dict)
            return random_response_choice, random_ind

        question_number = 1
        demographic_number = 13
        demographic_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 
        response_choices = [response_choice[0] for response_choice in Response.RESPONSE_CHOICES]
        expected_count_dict = { 'x' : response_choices }
        for choice in demographic_choices:
            expected_count_dict[choice] = [0] * len(Response.RESPONSE_CHOICES)
        fields = filter_out_fields_without_choices(Demographic._meta.fields)
        user = create_user()
        response_dict = RESPONSE_DICT.copy()
        response_dict['question_number'] = question_number
        for i in range(100):
            assessment = create_assessment(user=user)
            # create response 
            random_response_choice, random_response_ind = set_response_choice(assessment, response_dict)
            # create demographic
            demographic = Demographic(assessment=assessment)
            random_demographic_ind, random_demographic_choice = set_demographic_field(demographic, fields[demographic_number])
            demographic.save()
            # increment counts
            expected_count_dict[random_demographic_choice[0]][random_response_ind] += 1
        actual_response_counts = ResponsesVisualizationView.get_response_with_demographic_counts(ResponsesVisualizationView, Response.objects.filter(question_number=question_number), demographic_number)
        self.assertEqual(expected_count_dict, actual_response_counts)


class ScoresVisualizationViewTests(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create_superuser(
            username='test',
            password='test',
            email='test@test.com'
        )
        self.client.force_login(admin)

    def test_presence_of_staff_member_required_decorator(self):
        """Decorator is present"""
        self.assertTrue(is_function_wrapped_by_decorator(function=ScoresVisualizationView.dispatch,
                                                         decorator_name='staff_member_required'))

    def test_valid_get_request_Overall(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Overall Score", demographic_number=1)))
        self.assertContains(response, 'Scores')

    def test_valid_get_request_Gender(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Gender Score", demographic_number=1)))
        self.assertContains(response, 'Scores')
    
    def test_valid_get_request_Race(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Race Score", demographic_number=1)))
        self.assertContains(response, 'Scores')

    def test_valid_get_request_Religion(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Religion Score", demographic_number=1)))
        self.assertContains(response, 'Scores')

    def test_valid_get_request_Sexual_Orientation(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Sexual Orientation Score", demographic_number=1)))
        self.assertContains(response, 'Scores')
        
    def test_valid_get_request_Disability(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Disability Score", demographic_number=1)))
        self.assertContains(response, 'Scores')

    def test_valid_get_request_Culture(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Culture Score", demographic_number=1)))
        self.assertContains(response, 'Scores')

    def test_valid_get_request_Class(self):
        """Successfully render template response-vis.html"""
        response = self.client.get(reverse('visualization:scores', kwargs=dict(score_type="Class Score", demographic_number=len(DemographicsVisualizationView.demographic_labels)+1)))
        self.assertContains(response, 'Scores')


    def test_valid_post_request(self):
        """Successfully redirect to response-vis with question_num=request.POST['question_num']"""
        score_type_current = "Gender Score"
        score_type_in_post_body = "Overall Score"
        demographic_number=len(DemographicsVisualizationView.demographic_labels)+1
        response = self.client.post(
            reverse('visualization:scores', kwargs=dict(score_type=score_type_current, demographic_number=demographic_number )),
            data=dict(score_type=score_type_in_post_body, demographic_number=demographic_number))
        expected_url = reverse('visualization:scores', kwargs=dict(score_type=score_type_in_post_body, demographic_number=demographic_number))
        self.assertRedirects(response, expected_url)

    def test_static_method_get_score_counts_overall(self):
        """Returned counts should reflect the database values"""
        # create 100 score objects and update expected counts
        expected_score_counts = [0, 0, 0, 0, 0]
        user = create_user()
        for i in range(100):
            assessment = create_assessment(user=user)
            attribute_counts = [0, 0, 0, 0, 0]
            for i in range(len(attribute_counts)):
                attribute_counts[i] = random.randrange(5)
                expected_score_counts[i] += attribute_counts[i]
            score = Score.objects.create(assessment=assessment, sensitivity_total=attribute_counts[0], oneness_total=attribute_counts[1], \
                strength_total=attribute_counts[2], appreciation_total=attribute_counts[3], leveraged_total=attribute_counts[4])
        
        score_objects = Score.objects.all()
        actual_score_counts = ScoresVisualizationView.get_score_counts_overall(score_objects)

        self.assertEqual(expected_score_counts, actual_score_counts)

    def test_static_method_get_score_counts(self):
        """Returned counts should reflect the database values"""

        def set_score_power_perspective(assessment, score):
            perspectives = ["sensitivity", "oneness", "strength", "appreciation", "leveraged"]
            counts_to_set = [0, 0, 0, 0, 0]
            for i in range(len(counts_to_set)):
                counts_to_set[i] = random.randrange(5)
            Gender_Score.objects.create(score=score, sensitivity=counts_to_set[0], oneness=counts_to_set[1], strength=counts_to_set[2], appreciation=counts_to_set[3], leveraged=counts_to_set[4])
            return counts_to_set

        # create 100 response objects and update expected counts
        expected_score_counts = [0, 0, 0, 0, 0]
        user = create_user()
        for i in range(100):
            assessment = create_assessment(user=user)
            score = Score.objects.create(assessment=assessment)
            score_counts_set = set_score_power_perspective(assessment, score)
            for i in range(len(expected_score_counts)):
                expected_score_counts[i] += score_counts_set[i]

        score_objects = Gender_Score.objects.all()
        actual_score_counts = ScoresVisualizationView.get_score_counts(score_objects)
        
        self.assertEqual(expected_score_counts, actual_score_counts)

    def test_static_method_get_score_counts_demo(self):
        """Returned counts should reflect the database values"""

        def set_score_power_perspective(assessment, score):
            perspectives = ["sensitivity", "oneness", "strength", "appreciation", "leveraged"]
            counts_to_set = [0, 0, 0, 0, 0]
            for i in range(len(counts_to_set)):
                counts_to_set[i] = random.randrange(5)
            Gender_Score.objects.create(score=score, sensitivity=counts_to_set[0], oneness=counts_to_set[1], strength=counts_to_set[2], appreciation=counts_to_set[3], leveraged=counts_to_set[4])
            return counts_to_set
            
        demographic_number=1
        score_choices = ["Sensitivity", "Oneness", "Strength", "Appreciation", "Leveraged"]
        expected_count_dict = { 'x' : score_choices }
        demographic_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 
        for d in demographic_choices:
            expected_count_dict[d] = [0] * len(score_choices)
        # create 100 response objects and update expected counts
        user = create_user()
        fields = filter_out_fields_without_choices(Demographic._meta.fields)

        for i in range(100):
            assessment = create_assessment(user=user)
            score = Score.objects.create(assessment=assessment)
            score_counts_set = set_score_power_perspective(assessment, score)
            demographic = Demographic(assessment=assessment)
            random_demographic_ind, random_demographic_choice = set_demographic_field(demographic, fields[demographic_number])
            demographic.save()
            # increment counts
            for i in range(len(expected_count_dict[random_demographic_choice[0]])):
                expected_count_dict[random_demographic_choice[0]][i] += score_counts_set[i]
    
        score_objects = Gender_Score.objects.all()
        actual_score_counts = ScoresVisualizationView.get_score_counts_demo(ScoresVisualizationView, score_objects, demographic_choices, demographic_number)
        
        self.assertEqual(expected_count_dict, actual_score_counts)

    def test_static_method_get_score_counts_demo_overall(self):
            
        demographic_number=1
        score_choices = ["Sensitivity", "Oneness", "Strength", "Appreciation", "Leveraged"]
        expected_count_dict = { 'x' : score_choices }
        demographic_choices = [demographic_choice[0] for demographic_choice in DemographicsVisualizationView.demographic_choices[demographic_number]] 
        for d in demographic_choices:
            expected_count_dict[d] = [0] * len(score_choices)
        # create 100 response objects and update expected counts
        user = create_user()
        fields = filter_out_fields_without_choices(Demographic._meta.fields)

        for i in range(100):
            assessment = create_assessment(user=user)
            counts_to_set = [0, 0, 0, 0, 0]
            for i in range(len(counts_to_set)):
                counts_to_set[i] = random.randrange(5)
            score = Score.objects.create(assessment=assessment, sensitivity_total=counts_to_set[0], oneness_total=counts_to_set[1], strength_total=counts_to_set[2], appreciation_total=counts_to_set[3], leveraged_total=counts_to_set[4])
            demographic = Demographic(assessment=assessment)
            random_demographic_ind, random_demographic_choice = set_demographic_field(demographic, fields[demographic_number])
            demographic.save()
            score.save()
            # increment counts
            for i in range(len(expected_count_dict[random_demographic_choice[0]])):
                expected_count_dict[random_demographic_choice[0]][i] += counts_to_set[i]
    
        score_objects = Score.objects.all()
        actual_score_counts = ScoresVisualizationView.get_score_counts_demo_overall(ScoresVisualizationView, score_objects, demographic_choices, demographic_number)
        
        self.assertEqual(expected_count_dict, actual_score_counts)