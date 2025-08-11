import datetime
import requests
import json
import re
import logging
from typing import Optional, Type
from urllib.request import urlopen
from st_common_data.redis import MasterSlavesRedis

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


def proceed_user_agent(user_agent):
    pattern = r"([\w\d-]*)(?:\/([\.0-9]*))?(?: (.*))?"

    if not user_agent:
        raise ValueError("UserAgent is None")

    result = re.fullmatch(pattern, user_agent)

    if not result:
        raise ValueError("UserAgent is invalid")

    app_name, version, env = result.groups()
    data = {
        "app_name": app_name,
        "version": version,
        "env": env,
    }

    if not app_name:
        raise ValueError("App Name not found in UserAgent")

    return data


class JWKS(metaclass=SingletonMeta):
    """
    Auth0 json web keys set for local token verification
    """

    def __init__(self, auth0_domain: str, auth_exception: Type[Exception]):
        self.auth0_domain: str = auth0_domain
        self.auth_exception = auth_exception
        self._jwks_keys: dict = dict()

        self._update_jwks()

    def get_rsa_key(self, kid: str) -> Optional[dict]:
        try:
            return self._jwks_keys[kid]
        except KeyError:
            self._update_jwks()
            if kid not in self._jwks_keys:
                raise self.auth_exception('Unable to find appropriate key')
            return self._jwks_keys[kid]

    def _update_jwks(self):
        jsonurl = urlopen(f"https://{self.auth0_domain}/.well-known/jwks.json")
        self._jwks_keys = dict()
        for key in json.loads(jsonurl.read())['keys']:
            self._jwks_keys[key['kid']] = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]}


class ServiceAuth0Token(metaclass=SingletonMeta):
    """
    Auth0 token from service app for machine-to-machine communication (between services)
    """
    token_name = 'service_token'

    def __init__(self,
                 audience: str,
                 grant_type: str,
                 client_id: str,
                 client_secret: str,
                 services_token_url: str,
                 redi_url: str):
        self.audience = audience
        self.grant_type = grant_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = services_token_url
        self.redi_url = redi_url

    @property
    def token(self):
        redis_client = MasterSlavesRedis.from_url(self.redi_url)
        raw_data = redis_client.get(self.token_name)
        if raw_data:
            data = json.loads(raw_data)
            token = data['token']
            expiration_str = data['expiration_time']
            expiration = datetime.datetime.strptime(expiration_str, '%Y-%m-%d %H:%M:%S %Z')

            if expiration < datetime.datetime.utcnow():
                return self._update_token()
            return token
        else:
            return self._update_token()

    def _update_token(self):
        token_data = self._get_token()
        token = token_data['access_token']
        logger.info(f'{self.token_name} token was created!')
        expiration = datetime.datetime.utcnow().astimezone(tz=datetime.timezone.utc) + datetime.timedelta(
            seconds=token_data['expires_in'] - 10 * 60)
        data = {
            'token': token,
            'expiration_time': expiration.strftime('%Y-%m-%d %H:%M:%S %Z')
        }

        redis_client = MasterSlavesRedis.from_url(self.redi_url)
        redis_client.set(self.token_name, json.dumps(data))

        return token

    def _get_token(self, retry: int = 2):
        response = requests.post(
            url=self.token_url,
            data={
                'audience': self.audience,
                'grant_type': self.grant_type,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            while retry > 0:
                self._get_token(retry=retry - 1)
            try:
                details = response.json()
            except:
                details = response.text
            raise Exception(f'Unable to get token, status code: {response.status_code}. Server returned: {details}')

    def __str__(self):
        return self.token


class ManagementAuth0Token(ServiceAuth0Token):
    """
    Auth0 token from management app for communication with auth0 API
    """
    token_name = 'management_token'


class ServiceCAPAuth0Token(ServiceAuth0Token):
    """
    Auth0 CAP token
    """
    token_name = 'cap_service_token'
