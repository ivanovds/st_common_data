"""
Backend classes for different storages.
"""
from storages.backends.gcloud import GoogleCloudStorage


class StaticGoogleCloudStorage(GoogleCloudStorage):
    """
    Storage for static files in Google Cloud Storage.
    """
    location = 'static'
    default_acl = 'publicRead'
    allow_overwrite = True



__all__ = (
    'StaticGoogleCloudStorage',
)