# Generated by Django 3.2.13 on 2022-06-13 13:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DataRecovery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('data_type', models.CharField(choices=[('activity_log', 'Activity log'),
                                                        ('tracker', 'Tracker'),
                                                        ('quiz', 'Quiz'),
                                                        ('user_profile', 'User profile')],
                                               max_length=13)),
                ('reasons', models.CharField(blank=True, max_length=500, null=True)),
                ('data', models.TextField()),
                ('recovered', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True,
                                           null=True,
                                           on_delete=django.db.models.deletion.CASCADE,
                                           to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
