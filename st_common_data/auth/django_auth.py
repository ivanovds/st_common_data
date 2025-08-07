import logging
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import HTTP_HEADER_ENCODING, authentication
from rest_framework.exceptions import AuthenticationFailed, ValidationError
import jose.exceptions
from jose import jwt

from . import JWKS, ServiceAuth0Token, ManagementAuth0Token, proceed_user_agent

UserModel = get_user_model()
logger = logging.getLogger('django')


jwks = JWKS(auth0_domain=settings.AUTH0_DOMAIN, auth_exception=AuthenticationFailed)


class Filter:
    def __init__(self, *args, **kwargs):
        pass

    def exists(self):
        """give all group permission for service user"""
        return True


class QS:
    filter = Filter


class ServiceUser:
    """Dummy user for auth of services that use okta Service Credential flow"""
    def __init__(self):
        self.is_authenticated = True  # for IsAuthenticated permission class
        self.groups = QS  # for all groups permissions


class Auth0Authentication(authentication.BaseAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header.
    """
    www_authenticate_realm = 'api'
    auth0_api_audience = settings.AUTH0_API_AUDIENCE
    auth0_service_client_id = settings.AUTH0_SERVICE_CLIENT_ID

    def authenticate(self, request):
        authorization = request.headers.get("authorization", None)
        user_agent = request.headers.get("user-agent", None)

        if authorization is None:
            return None

        raw_token = self.get_raw_token(authorization)
        if raw_token is None:
            return None

        try:
            unverified_header = jwt.get_unverified_header(raw_token)
        except jose.exceptions.JWTError:
            raise AuthenticationFailed(
                detail='Error decoding token headers')

        rsa_key = jwks.get_rsa_key(unverified_header["kid"])
        try:
            claims = jwt.decode(
                raw_token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.auth0_api_audience,
                issuer=f'https://{settings.AUTH0_DOMAIN}/')
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed(
                detail='Token is expired')
        except jwt.JWTClaimsError:
            return None  # try another authentication instance
        except Exception:
            raise AuthenticationFailed(
                detail='Unable to parse authentication header')

        user = self.get_user(claims)

        self.check_user_agent(user_agent)
        logger.info(f"Request to '{request.path_info}' from '{user_agent}' "
                    f"{user.auth0 if isinstance(user, UserModel) else user.__class__.__name__}")
        if not user:
            return None
        else:
            return user, claims

    @staticmethod
    def get_raw_token(header: str):
        """
        Extracts an unvalidated JSON web token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if len(parts) != 2:
            raise AuthenticationFailed(
                detail='Authorization header must contain two space-delimited values',
                code='bad_authorization_header',
            )

        return parts[1]

    def get_user(self, claims: dict) -> UserModel:
        try:
            sub = claims['sub']
            sub_list = sub.split('|')
            auth_provider = sub_list[0]
            user_id = sub_list[1]
            if auth_provider != 'auth0':
                return None
        except KeyError:
            raise AuthenticationFailed(detail='No sub in token')
        except Exception:
            return None

        try:
            return UserModel.objects.get(auth0=user_id)
        except (UserModel.DoesNotExist, KeyError):
            return None

    @staticmethod
    def check_user_agent(user_agent: str) -> None:
        try:
            proceed_user_agent(user_agent)
        except ValueError as e:
            if settings.USER_AGENT_STRICT:
                return ValidationError({"error": str(e)})
            logger.warning(str(e))


class Auth0ServiceAuthentication(Auth0Authentication):
    """
    An authentication plugin for service auth.
    """
    www_authenticate_realm = 'api'

    def get_user(self, claims):
        if 'azp' in claims and claims['azp'] == self.auth0_service_client_id:
            return ServiceUser()
        else:
            return None


class Auth0CAPServiceAuthentication(Auth0ServiceAuthentication):
    """
    An authentication plugin for service auth (for CAP api).
    """
    auth0_api_audience = settings.AUTH0_CAP_API_AUDIENCE
    auth0_service_client_id = settings.AUTH0_CAP_SERVICE_CLIENT_ID


class Auth0CAPAuthentication(Auth0Authentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header (for CAP api).
    """
    auth0_api_audience = settings.AUTH0_CAP_API_AUDIENCE


class Auth0PineServiceAuthentication(Auth0ServiceAuthentication):
    """
    An authentication plugin for service auth (for pine_api).
    """
    auth0_api_audience = settings.AUTH0_PINE_API_AUDIENCE
    auth0_service_client_id = settings.AUTH0_PINE_SERVICE_CLIENT_ID


class Auth0BackOfficeServiceAuthentication(Auth0ServiceAuthentication):
    """
    An authentication plugin for service auth (for bo_api).
    """
    auth0_api_audience = settings.AUTH0_BO_API_AUDIENCE
    auth0_service_client_id = settings.AUTH0_BO_SERVICE_CLIENT_ID


class Auth0PineAuthentication(Auth0Authentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header (for pine_api).
    """
    auth0_api_audience = settings.AUTH0_PINE_API_AUDIENCE


service_auth0_token = ServiceAuth0Token(
    audience=settings.AUTH0_API_AUDIENCE,
    grant_type='client_credentials',
    client_id=settings.AUTH0_SERVICE_CLIENT_ID,
    client_secret=settings.AUTH0_SERVICE_CLIENT_SECRET,
    services_token_url=settings.AUTH0_SERVICE_TOKEN_URL,
    redi_url=settings.REDIS_CACHE
)
management_auth0_token = ManagementAuth0Token(
    audience=settings.AUTH0_MANAGEMENT_API_AUDIENCE,
    grant_type='client_credentials',
    client_id=settings.AUTH0_MANAGEMENT_CLIENT_ID,
    client_secret=settings.AUTH0_MANAGEMENT_CLIENT_SECRET,
    services_token_url=settings.AUTH0_MANAGEMENT_TOKEN_URL,
    redi_url=settings.REDIS_CACHE
)
