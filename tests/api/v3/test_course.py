import json
import pytest
import unittest

from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from oppia.test import OppiaTestCase

from tests.utils import get_api_key, \
    update_course_visibility, \
    update_course_owner
from oppia.models import Tracker, Course
from rest_framework.test import APIClient

class CourseAPITest(OppiaTestCase):

    STR_DOWNLOAD = 'download/'
    STR_ACTIVITY = 'activity/'
    STR_ZIP_EXPECTED_CONTENT_TYPE = 'application/zip'

    def setUp(self):
        super(CourseAPITest, self).setUp()
        self.user = User.objects.get(username='demo')
        self.admin = User.objects.get(username='admin')
        self.staff = User.objects.get(username='staff')
        self.teacher = User.objects.get(username='teacher')
        self.user_auth = {
            'username': 'demo',
            'api_key': get_api_key(user=self.user).key,
        }
        self.admin_auth = {
            'username': 'admin',
            'api_key': get_api_key(user=self.admin).key
        }
        self.staff_auth = {
            'username': 'staff',
            'api_key': get_api_key(user=self.staff).key
        }
        self.teacher_auth = {
            'username': 'teacher',
            'api_key': get_api_key(user=self.teacher).key
        }
        self.url = '/api/v3/course/'

    # Post invalid
    def test_post_invalid(self):
        client = APIClient()
        response = client.post(self.url, format='json')
        self.assertEqual(403, response.status_code)

    # test unauthorized
    @pytest.mark.xfail(reason="expected fail until v3 api fully developed")
    @unittest.expectedFailure
    def test_unauthorized(self):
        data = {
            'username': 'demo',
            'api_key': '1234',
        }
        client = APIClient()
        response = client.get(self.url, data=data, format='json')
        self.assertEqual(403, response.status_code)

    # test authorized
    def test_authorized(self):
        data = {
            'username': 'demo',
            'api_key': '1234',
        }
        client = APIClient()
        response = client.get(self.url, data=data, format='json')
        self.assertEqual(200, response.status_code)

    # test contains courses (and right no of courses)
    def test_has_courses(self):
        client = APIClient()
        response = client.get(
            self.url, format='json', data=self.user_auth)
        self.assertEqual(200, response.status_code)
        response_data = json.loads(response.content)
        self.assertTrue('courses' in response_data)
        # should have 2 courses with the test data set
        self.assertEqual(3, len(response_data['courses']))
        # check each course had a download url
        for course in response_data['courses']:
            self.assertTrue('url' in course)
            self.assertTrue('shortname' in course)
            self.assertTrue('title' in course)
            self.assertTrue('version' in course)
            self.assertTrue('author' in course)
            self.assertTrue('organisation' in course)

    
    def test_course_get_single(self):
        client = APIClient()
        resource_url = self.url + "1/"
        print(resource_url)
        response = client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertEqual(200, response.status_code)
        course = json.loads(response.content)
        # check course format
        self.assertTrue('shortname' in course)
        self.assertTrue('title' in course)
        self.assertTrue('description' in course)
        self.assertTrue('version' in course)
        self.assertTrue('author' in course)
        self.assertTrue('organisation' in course)

    
    def test_course_get_single_not_found(self):
        client = APIClient()
        resource_url = self.url + "999/"
        response = client.get(resource_url, format='json', data=self.user_auth)
        self.assertEqual(404, response.status_code)

    '''
    def test_course_get_single_draft_nonvisible(self):
        resource_url = get_api_url('v3', 'course', 3)
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_get_single_draft_admin_visible(self):
        resource_url = get_api_url('v3', 'course', 3)
        resp = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)

    def test_course_download_file_zip_not_found(self):
        resource_url = get_api_url('v3', 'course', 5) + self.STR_DOWNLOAD
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_download_file_course_not_found(self):
        resource_url = get_api_url('v3', 'course', 999) + self.STR_DOWNLOAD
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_download_draft_nonvisible(self):
        resource_url = get_api_url('v3', 'course', 3) + self.STR_DOWNLOAD
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_get_activity(self):
        resource_url = get_api_url('v3', 'course', 1) + self.STR_ACTIVITY
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpOK(resp)

    def test_course_get_activity_notfound(self):
        resource_url = get_api_url('v3', 'course', 999) + self.STR_ACTIVITY
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_get_activity_draft_nonvisible(self):
        resource_url = get_api_url('v3', 'course', 3) + self.STR_ACTIVITY
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)

    def test_course_get_activity_draft_admin_visible(self):
        resource_url = get_api_url('v3', 'course', 3) + self.STR_ACTIVITY
        resp = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertHttpOK(resp)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_live_course_admin(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_live_course_staff(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.staff_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_live_course_teacher(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.teacher_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_live_course_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_draft_course_admin(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, True, False)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_draft_course_staff(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, True, False)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.staff_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    def test_draft_course_teacher(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, True, False)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.teacher_auth)
        self.assertEqual(response.status_code, 404)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_draft_course_teacher_owner(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, True, False)
        update_course_owner(1, self.teacher.id)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.teacher_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        update_course_visibility(1, False, False)
        update_course_owner(1, self.admin.id)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    def test_draft_course_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, True, False)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertEqual(response.status_code, 404)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_archived_course_admin(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, False, True)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_archived_course_staff(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, False, True)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.staff_auth)
        self.assertEqual(response.status_code, 404)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_archived_course_teacher(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, False, True)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.teacher_auth)
        self.assertEqual(response.status_code, 404)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_archived_course_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        update_course_visibility(1, False, True)
        resource_url = get_api_url('v3', 'course', 1) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertEqual(response.status_code, 404)
        update_course_visibility(1, False, False)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    # Course does not exist
    def test_dne_course_admin(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1123) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.admin_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_dne_course_staff(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1123) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.staff_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_dne_course_teacher(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1123) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.teacher_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_dne_course_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 1123) + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    @pytest.mark.xfail(reason="works on local but not on github workflows")
    def test_live_course_shortname_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 'anc1-all') \
            + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpOK(response)
        self.assertEqual(response['content-type'],
                         self.STR_ZIP_EXPECTED_CONTENT_TYPE)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start+1, tracker_count_end)

    def test_dne_course_shortname_normal(self):
        tracker_count_start = Tracker.objects.all().count()
        resource_url = get_api_url('v3', 'course', 'does-not-exist') \
            + self.STR_DOWNLOAD
        response = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertEqual(response.status_code, 404)
        tracker_count_end = Tracker.objects.all().count()
        self.assertEqual(tracker_count_start, tracker_count_end)

    def test_course_shortname_get_single(self):
        resource_url = get_api_url('v3', 'course', 'anc1-all')
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)
        # check course format
        course = self.deserialize(resp)
        self.assertTrue('shortname' in course)
        self.assertTrue('title' in course)
        self.assertTrue('description' in course)
        self.assertTrue('version' in course)
        self.assertTrue('author' in course)
        self.assertTrue('organisation' in course)

    def test_course_shortname_get_single_staff(self):
        resource_url = get_api_url('v3', 'course', 'anc1-all')
        resp = self.api_client.get(
            resource_url, format='json', data=self.staff_auth)
        self.assertHttpOK(resp)
        self.assertValidJSON(resp.content)
        # check course format
        course = self.deserialize(resp)
        self.assertTrue('shortname' in course)
        self.assertTrue('title' in course)
        self.assertTrue('description' in course)
        self.assertTrue('version' in course)
        self.assertTrue('author' in course)
        self.assertTrue('organisation' in course)
        
    def test_course_shortname_get_single_not_found(self):
        resource_url = get_api_url('v3', 'course', 'does-not-exist')
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertHttpNotFound(resp)
        
    def test_course_shortname_get_multiple_found(self):
        # add a temp course with same shortname as another
        course = Course()
        course.shortname = 'anc1-all'
        course.version = 123456789
        course.save()

        resource_url = get_api_url('v3', 'course', 'anc1-all')
        resp = self.api_client.get(
            resource_url, format='json', data=self.user_auth)
        self.assertRaises(MultipleObjectsReturned)
        self.assertEqual(300, resp.status_code)
    '''
