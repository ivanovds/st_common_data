__all__ = ('BaseError', 'UnhealthComponentError', 'DegradedComponentError',)


class BaseError(Exception):
    pass


class UnhealthComponentError(BaseError):
    pass


class DegradedComponentError(BaseError):
    pass
