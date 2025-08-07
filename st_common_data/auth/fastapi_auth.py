import importlib
from dataclasses import dataclass
import logging

import jose.exceptions
from fastapi import Request, Depends
from jose import jwt
from fastapi_exceptions.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.settings import config
from . import proceed_user_agent

UserModel = getattr(
    importlib.import_module('app.models'), config.auth_user_model
)  # in tier_system AUTH_USER_MODEL="UserDataModel"
from . import JWKS, ServiceAuth0Token, ManagementAuth0Token


jwks = JWKS(auth0_domain=config.auth0_domain, auth_exception=AuthenticationFailed)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class User:
    admin: bool
    user_data: UserModel
    claims: dict


def is_tier_admin(claims: dict) -> bool:
    if 'permissions' in claims and config.auth0_admin_permission in claims['permissions']:
        return True
    else:
        return False


class Auth0Authentication:
    async def authenticate_request(
        self, request: Request,
        audience: str = config.auth0_oa_api_audience
    ) -> dict:
        authorization = request.headers.get('authorization', None)
        if authorization is None:
            raise AuthenticationFailed(
                detail='No authorization header')

        raw_token = self.get_raw_token(authorization)
        if raw_token is None:
            raise AuthenticationFailed(
                detail='Empty authorization header')

        claims = await self.authenticate(raw_token, audience)
        self.check_user_agent(request=request, claims=claims)

        return claims

    @staticmethod
    async def authenticate(raw_token, audience) -> dict:
        # Validation of token, if token is invalid - exception would be raised
        try:
            unverified_header = jwt.get_unverified_header(raw_token)
        except jose.exceptions.JWTError:
            raise AuthenticationFailed(
                detail='Error decoding token headers')

        try:
            rsa_key = jwks.get_rsa_key(unverified_header["kid"])
            payload = jwt.decode(
                raw_token,
                rsa_key,
                algorithms=["RS256"],
                audience=audience,
                issuer=f'https://{config.auth0_domain}/')
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed(
                detail='Token is expired')
        except jwt.JWTClaimsError as e:
            raise AuthenticationFailed(
                detail='Incorrect claims, please check the audience and issuer')
        except Exception:
            raise AuthenticationFailed(
                detail='Unable to parse authentication header')

        return payload

    @staticmethod
    def get_raw_token(header):
        """
        Extracts an unvalidated JSON web token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            raise AuthenticationFailed(
                detail='Empty authorization header')

        if len(parts) != 2:
            raise AuthenticationFailed(
                detail='Authorization header must contain two space-delimited values')

        return parts[1]

    @staticmethod
    def check_user_agent(request: Request, claims: dict) -> None:
        user_agent = request.headers.get('user-agent', None)
        try:
            proceed_user_agent(user_agent)
        except ValueError as e:
            if config.user_agent_strict:
                return ValidationError({"error": str(e)})
            logger.warning(str(e))

        if 'sub' in claims:
            auth0_id = claims['sub'].split('|')[1]
        else:
            auth0_id = 'service_token'
        logger.info(f"Request to '{request.url.path}' from '{user_agent}' {auth0_id}")


auth_backend = Auth0Authentication()


async def get_current_user_tp(
    request: Request,
    session: Session = Depends(get_db),
) -> User:
    claims = await auth_backend.authenticate_request(request, audience=config.auth0_tp_api_audience)
    return await get_user_from_claims(claims, session)


async def get_current_user(
    request: Request,
    session: Session = Depends(get_db),
) -> User:
    claims = await auth_backend.authenticate_request(request)
    return await get_user_from_claims(claims, session)


async def get_current_service(
    claims: dict = Depends(auth_backend.authenticate_request)
):
    if 'azp' in claims and claims['azp'] == config.auth0_service_client_id:
        return claims
    else:
        raise PermissionDenied


async def get_user_from_claims(
    claims: dict,
    session: Session,
) -> User:
    try:
        sub = claims['sub']
        sub_list = sub.split('|')
        auth_provider = sub_list[0]
        auth0_user_id = sub_list[1]
        if auth_provider != 'auth0':
            raise AuthenticationFailed(detail='Not auth0 user')
    except KeyError:
        raise AuthenticationFailed(detail='No sub in token')
    except Exception:
        raise AuthenticationFailed(detail='Invalid sub in token')

    try:
        user_data = session.query(UserModel).filter(UserModel.auth0 == auth0_user_id).one()
    except NoResultFound:
        raise PermissionDenied
    return User(
        admin=is_tier_admin(claims),
        user_data=user_data,
        claims=claims)


service_auth0_token = ServiceAuth0Token(
    audience=config.auth0_oa_api_audience,
    grant_type='client_credentials',
    client_id=config.auth0_service_client_id,
    client_secret=config.auth0_service_client_secret,
    services_token_url=config.auth0_service_token_url,
    redi_url=config.redis_cache
)
management_auth0_token = ManagementAuth0Token(
    audience=config.auth0_management_api_audience,
    grant_type='client_credentials',
    client_id=config.auth0_management_client_id,
    client_secret=config.auth0_management_client_secret,
    services_token_url=config.auth0_management_token_url,
    redi_url=config.redis_cache
)
