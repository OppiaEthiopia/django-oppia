import json
import operator
from itertools import chain

from django.contrib.auth.models import User
from collections import defaultdict
from django.db.models import Max, Min, Avg, F, FloatField, Q, ExpressionWrapper
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView 

from helpers.mixins.DateRangeFilterMixin import DateRangeFilterMixin
from helpers.mixins.SafePaginatorMixin import SafePaginatorMixin
from oppia.forms.activity_search import ActivitySearchForm
from oppia.mixins.PermissionMixins import CanViewUserDetailsMixin
from oppia.models import Activity, Tracker, Course
from oppia.permissions import get_user_courses, can_view_course_activity, permission_view_course
from oppia.views import filter_trackers
from profile.models import CustomField, UserProfile, UserProfileCustomField
from quiz.models import Quiz, QuizAttempt, QuizProps
from summary.models import UserCourseSummary


def get_tracker_activities(user, course_ids=[], course=None):
    if course:
        trackers = Tracker.objects.filter(course=course)
    else:
        trackers = Tracker.objects.filter(course__id__in=course_ids)

    return trackers.filter(user=user)


class UserScorecardDetails(CanViewUserDetailsMixin, DateRangeFilterMixin, DetailView):
    template_name = 'profile/user-scorecard.html'
    context_object_name = 'view_user'
    pk_url_kwarg = 'user_id'
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cohort_courses, other_courses, all_courses = get_user_courses(self.request, self.object)

        courses = []
        for course in all_courses:
            course.can_view_course_activity = can_view_course_activity(self.request, course.id)
            courses.append(UserCourseSummary.objects.get_stats_summary(self.object, course))

        order_options = ['course_display',
                         'no_quizzes_completed',
                         'pretest_score',
                         'no_activities_completed',
                         'no_points',
                         'no_badges',
                         'no_media_viewed']
        default_order = 'course_display'

        ordering = self.request.GET.get('order_by', default_order)
        inverse_order = ordering.startswith('-')
        if inverse_order:
            ordering = ordering[1:]

        if ordering not in order_options:
            ordering = default_order
            inverse_order = False

        courses.sort(key=operator.itemgetter(ordering), reverse=inverse_order)

        start_date, end_date = self.get_daterange()
        course_ids = list(chain(cohort_courses.values_list('id', flat=True),
                                other_courses.values_list('id', flat=True)))
        trackers = get_tracker_activities(self.object, course_ids=course_ids)
        activity = filter_trackers(trackers, start_date, end_date)

        context['courses'] = courses
        context['page_ordering'] = ('-' if inverse_order else '') + ordering
        context['activity_graph_data'] = activity
        return context


@method_decorator(permission_view_course, name='dispatch')
class UserCourseScorecardDetails(CanViewUserDetailsMixin, DateRangeFilterMixin, DetailView):
    template_name = 'profile/user-course-scorecard.html'
    context_object_name = 'view_user'
    pk_url_kwarg = 'user_id'
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        act_quizzes = Activity.objects \
            .filter(section__course=course, type=Activity.QUIZ) \
            .order_by('section__order', 'order')

        quizzes_attempted = 0
        quizzes_passed = 0
        course_pretest = None

        quizzes = []
        for aq in act_quizzes:
            quiz, course_pretest, quizzes_attempted, quizzes_passed = \
                process_quiz_activity(self.object, aq, course_pretest, quizzes_attempted, quizzes_passed)
            quizzes.append(quiz)

        activities_completed = course.get_activities_completed(course, self.object)
        activities_total = course.get_no_activities()
        activities_percent = (activities_completed * 100) / activities_total

        start_date, end_date = self.get_daterange()

        trackers = get_tracker_activities(self.object, course=course)
        activity = filter_trackers(trackers, start_date, end_date)

        order_options = ['quiz_order',
                         'no_attempts',
                         'max_score',
                         'min_score',
                         'first_score',
                         'latest_score',
                         'avg_score']
        default_order = 'quiz_order'
        ordering = self.request.GET.get('order_by', default_order)
        inverse_order = ordering.startswith('-')
        if inverse_order:
            ordering = ordering[1:]
        if ordering not in order_options:
            ordering = default_order
            inverse_order = False

        quizzes.sort(key=operator.itemgetter(ordering), reverse=inverse_order)

        context['page_ordering'] = ('-' if inverse_order else '') + ordering
        context['course'] = course
        context['quizzes'] = quizzes
        context['quizzes_passed'] = quizzes_passed
        context['quizzes_attempted'] = quizzes_attempted
        context['pretest_score'] = course_pretest
        context['activities_completed'] = activities_completed
        context['activities_total'] = activities_total
        context['activities_percent'] = activities_percent
        context['activity_graph_data'] = activity

        return context   

