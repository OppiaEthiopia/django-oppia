import pytest

from django.core import mail
from django.urls import reverse

from oppia.test import OppiaTestCase

from settings import constants
from settings.models import SettingProperties


class RegenerateCertficatesTest(OppiaTestCase):
    
    fixtures = ['tests/test_user.json',
                'tests/test_oppia.json',
                'default_gamification_events.json',
                'tests/test_tracker.json',
                'tests/test_permissions.json',
                'default_badges.json',
                'tests/test_course_permissions.json',
                'tests/awards/award-course.json',
                'tests/test_certificatetemplate.json',
                'tests/test_certificates.json',
                'tests/test_feedback.json',
                'tests/test_customfields.json',
                'tests/awards/test_feedback_display_name.json']
    
    STR_URL = 'profile:user_regenerate_certificates'
    STR_URL_REDIRECT = 'profile:user_regenerate_certificates_success'
    STR_TEMPLATE = 'profile/certificates/regenerate.html'
    
    ####
    # check access via GET various users
    ####
    # admin/staff/user/teacher
    def test_get_own(self):
        allowed_users = [self.admin_user,
                         self.staff_user,
                         self.teacher_user,
                         self.normal_user]
        for user in allowed_users:
            url = reverse(self.STR_URL, args=[user.id])
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.STR_TEMPLATE)
    
    
    def test_get_admin_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.STR_TEMPLATE)
    
    def test_get_staff_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.STR_TEMPLATE)

    def test_get_teacher_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.teacher_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_get_user_other(self):
        url = reverse(self.STR_URL, args=[self.admin_user.id])
        self.client.force_login(self.normal_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    ####
    # check access via POST various users
    ####

    # check certs emailed (or not)
    # check new valus of certs
    def test_post_admin_own(self):
        url = reverse(self.STR_URL, args=[self.admin_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.admin_user.id]),
                         302,
                         200)

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_post_staff_own(self):
        url = reverse(self.STR_URL, args=[self.staff_user.id])
        self.client.force_login(self.staff_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.staff_user.id]),
                         302,
                         200)

    def test_post_teacher_own(self):
        url = reverse(self.STR_URL, args=[self.teacher_user.id])
        self.client.force_login(self.teacher_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.teacher_user.id]),
                         302,
                         200)

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_post_user_own(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.normal_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_post_admin_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_post_staff_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.staff_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)

    def test_post_teacher_other(self):
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.teacher_user)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)

    def test_post_user_other(self):
        url = reverse(self.STR_URL, args=[self.admin_user.id])
        self.client.force_login(self.normal_user)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_emailing_on(self):
        SettingProperties.set_bool(constants.OPPIA_EMAIL_CERTIFICATES, True)
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)
        self.assertEqual(4, len(mail.outbox))

    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_emailing_off(self):
        SettingProperties.set_bool(constants.OPPIA_EMAIL_CERTIFICATES, False)
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, {})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)
        self.assertEqual(0, len(mail.outbox))

    # Check when email changed
    @pytest.mark.xfail(reason="works on local, but not on Github workflow")
    def test_change_email(self):
        SettingProperties.set_bool(constants.OPPIA_EMAIL_CERTIFICATES, True)
        current_email = self.normal_user.email
        new_email = 'mynewemail@email.com'
        url = reverse(self.STR_URL, args=[self.normal_user.id])
        self.client.force_login(self.admin_user)
        response = self.client.post(url, {'email': new_email,
                                          'old_email': current_email})
        self.assertRedirects(response,
                         reverse(self.STR_URL_REDIRECT,
                                 args=[self.normal_user.id]),
                         302,
                         200)
        self.assertEqual(4, len(mail.outbox))
        
        # check emails sent to new address
        for email in mail.outbox:
            self.assertEqual(new_email, email.to[0])
    