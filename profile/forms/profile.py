# oppia/profile/forms.py
import hashlib
import urllib

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from profile.models import CustomField
from profile.forms import helpers

from settings import constants
from settings.models import SettingProperties


class ProfileForm(forms.Form):
    api_key = forms.CharField(widget=forms.TextInput(attrs={'readonly':
                                                            'readonly'}),
                              required=False,
                              help_text=_(u'You cannot edit your API Key.'))
    username = forms.CharField(widget=forms.TextInput(attrs={'readonly':
                                                             'readonly'}),
                               required=False,
                               help_text=_(u'You cannot edit your username.'))
    email = forms.CharField(validators=[validate_email],
                            error_messages={'invalid':
                                            (u'Please enter a valid e-mail \
                                             address.')},
                            required=False)
    password = forms.CharField(widget=forms.PasswordInput,
                               required=False,
                               min_length=6,
                               error_messages={
                                   'min_length':
                                   _(u'The new password should be at least 6 \
                                   characters long')})
    password_again = forms.CharField(widget=forms.PasswordInput,
                                     required=False,
                                     min_length=6)
    first_name = forms.CharField(max_length=100,
                                 min_length=2,
                                 required=True)
    last_name = forms.CharField(max_length=100,
                                min_length=2,
                                required=True)
    organisation = forms.CharField(max_length=100, required=False)
    grand_father = forms.CharField(max_length=100, required=False)
    participant_id = forms.CharField(max_length=100, required=False)
    gender = forms.CharField(max_length=50, required=False)
    education_level = forms.CharField(max_length=100, required=False)
    region = forms.CharField(max_length=100, required=False)
    region_uid = forms.CharField(max_length=100, required=False)
    zone = forms.CharField(max_length=100, required=False)
    zone_uid = forms.CharField(max_length=100, required=False)
    woreda = forms.CharField(max_length=100, required=False)
    woreda_uid = forms.CharField(max_length=100, required=False)
    phcu = forms.CharField(max_length=100, required=False)
    phcu_uid = forms.CharField(max_length=100, required=False)
    health_post = forms.CharField(max_length=100, required=False)
    healthpost_uid = forms.CharField(max_length=100, required=False)
    year_of_birth = forms.IntegerField(required=False)
    year_of_employment = forms.IntegerField(required=False)
    about = forms.CharField(widget=forms.Textarea, required=False)
    phone_number = forms.CharField(max_length=100, required=False)
    profession = forms.CharField(max_length=100, required=False)
    health_post_type = forms.CharField(max_length=100, required=False)
    hew_setting = forms.CharField(max_length=100, required=False)
    exclude_from_reporting = forms.BooleanField(
        required=False,
        help_text=_('If checked, the activity from this user will not be taken into account for summary '
                    'calculations and reports'))

    def __init__(self, allow_edit=True, *args, **kwargs):
        # Prepopulate initial data from UserProfile instance if provided
        instance = kwargs.pop('instance', None)
        if instance:
            initial = kwargs.get('initial', {})
            # Populate all new UserProfile fields
            for field in [
                'organisation', 'grand_father', 'participant_id', 
                'gender', 'education_level', 'region', 'region_uid', 'zone', 'zone_uid',
                'woreda', 'woreda_uid', 'phcu', 'phcu_uid', 'health_post', 'healthpost_uid',
                'year_of_birth', 'year_of_employment', 'about', 'phone_number',
                'Profession', 'health_post_type', 'hew_setting']:
                initial[field] = getattr(instance, field, '')
            kwargs['initial'] = initial

        super(ProfileForm, self).__init__(*args, **kwargs)

        userdata = kwargs.get('initial') \
            if 'initial' in kwargs else kwargs.get('data')
        email = userdata.get('email', None)
        username = userdata.get('username', None)

        helpers.custom_fields(self)

        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.label_class = 'col-lg-2 col-md-3 col-sm-4'
        self.helper.field_class = 'col-lg-5 col-md-8 col-sm-8'

        self.helper.layout = Layout()

        if SettingProperties.get_bool(
                constants.OPPIA_SHOW_GRAVATARS,
                settings.OPPIA_SHOW_GRAVATARS):
            gravatar_url = "https://www.gravatar.com/avatar.php?"
            gravatar_id = hashlib.md5(str(email).encode('utf-8')).hexdigest()
            gravatar_url += urllib.parse.urlencode({
                'gravatar_id': gravatar_id,
                'size': 64
            })
            self.gravatar = FormHelper()
            self.gravatar.form_tag = False
            self.gravatar.layout = Layout(
                Div(
                    HTML("""<label class="control-label col-lg-2">"""
                         + _(u'Photo') + """</label>"""),
                    Div(
                        HTML(mark_safe(
                            '<img src="{0}" alt="gravatar for {1}" \
                            class="gravatar" width="{2}" height="{2}"/>'
                            .format(gravatar_url, username, 64))),
                        HTML("""<br/>"""),
                        HTML("""<a href="https://www.gravatar.com">"""
                             + _(u'Update gravatar') + """</a>"""),
                        css_class="col-lg-4",
                    ),
                    css_class="form-group",
                )
            )

        if not allow_edit:
            # Set fields as read-only if the user is not allow to edit their
            # profile
            for key, field in self.fields.items():
                if not key.startswith('password'):
                    field.widget.attrs.update({'readonly': 'readonly'})

        self.helper.layout.extend([
            'organisation',
            'grand_father',
            'participant_id',
            'gender',
            'education_level',
            'region',
            'region_uid',
            'zone',
            'zone_uid',
            'woreda',
            'woreda_uid',
            'phcu',
            'phcu_uid',
            'health_post',
            'healthpost_uid',
            'year_of_birth',
            'year_of_employment',
            'about',
            'phone_number',
            'profession',
            'health_post_type',
            'hew_setting',
        ])

        custom_fields = CustomField.objects.all().order_by('order')
        # Training Profile Table before Change Password
        self.helper.layout.append(HTML('''
    <div class="p-4">
        {# Training Profile Table before Change Password #}
        <h4>Training Profile</h4>
        <div class="table-responsive">
            <table class="table table-bordered table-sm">
                <thead>
            <thead>
                <tr>
                    <th>Training Date</th>
                    <th>Module Type</th>
                    <th>Custom Field 1</th>
                    <th>Custom Field 2</th>
                    <th>Custom Field 3</th>
                    <th>Edit</th>
                </tr>
            </thead>
            <tbody>
                {% for training_id, fields in customfields_by_training.items %}
                    {% with training=fields.0.training_info %}
                    <tr>
                        <td>{% if training %}{{ training.training_date }}{% else %}N/A{% endif %}</td>
                        <td>{% if training %}{{ training.module_type }}{% else %}N/A{% endif %}</td>
                        <td>{% if fields|length > 0 %}{{ fields.0.get_value }}{% endif %}</td>
                        <td>{% if fields|length > 1 %}{{ fields.1.get_value }}{% endif %}</td>
                        <td>{% if fields|length > 2 %}{{ fields.2.get_value }}{% endif %}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" data-toggle="modal" data-target="#editCustomFieldModal{{ training_id }}">Edit</button>
                            <!-- Modal for editing custom fields -->
                            <div class="modal fade" id="editCustomFieldModal{{ training_id }}" tabindex="-1" role="dialog" aria-labelledby="editCustomFieldModalLabel{{ training_id }}" aria-hidden="true">
                                <div class="modal-dialog" role="document">
                                    <div class="modal-content">
                                        <form method="post" action="{% url 'profile:edit_customfield' training_id=view_user.id training_info_id=training_id %}">
                                            {% csrf_token %}
                                            <div class="modal-header">
                                                <h5 class="modal-title" id="editCustomFieldModalLabel{{ training_id }}">Edit Custom Fields</h5>
                                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                                    <span aria-hidden="true">&times;</span>
                                                </button>
                                            </div>
                                            <div class="modal-body">
                                                {% for field in fields %}
                                                    <div class="form-group">
                                                        <label>{{ field.key_name.label }}</label>
                                                        <input type="text" class="form-control" name="customfield_{{ field.id }}" value="{{ field.get_value }}">
                                                    </div>
                                                {% endfor %}
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                                                <button type="submit" class="btn btn-primary">Save changes</button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </td>
                    </tr>
                    {% endwith %}
                {% empty %}
                    <tr><td colspan="6">No custom fields found.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
        '''))

        self.helper.layout.extend([
            Div(
                HTML("""<h4 class='mt-5 mb-3'>"""
                     + _(u'Change password') + """</h4>"""),
            ),
            Div(HTML("""<div style='clear:both'></div>""")),
            'password',
            'password_again',
            Div(
                Submit('submit',
                       _(u'Save Profile'),
                       css_class='btn btn-default mt-3'),
                css_class='text-center col-lg-offset-2 col-lg-6',
            )])

    def clean(self):
        cleaned_data = self.cleaned_data
        # check email not used by anyone else
        email = cleaned_data.get("email")
        username = cleaned_data.get("username")

        if email and User.objects.exclude(username__exact=username) \
                .filter(email=email).exists():
            raise forms.ValidationError(_(u"Email address already in use"))

        # if password entered then check they are the same
        password = cleaned_data.get("password")
        password_again = cleaned_data.get("password_again")
        if password and password_again and password != password_again:
            raise forms.ValidationError(_(u"Passwords do not match."))

        return cleaned_data
