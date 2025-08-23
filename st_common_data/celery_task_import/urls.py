from django.urls import path

from st_common_data.celery_task_import.django_views import CeleryTasksImportView

urlpatterns = [
    path('', CeleryTasksImportView.as_view(), name='import_tasks'),
]
