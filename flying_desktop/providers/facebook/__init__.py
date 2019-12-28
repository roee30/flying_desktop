from pathlib import Path
from typing import AsyncIterator, Sequence, Iterable

import attr
import facebook
from furl import Path as URLPath

from flying_desktop.utils import delegate
from ...providers import Photo, SettingsStorage, PhotoProvider

HERE = Path(__file__).parent

ACCESS_TOKEN_EXPIRED = 190


@attr.s(frozen=True)
class APIPath:
    """
    Represents a URL path relative to an API root
    :param api: Graph API instance
    :param path: Relative URL path
    """

    provider: 'FacebookPhotos' = attr.ib()
    path: URLPath = attr.ib(converter=URLPath, default="")
    retries: int = attr.ib(default=1)

    def __call__(self, **kwargs):
        """
        Call URL path with ``kwargs`` as query parameters
        :param kwargs: query string parameters
        """
        try:
            return self.provider.api.request(str(self.path), args=kwargs)
        except facebook.GraphAPIError as ex:
            print(ex.result)
            if not self.retries or ex.code != ACCESS_TOKEN_EXPIRED:
                raise
        self.provider.renew_token()
        # one retry
        return attr.evolve(self, retries=self.retries - 1)(**kwargs)

    def __getattr__(self, item):
        """
        append ``/item`` to the end of the path
        """
        return attr.evolve(self, path=self.path / item)


class FacebookPhotos(PhotoProvider):
    """
    Facebook photos provider
    """

    batch_size = 500
    storage = SettingsStorage("facebook/token.json")
    client_secrets = HERE / "credentials.json"
    scope = "user_photos"

    def __init__(self, credentials):
        # super().__init__(credentials)
        super().__init__(credentials)
        self.api = facebook.GraphAPI(access_token=credentials.access_token, version=3.1)
        self.graph = APIPath(self)

    def renew_token(self):
        self.storage.delete()
        credentials = self.authorization_code_grant()
        super().__init__(credentials)
        self.api = facebook.GraphAPI(access_token=credentials.access_token, version=3.1)

    async def download_photo(self, meta_photo: dict) -> Photo:
        return await self._download_from_url(meta_photo["images"][0]["source"])

    async def download_meta_photos(self) -> AsyncIterator[Sequence[dict]]:
        result = await self.download_meta_photos_page()
        yield result["data"]
        while "next" in result["paging"]:
            result = await self.download_meta_photos_page(
                result["paging"]["cursors"]["after"]
            )
            yield result["data"]

    async def download_meta_photos_page(self, cursor=None) -> dict:
        """
        Retrieve one page of photo metadata
        :param cursor: cursor returned in previous request
        :return: next page of photo metadata
        """
        return await delegate(
            lambda: self.graph.me.photos(
                type="uploaded",
                **(dict(after=cursor) if cursor else {}),
                fields="images",
                limit=self.batch_size,
            )
        )

    @staticmethod
    def filter_meta_photos(photos: Iterable[dict], min_width: int) -> Sequence[dict]:
        return list(
            filter(lambda photo: photo["images"][0]["width"] >= min_width, photos)
        )