@method_decorator(permission_view_course, name='dispatch')
class UserCourseGradeResults(CanViewUserDetailsMixin, DateRangeFilterMixin, DetailView):
    template_name = 'profile/user-course-grade.html'
    context_object_name = 'view_user'
    pk_url_kwarg = 'user_id'
    model = User
  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        start_date, end_date = self.get_daterange()

        # Process quizzes dynamically for the selected course
        act_quizzes = Activity.objects.filter(section__course=course, type=Activity.QUIZ).order_by('section__order', 'order')

        quizzes_attempted = 0
        quizzes_passed = 0
        course_pretest = None
        user_profile = UserProfile.objects.get(user=self.object)
        
        #Get digests of feedback activities related to this course#quiz_digests = Activity.objects.filter(section__course=course, type=Activity.QUIZ).values_list('digest', flat=True)
        feedback_digests = Activity.objects.filter(section__course=course, type=Activity.FEEDBACK).values_list('digest', flat=True)

        # Filter quizzes by the digests through QuizProps
        feedback_quizzes = Quiz.objects.filter(quizprops__name=QuizProps.DIGEST, quizprops__value__in=feedback_digests)

        # Retrieve feedback attempts for this user and course-specific feedback quizzes
        feedback_attempts = QuizAttempt.objects.filter(user=self.object, quiz__in=feedback_quizzes).order_by('-submitted_date', '-attempt_date')
        


        quizzes = []
        # Dynamically process additional quizzes beyond predefined ones
        for aq in act_quizzes:
            quiz, course_pretest, quizzes_attempted, quizzes_passed = \
                process_quiz_activity(self.object, aq, course_pretest, quizzes_attempted, quizzes_passed)
            quizzes.append(quiz)
            
        unit_session_results = extract_and_display_unit_session_results(quizzes)

        # Additional context values
        activities_completed = course.get_activities_completed(course, self.object)
        activities_total = course.get_no_activities()
        activities_percent = (activities_completed * 100) / activities_total

        start_date, end_date = self.get_daterange()
        trackers = get_tracker_activities(self.object, course=course)
        activity = filter_trackers(trackers, start_date, end_date)

        # Sorting logic
        order_options = ['quiz_order', 'no_attempts', 'max_score', 'min_score', 'first_score', 'latest_score', 'avg_score']
        default_order = 'quiz_order'
        ordering = self.request.GET.get('order_by', default_order)
        inverse_order = ordering.startswith('-')
        if inverse_order:
            ordering = ordering[1:]
        if ordering not in order_options:
            ordering = default_order
        inverse_order = False
        quizzes.sort(key=operator.itemgetter(ordering), reverse=inverse_order)

        #context['unit_avg_results'] = unit_avg_results
        context['unit_session_results'] = unit_session_results
        context['page_ordering'] = ('-' if inverse_order else '') + ordering
        context['course'] = course
        context['feedback_attempts'] = feedback_attempts
        context['quizzes'] = quizzes
        context['quizzes_passed'] = quizzes_passed
        context['quizzes_attempted'] = quizzes_attempted
        context['pretest_score'] = course_pretest
        context['activities_completed'] = activities_completed
        context['activities_total'] = activities_total
        context['activities_percent'] = activities_percent
        context['activity_graph_data'] = activity
        context['user_profile'] = user_profile

        custom_fields = CustomField.objects.all()
        for custom_field in custom_fields:
            upcf_row = UserProfileCustomField.objects \
                .filter(key_name=custom_field, user=self.object)
            if upcf_row.exists():
                context[custom_field.id] = upcf_row.first().get_value()

        return context 

