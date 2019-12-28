"""
A bucket is a combination of the means to fetch remote photos
and the metadata of the photos already fetched.
"""
from typing import Sequence, Callable

import attr

from .providers import PhotoProvider
from .providers.facebook import FacebookPhotos
from .providers.google import GooglePhotos
from .settings import SETTINGS
from .utils import delegate

attrs = attr.s(auto_attribs=True, kw_only=True)


@attr.s(auto_attribs=True, frozen=True)
class BucketFactory:
    """
    Factory for making empty buckets.
    :param name: Name of method for fetching remote photos
    :param description: description of said method
    :param init: coroutine yielding a ``PhotoProvider``
    """

    name: str
    description: str
    init: Callable[[], PhotoProvider]

    def new(self, **kwargs):
        return EmptyBucket(**attr.asdict(self), **kwargs)


@attrs
class PhotoBucket:
    name: str
    description: str
    checked: bool = True

    @property
    def _credentials_key(self):
        return f"{self.name}/connected"


@attrs
class FilledBucket(PhotoBucket):
    client: PhotoProvider

    def __attrs_post_init__(self):
        self._photos = []

    async def download(self):
        async for batch in self.client.download_meta_photos():
            self._photos += batch
            yield

    def select(self, min_width):
        return self.client.filter_meta_photos(self.photos, min_width)

    @property
    def photos(self) -> Sequence[dict]:
        return self._photos

    def empty(self):
        SETTINGS[self._credentials_key] = False
        self.client.clear()


@attrs
class EmptyBucket(PhotoBucket):
    _init: Callable[[], PhotoProvider]

    @property
    def photos(self):
        return []

    async def fill(self) -> FilledBucket:
        SETTINGS[self._credentials_key] = True
        return FilledBucket(
            name=self.name,
            description=self.description,
            client=await delegate(self._init),
        )

    def has_credentials(self):
        return SETTINGS.get(self._credentials_key, False)


Google = BucketFactory(
    name="Google",
    description="Connect to Google Photos",
    init=GooglePhotos.from_code_grant,
)

Facebook = BucketFactory(
    name="Facebook",
    description="Connect to your Facebook photos",
    init=FacebookPhotos.from_code_grant,
)
