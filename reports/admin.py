from django.contrib import admin

from helpers.mixins.PermissionMixins import ReadOnlyAdminMixin
from reports.models import DashboardAccessLog


class DashboardAccessLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'access_date', 'url', 'ip', 'data')
    search_fields = ['user__username']


admin.site.register(DashboardAccessLog, DashboardAccessLogAdmin)
