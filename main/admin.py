from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .models import Portfolio, Project, Feedback


class CustomUserAdmin(UserAdmin):

    list_display = ['email', 'username', ]


admin.site.register(get_user_model(), CustomUserAdmin)

admin.site.register([Portfolio, Project, Feedback])
