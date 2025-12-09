from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
# Register your models here.


class UserModel(UserAdmin):
    ordering = ('email',)


admin.site.register(CustomUser, UserModel)
admin.site.register(Staff)
admin.site.register(Video)
admin.site.register(VideoComment)
admin.site.register(VideoLike)
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(NewsAndEvents)
admin.site.register(Session)
