import mimetypes

import gridfs
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import connection
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class GridFSStorage(Storage):
    """Keep uploaded files (event posters) inside MongoDB Atlas instead of on the local disk."""

    bucket_name = "media"

    @property
    def _bucket(self):
        return gridfs.GridFSBucket(connection.database, bucket_name=self.bucket_name)

    def _latest(self, name):
        return next(iter(self._bucket.find({"filename": name}).sort("uploadDate", -1).limit(1)), None)

    def _open(self, name, mode="rb"):
        if self._latest(name) is None:
            raise FileNotFoundError(name)
        stream = self._bucket.open_download_stream_by_name(name)
        file = ContentFile(stream.read(), name=name)
        file.content_type = (stream.metadata or {}).get("contentType")
        return file

    def _save(self, name, content):
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0]
        if hasattr(content, "seek"):
            content.seek(0)
        self._bucket.upload_from_stream(name, content, metadata={"contentType": content_type})
        return name

    def delete(self, name):
        for grid_file in self._bucket.find({"filename": name}):
            self._bucket.delete(grid_file._id)

    def exists(self, name):
        return self._latest(name) is not None

    def size(self, name):
        grid_file = self._latest(name)
        if grid_file is None:
            raise FileNotFoundError(name)
        return grid_file.length

    def get_modified_time(self, name):
        grid_file = self._latest(name)
        if grid_file is None:
            raise FileNotFoundError(name)
        return grid_file.upload_date

    def url(self, name):
        return reverse("media_file", args=[name])
