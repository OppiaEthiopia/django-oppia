from django.views.decorators.csrf import csrf_exempt
# All imports moved to the top for PEP 8 compliance
from django.http import JsonResponse, HttpResponseRedirect, Http404
from profile.models import UserProfileCustomField, CustomField, TrainingInfo, UserProfile
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, FormView, TemplateView, DetailView
from tastypie.models import ApiKey
from helpers.mixins.SafePaginatorMixin import SafePaginatorMixin
from helpers.mixins.TitleViewMixin import TitleViewMixin
from oppia.mixins.PermissionMixins import CanEditUserMixin
from oppia.models import Points, Award, Tracker, Course, CertificateTemplate
from profile.forms import LoginForm, RegisterForm, ProfileForm, RegenerateCertificatesForm
from profile.utils import filter_redirect
from quiz.models import QuizAttempt, QuizAttemptResponse
from settings import constants
from settings.models import SettingProperties
from io import StringIO
from urllib.parse import urlparse


# AJAX group edit view for all UserProfileCustomFields in a training group
@csrf_exempt
def ajax_edit_userprofilecustomfield_group(request, training_info_id):
    user_id = request.GET.get('user_id') or request.POST.get('user_id')
    if user_id:
        UserModel = get_user_model()
        user = UserModel.objects.filter(pk=user_id).first()
    else:
        user = request.user
    custom_fields = CustomField.objects.all().order_by('order')
    upcfs_map = {}
    upcfs = UserProfileCustomField.objects.filter(user=user, training_info_id=training_info_id)
    for upcf in upcfs:
        upcfs_map[str(upcf.key_name.id)] = upcf
    upcf_list = []
    for custom_field in custom_fields:
        upcf = upcfs_map.get(str(custom_field.id))
        if not upcf:
            # Create a dummy instance for rendering only
            from types import SimpleNamespace
            upcf = SimpleNamespace(
                key_name=custom_field,
                value_str='',
                value_int=None,
                value_bool=None,
                training_info_id=training_info_id
            )
        upcf_list.append(upcf)
    if request.method == 'POST':
        errors = {}
        # Validate and save all custom field values for the user/training group
        for upcf in upcf_list:
            value = request.POST.get(f'value_{upcf.key_name.id}', None)
            field_label = upcf.key_name.label
            # Required field validation
            if upcf.key_name.required and (value is None or value == ''):
                errors[upcf.key_name.id] = f"{field_label} is required."
                continue
            # Type validation
            if value is not None and value != '':
                if upcf.key_name.type == 'int':
                    try:
                        value_int = int(value)
                    except ValueError:
                        errors[upcf.key_name.id] = f"{field_label} must be an integer."
                        continue
                elif upcf.key_name.type == 'bool':
                    if value == 'true':
                        value_bool = True
                    elif value == 'false':
                        value_bool = False
                    else:
                        errors[upcf.key_name.id] = f"{field_label} must be True or False."
                        continue
                else:
                    value_str = value
            # Save or create the model instance if no errors for this field
            if upcf.__class__.__name__ == 'SimpleNamespace':
                # Create new UserProfileCustomField
                upcf_model = UserProfileCustomField(
                    key_name=upcf.key_name,
                    user=user,
                    training_info_id=training_info_id
                )
            else:
                upcf_model = upcf
            if upcf.key_name.type == 'int':
                upcf_model.value_int = int(value) if value not in [None, ''] else None
                upcf_model.value_str = ''
                upcf_model.value_bool = None
            elif upcf.key_name.type == 'bool':
                if value == 'true':
                    upcf_model.value_bool = True
                elif value == 'false':
                    upcf_model.value_bool = False
                else:
                    upcf_model.value_bool = None
                upcf_model.value_int = None
                upcf_model.value_str = ''
            else:
                upcf_model.value_str = value
                upcf_model.value_int = None
                upcf_model.value_bool = None
            if upcf.key_name.id not in errors:
                upcf_model.save()
        if errors:
            # Do not clear the form, send errors back
            return JsonResponse({'success': False, 'errors': errors})
        # After saving, repopulate upcf_list with updated values
        upcfs = UserProfileCustomField.objects.filter(user=user, training_info_id=training_info_id)
        upcfs_map = {str(upcf.key_name.id): upcf for upcf in upcfs}
        upcf_list = []
        for custom_field in custom_fields:
            upcf = upcfs_map.get(str(custom_field.id))
            if not upcf:
                from types import SimpleNamespace
                upcf = SimpleNamespace(
                    key_name=custom_field,
                    value_str='',
                    value_int=None,
                    value_bool=None,
                    training_info_id=training_info_id
                )
            upcf_list.append(upcf)
        return JsonResponse({'success': True})
    return render(request, 'profile/ajax_edit_userprofilecustomfield_group.html', {
        'upcfs': upcf_list,
        'custom_fields': custom_fields,
        'training_info_id': training_info_id,
        'user_id': user.id if user else None
    })