def process_quiz_activity(view_user, aq, course_pretest, quizzes_attempted, quizzes_passed):
    quiz = Quiz.objects.filter(quizprops__value=aq.digest, quizprops__name=QuizProps.DIGEST).first()

    no_attempts = quiz.get_no_attempts_by_user(quiz, view_user)
    attempts = QuizAttempt.objects.filter(quiz=quiz, user=view_user)

    passed = False
    avg_score = None
    if no_attempts > 0:
        quiz_maxscore = float(attempts[0].maxscore)
        attempts_stats = attempts.aggregate(max=Max('score'), min=Min('score'), avg=Avg('score'))
        
        max_score = 100 * float(attempts_stats['max']) / quiz_maxscore
        min_score = 100 * float(attempts_stats['min']) / quiz_maxscore
        avg_score = 100 * float(attempts_stats['avg']) / quiz_maxscore
        first_date = attempts.aggregate(date=Min('attempt_date'))['date']
        recent_date = attempts.aggregate(date=Max('attempt_date'))['date']
        first_score = 100 * float(attempts.filter(attempt_date=first_date)[0].score) / quiz_maxscore
        latest_score = 100 * float(attempts.filter(attempt_date=recent_date)[0].score) / quiz_maxscore

        passed = max_score is not None and max_score > 75
        if quiz.is_baseline():
            course_pretest = first_score
        else:
            quizzes_attempted += 1
            quizzes_passed = (quizzes_passed + 1) if passed else quizzes_passed

    else:
        max_score = None
        min_score = None
        first_score = None
        latest_score = None

    quiz_info = {
        'quiz': aq,
        'id': quiz.pk if quiz else None,
        'quiz_order': aq.order,
        'no_attempts': no_attempts,
        'max_score': max_score,
        'min_score': min_score,
        'first_score': first_score,
        'latest_score': latest_score,
        'avg_score': avg_score,
        'passed': passed
    }  
    return quiz_info, course_pretest, quizzes_attempted, quizzes_passed


def extract_and_display_unit_session_results(quizzes):

    unit_session_data = defaultdict(lambda: {
        'sessions': [],
        'total_score': 0,
        'count': 0
    })

    for quiz in quizzes:
        quiz_name = str(quiz['quiz'])
        
        if 'Session' in quiz_name:
            unit = "General"
            unit_number = float('inf')
            session_number = float('inf')

            # Extract unit number if present
            if 'Unit' in quiz_name:
                try:
                    unit_part = quiz_name.split('Unit')[-1].split()[0]
                    unit_number = int(''.join(filter(str.isdigit, unit_part)))
                    unit = f"Unit {unit_number}"
                except (IndexError, ValueError):
                    unit_number = "General"

            # Extract session number
            try:
                session_part = quiz_name.split('Session')[-1].split()[0]
                session_number = int(''.join(filter(str.isdigit, session_part)))
                session = f"Session {session_number}"
            except (IndexError, ValueError):
                continue  # Skip this quiz if session number cannot be parsed

            # Update the unit's data
            unit_session_data[unit]['sessions'].append({
                'session': session,
                'session_number': session_number,
                'quiz_name': quiz_name,
                'avg_score': quiz['avg_score'],
                'passed': quiz['passed'],
            })
            unit_session_data[unit]['total_score'] += quiz['avg_score']
            unit_session_data[unit]['count'] += 1

    # Build the final output
    display_data = []
    for unit, data in unit_session_data.items():
        avg_score = data['total_score'] / data['count']
        sorted_sessions = sorted(data['sessions'], key=lambda x: x['session_number'])

        display_data.append({
            'unit': unit,
            'avg_score': avg_score,
            'sessions': sorted_sessions
        })

    # Sort units by unit number
    display_data.sort(key=lambda x: int(x['unit'].split()[-1]) if x['unit'] != "General" else float('inf'))

    return display_data




class UserActivityDetailListDetails(CanViewUserDetailsMixin, DateRangeFilterMixin, SafePaginatorMixin, ListView):
    template_name = 'profile/activity/list.html'
    paginate_by = 25
    daterange_form_class = ActivitySearchForm
    user_url_kwarg = 'user_id'

    def get_user_id(self):
        return self.kwargs[self.user_url_kwarg]

    def get_queryset(self):
        self.filtered = False
        trackers = Tracker.objects.filter(user__pk=self.get_user_id()).exclude(type__exact='')
        start_date, end_date = self.get_daterange()
        trackers = trackers.filter(tracker_date__gte=start_date, tracker_date__lte=end_date)

        form = self.get_daterange_form()
        if form.is_valid():
            act_type = form.cleaned_data.get("type")
            if act_type:
                trackers = trackers.filter(type=act_type)

        return trackers.order_by('-tracker_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = User.objects.get(pk=self.get_user_id())
        context['advanced_search'] = self.filtered

        for tracker in context['page_obj'].object_list:
            tracker.data_obj = []
            try:
                data_dict = json.loads(tracker.data)
                for key, value in data_dict.items():
                    tracker.data_obj.append([key, value])
            except ValueError:
                pass
            tracker.data_obj.append(['agent', tracker.agent])
            tracker.data_obj.append(['ip', tracker.ip])

        return context
