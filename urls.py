from .views import (
    register, register_delete, login, menu, update_task, task_create, delete_taks_list, delete_task,
    tasks_list, all_tasks_views, error_continued, settings_view, user_data, user_profile, edit_profile,
    task_info, task_info_grade, task_info_comment, delete_comment, wallet, buy_subscription,
)
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView

def catch_all_redirect(request, path=None):
    if request.user.is_authenticated:
        return redirect('menu', id=str(request.user.id))
    else:
        return redirect('menu', id='none')

urlpatterns = [
    path('', lambda request: redirect('menu', id=request.user.id if request.user.is_authenticated else 'none')),
    path('register', register, name='register'),
    path('register-delete', register_delete, name='register-delete'),
    path('login', login, name='login'),
    path('logout/', LogoutView.as_view(next_page='/login'), name='logout'),
    path('menu/<str:id>', menu, name='menu'),
    path('task-create/<int:user_id>', task_create, name='task-create'),
    path('tasks-list/<str:id>', tasks_list, name='tasks-list'),
    path('update_task/<int:user_id>/<int:task_id>', update_task, name='update_task'),
    path('delete_taks_list/<int:id>', delete_taks_list, name='delete_taks_list'),
    path('delete_task/<int:id>', delete_task, name='delete-task'),
    path('task-info/<int:task_id>/', task_info, name='task-info'),
    path('task-info/<int:task_id>/grade/', task_info_grade, name='task_info_grade'),
    path('task-info/<int:task_id>/comment/', task_info_comment, name='task_info_comment'),
    path('delete-comment/<int:comment_id>/', delete_comment, name='delete-comment'),
    path('all-tasks-views', all_tasks_views, name='all-tasks-views'),
    path('error-continued', error_continued, name='error-continued'),
    path('settings', settings_view, name='settings'),
    path('user-data', user_data, name='user-data'),
    path('user-profile/<str:id>', user_profile, name='user-profile'),
    path('edit-profile', edit_profile, name='edit-profile'),
    path('wallet', wallet, name='wallet'),
    path('buy-subscription', buy_subscription, name='buy_subscription'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^(?P<path>.*)$', catch_all_redirect),
]