STR_COMMON_FORM = 'common/form/form.html'
STR_OPPIA_HOME = 'oppia:index'


class LoginView(TitleViewMixin, FormView):
    template_name = STR_COMMON_FORM
    form_class = LoginForm
    title = _(u'Login')

    def get_initial(self):
        return {'next': filter_redirect(self.request.GET)}

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse(STR_OPPIA_HOME))
        return super().dispatch(*args, **kwargs)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        next_page = filter_redirect(self.request.POST)

        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(self.request, user)
            if next_page is not None:
                parsed_uri = urlparse(next_page)
                if parsed_uri.netloc == '':
                    return HttpResponseRedirect(next_page)

        return HttpResponseRedirect(reverse(STR_OPPIA_HOME))


class RegisterView(TitleViewMixin, FormView):

    template_name = STR_COMMON_FORM
    form_class = RegisterForm
    success_url = 'thanks/'
    title = _(u'Register')

    def dispatch(self, *args, **kwargs):
        self_register = SettingProperties.get_bool(
            constants.OPPIA_ALLOW_SELF_REGISTRATION,
            settings.OPPIA_ALLOW_SELF_REGISTRATION)
        if not self_register:
            raise Http404
        else:
            return super().dispatch(*args, **kwargs)

    def get_initial(self):
        return {'next': filter_redirect(self.request.GET)}

    def form_valid(self, form):
        form.save()
        # Create new user
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")

        u = authenticate(username=username, password=password)
        if u is not None and u.is_active:
            login(self.request, u)

        return super().form_valid(form)


