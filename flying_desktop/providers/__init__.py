"""
Providers are the application's interface to different picture sources
"""
import abc
import json
from http import HTTPStatus
from pathlib import Path
from typing import AsyncIterator, Sequence, Iterable

import aiohttp
import attr
from oauth2client import client, tools
from oauth2client.client import Credentials

from flying_desktop.settings import SETTINGS


class AbstractClassProperty:
    """
    Abstract class member
    """

    __isabstractmethod__ = True


@attr.s
class Photo:
    """
    Photo and its content type, represented by conventional extension
    """

    suffix: str = attr.ib()
    data: bytes = attr.ib(repr=False)


class SettingsStorage(client.Storage):
    """
    Qt credentials storage for oauth2 tokens
    """

    def __init__(self, settings_path):
        super().__init__()
        self.settings_path = settings_path

    def locked_get(self):
        value = SETTINGS[self.settings_path]
        return value and Credentials.new_from_json(value)

    def locked_put(self, credentials: Credentials):
        SETTINGS[self.settings_path] = json.dumps(credentials.to_json())

    def locked_delete(self):
        return SETTINGS.remove(self.settings_path)


class PhotoProvider(metaclass=abc.ABCMeta):
    """
    Abstract class for photo providers
    """
    @abc.abstractmethod
    def __init__(self, credentials: client.OAuth2Credentials):
        pass

    @abc.abstractmethod
    async def download_meta_photos(self) -> AsyncIterator[Sequence[dict]]:
        """
        Download photo metadata
        """
        pass

    @abc.abstractmethod
    async def download_photo(self, meta_photo: dict) -> Photo:
        """
        Retrieve photo data from photo metadata
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def filter_meta_photos(photos: Iterable[dict], min_width: int) -> Sequence[dict]:
        """
        Filter meta photos by width
        :param photos: list of meta photos
        :param min_width: return all photos with width more than or equal to this value
        :return: list of matching photos
        """
        pass

    @staticmethod
    async def _download_from_url(url: str) -> Photo:
        """
        Download photo at ``url``, parsing its content type
        """
        async with aiohttp.ClientSession() as session, session.get(url) as response:
            general_type, suffix = response.headers["Content-Type"].split("/")
            if response.status != HTTPStatus.OK or general_type != "image":
                raise BadResponse(response)
            return Photo(suffix, await response.read())

    @classmethod
    def clear(cls):
        """
        Clear credentials storage
        """
        cls.storage.delete()

    storage: SettingsStorage = AbstractClassProperty()
    client_secrets: Path = AbstractClassProperty()
    scope: str = AbstractClassProperty()

    @classmethod
    def authorization_code_grant(cls, pkce: bool = True) -> client.OAuth2Credentials:
        """
        Execute the authorization code grant oauth2 flow
        :param pkce: execute Proof Key for Code Exchange from RFC 7636
        :return: oauth2 credentials resulting from flow
        """
        credentials = cls.storage.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(
                cls.client_secrets, scope=cls.scope, pkce=pkce
            )
            credentials = tools.run_flow(flow, cls.storage)
        return credentials

    @classmethod
    def from_code_grant(cls):
        """
        Instantiate provider using the authorization code grant
        """
        return cls(cls.authorization_code_grant())


@attr.s(hash=True, str=True)
class BadResponse(Exception):
    """
    An unexpected response or one indicating an error
    """
    response = attr.ib()
