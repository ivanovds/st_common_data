import inspect
from celery import current_app
from typing import get_origin, get_args


class CeleryTaskFormator:
    def __init__(self, service_name_queue: str):
        self.result = {
            "service_name_queue": service_name_queue,
            "service_tasks": list()
        }

    def get_argument_type(self, type_entityn) -> str | None:
        if type_entityn is inspect._empty:
            return None
        origin = get_origin(type_entityn)
        args = get_args(type_entityn)

        # Plain type like int, str, dict
        if origin is None:
            return getattr(type_entityn, "__name__", str(type_entityn))

        return f"{origin.__name__}[{', '.join(self.get_argument_type(a) for a in args)}]"

    @staticmethod
    def get_argument_default(default_entity) -> str | None:
        return None if hasattr(default_entity, '__name__') else default_entity

    def run(self):
        custom_tasks = {
            name: task for name, task in current_app.tasks.items()
            if not name.startswith('celery.')
        }

        for name, task in custom_tasks.items():
            task_result = {
                'function_name': name,
                'arguments': list()
            }

            sig = inspect.signature(task.run)
            for param in sig.parameters.values():
                argument_type = self.get_argument_type(param.annotation)
                default_value = self.get_argument_default(param.default)

                task_result['arguments'].append(
                    {
                        'argument_name': param.name,
                        'argument_type': argument_type,
                        'default_value': default_value
                    }
                )

            self.result['service_tasks'].append(task_result)
