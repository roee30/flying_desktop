from pathlib import Path
from typing import AsyncIterator, Sequence, Iterable

from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest as GoogleHttpRequest
from httplib2 import Http

from flying_desktop.utils import delegate
from .. import PhotoProvider, Photo, SettingsStorage

HERE = Path(__file__).parent


class GooglePhotos(PhotoProvider):
    """
    Google photos provider
    """

    max_batch_size = 100
    storage = SettingsStorage("google/token.json")
    client_secrets = HERE / "credentials.json"
    scope = "https://www.googleapis.com/auth/photoslibrary.readonly"

    def __init__(self, credentials):
        super().__init__(credentials)
        self.service = build(
            "photoslibrary",
            "v1",
            credentials=credentials,
            requestBuilder=lambda _, *args, **kwargs: GoogleHttpRequest(
                credentials.authorize(Http()), *args, **kwargs
            ),
        )

    async def get_photo(self, photo_id, fields=None):
        """
        Get metadata for photo
        :param photo_id: ID of photo
        :param fields: fields to include in response
        :return: photo metadata
        """
        return await delegate(
            lambda: self.service.mediaItems()
            .get(mediaItemId=photo_id, fields=fields)
            .execute()
        )

    async def download_photo(self, meta_photo: dict) -> Photo:
        photo_id = meta_photo["id"]
        url = (await self.get_photo(photo_id, fields="baseUrl"))["baseUrl"] + "=d"
        return await self._download_from_url(url)

    async def download_meta_photos(self) -> AsyncIterator[Sequence[dict]]:
        result = await self.download_meta_photos_page()
        yield result["mediaItems"]
        while "nextPageToken" in result:
            result = await self.download_meta_photos_page(result["nextPageToken"])
            yield result["mediaItems"]

    async def download_meta_photos_page(self, page_token=None):
        """
        Retrieve one page of photo metadata
        :param page_token: token returned in previous request
        :return: next page of photo metadata
        """
        fields = "nextPageToken,mediaItems(id,mediaMetadata(width,height))"
        return await delegate(
            lambda: (
                self.service.mediaItems()
                .search(
                    fields=fields,
                    body={
                        "filters": {
                            "contentFilter": {"includedContentCategories": ["PEOPLE"]},
                            "mediaTypeFilter": {"mediaTypes": ["PHOTO"]},
                        },
                        "pageSize": self.max_batch_size,
                        **({"pageToken": page_token} if page_token else {}),
                    },
                )
                .execute()
            )
        )

    @staticmethod
    def filter_meta_photos(photos: Iterable[dict], min_width: int) -> Sequence[dict]:
        return list(
            filter(
                lambda photo: int(photo["mediaMetadata"]["width"]) >= min_width, photos
            )
        )


def make_url(photo):
    return photo["baseUrl"] + "=d"