class EditView(CanEditUserMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group CustomFields by training_info_id for selected user
        custom_fields = CustomField.objects.all().order_by('order')
        upcfs = UserProfileCustomField.objects.filter(user=self.object)
        grouped = {}
        for upcf in upcfs:
            tid = getattr(upcf, 'training_info_id', None)
            if tid not in grouped:
                grouped[tid] = []
            cf = upcf.key_name
            grouped[tid].append({'upcf': upcf, 'custom_field': cf})
        context['customfields_grouped_by_training'] = grouped
        return context

    model = User
    form_class = ProfileForm
    context_object_name = 'view_user'
    template_name = 'profile/profile.html'
    pk_url_kwarg = 'user_id'

    def __init__(self,  **kwargs):
        super().__init__(**kwargs)
        self.allow_edit = SettingProperties \
            .get_bool(constants.OPPIA_ALLOW_PROFILE_EDITING,
                      settings.OPPIA_ALLOW_PROFILE_EDITING)

    def get_object(self, queryset=None):
        if self.pk_url_kwarg in self.kwargs:
            return super().get_object()
        else:
            return self.request.user

    def get_success_url(self):
        # We return after success to the same view
        return self.request.path

    def get_form_kwargs(self):
        """As it is not a ModelForm, we remove the instance argument"""
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance')
        kwargs.update({'allow_edit': self.allow_profile_editing()})
        return kwargs

    def get_initial(self):
        key = ApiKey.objects.get(user=self.object)
        user_profile, created = UserProfile.objects \
            .get_or_create(user=self.object)

        initial = {
            'username': self.object.username,
            'email': self.object.email,
            'first_name': self.object.first_name,
            'last_name': self.object.last_name,
            'api_key': key.key,
            'organisation': user_profile.organisation,
            'grand_father': user_profile.grand_father,
            'participant_id': user_profile.participant_id,
            'gender': user_profile.gender,
            'education_level': user_profile.education_level,
            'region': user_profile.region,
            'region_uid': user_profile.region_uid,
            'zone': user_profile.zone,
            'zone_uid': user_profile.zone_uid,
            'woreda': user_profile.woreda,
            'woreda_uid': user_profile.woreda_uid,
            'phcu': user_profile.phcu,
            'phcu_uid': user_profile.phcu_uid,
            'health_post': user_profile.health_post,
            'healthpost_uid': user_profile.healthpost_uid,
            'year_of_birth': user_profile.year_of_birth,
            'year_of_employment': user_profile.year_of_employment,
            'about': user_profile.about,
            'phone_number': user_profile.phone_number,
            'profession': user_profile.profession,
            'health_post_type': user_profile.health_post_type,
            'hew_setting': user_profile.hew_setting,
            'exclude_from_reporting': user_profile.exclude_from_reporting
        }

        custom_fields = CustomField.objects.all()
        for custom_field in custom_fields:
            upcf_row = UserProfileCustomField.objects \
                .filter(key_name=custom_field, user=self.object)
            if upcf_row.exists():
                initial[custom_field.id] = upcf_row.first().get_value()

        return initial

    def form_valid(self, form):
        if self.allow_profile_editing():
            self.edit_form_process(form, self.object)
            messages.success(self.request, _(u"Profile updated"))

        # if password should be changed
        password = form.cleaned_data.get("password", )
        if password:
            self.object.set_password(password)
            self.object.save()
            messages.success(self.request, _(u"Password updated"))

        return self.render_to_response(self.get_context_data(form=form))

    def allow_profile_editing(self):
        return self.allow_edit or self.request.user.is_staff

    def edit_form_process(self, form, view_user):
        email = form.cleaned_data.get("email")
        first_name = form.cleaned_data.get("first_name")
        last_name = form.cleaned_data.get("last_name")
        view_user.email = email
        view_user.first_name = first_name
        view_user.last_name = last_name
        view_user.save()

        user_profile, created = UserProfile.objects \
            .get_or_create(user=view_user)
        
        user_profile.organisation = form.cleaned_data.get('organisation')
        user_profile.phone_number = form.cleaned_data.get('phone_number')

        if self.request.user.is_staff:
            user_profile.exclude_from_reporting = form.cleaned_data.get('exclude_from_reporting')
        user_profile.save()

        # save any custom fields
        custom_fields = CustomField.objects.all()
        for custom_field in custom_fields:
            if (form.cleaned_data.get(custom_field.id) is not None
                and form.cleaned_data.get(custom_field.id) != '') \
                    or custom_field.required is True:
                # Try to get the first matching record, or create if none exists
                profile_field = UserProfileCustomField.objects.filter(key_name=custom_field, user=view_user).first()
                if not profile_field:
                    profile_field = UserProfileCustomField.objects.create(key_name=custom_field, user=view_user)

                if custom_field.type == 'int':
                    profile_field.value_int = form.cleaned_data.get(custom_field.id)
                    profile_field.value_bool = None
                    profile_field.value_str = ''
                elif custom_field.type == 'bool':
                    profile_field.value_bool = form.cleaned_data.get(custom_field.id)
                    profile_field.value_int = None
                    profile_field.value_str = ''
                else:
                    profile_field.value_str = form.cleaned_data.get(custom_field.id)
                    profile_field.value_int = None
                    profile_field.value_bool = None

                profile_field.save()


class ExportDataView(TemplateView):

    def get(self, request, data_type):
        if data_type == 'activity':
            my_activity = Tracker.objects.filter(user=request.user)
            return render(request, 'profile/export/activity.html',
                          {'activity': my_activity})
        elif data_type == 'quiz':
            my_quizzes = []
            my_quiz_attempts = QuizAttempt.objects.filter(user=request.user)
            for mqa in my_quiz_attempts:
                data = {}
                data['quizattempt'] = mqa
                data['quizattemptresponses'] = QuizAttemptResponse.objects \
                    .filter(quizattempt=mqa)
                my_quizzes.append(data)

            return render(request, 'profile/export/quiz_attempts.html',
                          {'quiz_attempts': my_quizzes})
        elif data_type == 'points':
            points = Points.objects.filter(user=request.user)
            return render(request, 'profile/export/points.html',
                          {'points': points})
        elif data_type == 'badges':
            badges = Award.objects.filter(user=request.user)
            return render(request, 'profile/export/badges.html',
                          {'badges': badges})
        elif data_type == 'profile':
            profile, additional_profile, custom_profile =  \
                self.get_profile_data(request.user)
            return render(request, 'profile/export/profile.html',
                          {'profile': profile,
                           'additional_profile': additional_profile,
                           'custom_profile': custom_profile})
        else:
            raise Http404

    @staticmethod
    def get_profile_data(user):
        profile = User.objects.get(pk=user.id)
        additional_profile = UserProfile.objects.get(user=user)
        custom_profile_fields = CustomField.objects.filter(
            userprofilecustomfield__user=user).order_by('order')
        custom_profile = []
        for cpf in custom_profile_fields:
            cp = {}
            cp['label'] = cpf.label
            upcf = UserProfileCustomField.objects.filter(key_name=cpf.id, user=user).first()
            cp['value'] = upcf.get_value() if upcf else ''
            custom_profile.append(cp)
        return profile, additional_profile, custom_profile


class PointsView(SafePaginatorMixin, ListView):
    template_name = 'profile/points.html'
    paginate_by = 25

    def get_queryset(self):
        return Points.objects.filter(user=self.request.user).order_by('-date')


class BadgesView(ListView):
    context_object_name = 'awards'
    template_name = 'profile/badges.html'

    def get_queryset(self):
        return Award.objects.filter(
            user=self.request.user).order_by('-award_date')


class RegenerateCertificatesView(CanEditUserMixin, DetailView, FormView):
    model = User
    form_class = RegenerateCertificatesForm
    context_object_name = 'user'
    template_name = 'profile/certificates/regenerate.html'
    pk_url_kwarg = 'user_id'
    success_url = 'success/'

    def get_initial(self):
        user = self.get_object()
        return {
            'email': user.email,
            'old_email': user.email
        }

    def get_object(self, queryset=None):
        if self.pk_url_kwarg in self.kwargs:
            return super().get_object()
        else:
            return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        awards = Award.objects.filter(user=self.object)
        certificates = []
        for award in awards:
            try:
                course = Course.objects.get(awardcourse__award=award)
            except Course.DoesNotExist:
                continue
            badge = award.badge
            certs = CertificateTemplate.objects.filter(course=course, badge=badge, enabled=True)
            for cert in certs:
                certificate = {}
                certificate['course'] = course
                certificate['badge'] = badge
                valid, display_name = cert.display_name(self.object)
                certificate['display_name'] = display_name
                certificate['cert_link'] = award.certificate_pdf
                certificates.append(certificate)

        context['user'] = self.object
        context['certificates'] = certificates
        return context

    def form_valid(self, form):
        user = self.get_object()
        old_email = form.cleaned_data.get("old_email")
        new_email = form.cleaned_data.get("email")
        if old_email != new_email:
            user.email = new_email
            user.save()

        user_command = "--user=" + str(user.id)
        call_command('generate_certificates', user_command, stdout=StringIO())
        return super().form_valid(form)
