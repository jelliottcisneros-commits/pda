from django.contrib.messages import ERROR, get_messages
from django.contrib.messages.storage.base import Message
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from core.constants import INVALID_LAST_QUESTION_ERROR_MESSAGE, CANNOT_MOVE_BACKWARDS_MESSAGE
from core.decorators import valid_last_question_required, assessment_completion_required, \
    incomplete_assessment_required, \
    require_session_key_absence
from core.tests.utils import *


class RequireSessionKeyAbsenceDecoratorTests(TestCase):
    def test_session_key_present(self):
        """Redirect to continue with error message saying cannot move backwards (since session key already exists) """

        session_key = 'key'

        @require_session_key_absence(session_key)
        def test_view(request):
            self.fail('Unexpectedly got to inner function')

        request = MockHttpRequest()
        session = request.session
        session[session_key] = 'value'
        assert session_key in request.session
        response = test_view(request)

        expected_url = reverse('core:continue')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)
        expected_message = Message(level=ERROR, message=CANNOT_MOVE_BACKWARDS_MESSAGE)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)

    def test_session_key_absent(self):
        """Call wrapped function """
        session_key = 'key'
        msg = 'success'

        @require_session_key_absence(session_key)
        def test_view(request, msg):
            return HttpResponse(msg)

        request = MockHttpRequest()

        assert session_key not in request.session
        response = test_view(request, msg=msg)

        self.assertContains(response, msg)


class ValidLastQuestionRequiredDecoratorTests(TestCase):
    def test_last_question_is_absent(self):
        """Redirect to demographic"""

        @valid_last_question_required
        def test_view(request, user_id, assessment_id):
            self.fail('Unexpectedly got to inner function')

        user_id = 0
        assessment_id = 0
        request = MockHttpRequest()

        assert 'last_question' not in request.session
        response = test_view(request, user_id=user_id, assessment_id=assessment_id)

        expected_url = reverse('core:demographics', kwargs=dict(user_id=user_id, assessment_id=assessment_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_last_question_is_negative(self):
        """Raise AssertionError"""

        @valid_last_question_required
        def test_view(request, user_id, assessment_id):
            self.fail('Unexpectedly got to inner function')

        last_question = -1
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        with self.assertRaisesMessage(AssertionError, INVALID_LAST_QUESTION_ERROR_MESSAGE % last_question):
            test_view(request, user_id=0, assessment_id=0)

    def test_last_question_is_greater_than_num_questions(self):
        """Raise AssertionError"""

        @valid_last_question_required
        def test_view(request, user_id, assessment_id):
            self.fail('Unexpectedly got to inner function')

        create_question()
        num_questions = Question.objects.count()
        last_question = num_questions + 1
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        with self.assertRaisesMessage(AssertionError, INVALID_LAST_QUESTION_ERROR_MESSAGE % last_question):
            test_view(request, user_id=0, assessment_id=0)

    def test_last_question_is_valid(self):
        """Call wrapped function"""

        @valid_last_question_required
        def test_view(request, user_id, assessment_id):
            return HttpResponse('Success')

        last_question = 0
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        response = test_view(request, user_id=0, assessment_id=0)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Success')


class IncompleteAssessmentRequiredDecoratorTests(TestCase):
    def test_assessment_is_complete(self):
        """Redirect to score"""

        @incomplete_assessment_required
        def test_view(request, user_id, assessment_id):
            self.fail('Unexpectedly got to inner function')

        user_id = 0
        assessment_id = 0
        create_question()
        num_questions = Question.objects.count()
        last_question = num_questions  # ensuring complete assessment
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        response = test_view(request, user_id=user_id, assessment_id=assessment_id)

        expected_url = reverse('core:score', kwargs=dict(user_id=user_id, assessment_id=assessment_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_assessment_is_incomplete(self):
        """Call wrapped function"""

        @incomplete_assessment_required
        def test_view(request, user_id, assessment_id):
            return HttpResponse("Success")

        user_id = 0
        assessment_id = 0
        create_question()
        create_question()
        num_questions = Question.objects.count()
        last_question = num_questions - 1  # ensuring incomplete assessment
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        response = test_view(request, user_id=user_id, assessment_id=assessment_id)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Success')


class AssessmentCompletionRequiredDecoratorTests(TestCase):
    def test_assessment_is_incomplete(self):
        """Redirect to question with number=last_question + 1"""

        @assessment_completion_required
        def test_view(request, user_id, assessment_id):
            self.fail('Unexpectedly got to inner function')

        user_id = 0
        assessment_id = 0
        create_question()
        create_question()
        num_questions = Question.objects.count()
        last_question = num_questions - 1  # ensuring incomplete assessment
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        response = test_view(request, user_id=user_id, assessment_id=assessment_id)

        expected_url = reverse('core:question',
                               kwargs=dict(user_id=user_id, assessment_id=assessment_id, number=last_question + 1))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    def test_assessment_is_complete(self):
        """Call wrapped function"""

        @assessment_completion_required
        def test_view(request, user_id, assessment_id):
            return HttpResponse("Success")

        user_id = 0
        assessment_id = 0
        create_question()
        num_questions = Question.objects.count()
        last_question = num_questions  # ensuring complete assessment
        request = MockHttpRequest()
        session = request.session
        session['last_question'] = last_question
        session.save()

        response = test_view(request, user_id=user_id, assessment_id=assessment_id)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Success')
