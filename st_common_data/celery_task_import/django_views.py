from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from st_common_data.celery_task_import.handlers import CeleryTaskFormator
from st_common_data.auth.django_auth import Auth0ServiceAuthentication


class CeleryTasksImportView(APIView):
    authentication_classes = (Auth0ServiceAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, *args, **kwargs):
        handler = CeleryTaskFormator(settings.CELERY_TASK_DEFAULT_QUEUE)
        handler.run()
        return Response(handler.result)
