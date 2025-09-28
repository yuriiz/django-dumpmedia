import logging
import tarfile
from io import BytesIO
from threading import Thread
from typing import Iterator, List

from django.apps import apps
from django.db.models import FileField
from django.http import HttpRequest, StreamingHttpResponse

logger = logging.getLogger(__name__)


def _streaming_content(models: List[str]) -> Iterator[bytes]:
    buffer = BytesIO()
    with tarfile.open("media.tar.gz", "w|gz", fileobj=buffer) as tar:
        for Model in apps.get_models():
            if models and Model._meta.verbose_name not in models:
                continue
            fields = [
                f.name
                for f in Model._meta.get_fields()
                if isinstance(
                    f,
                    FileField,
                )
            ]
            if not fields:
                continue

            def _dump():
                for obj in Model.objects.iterator():
                    for field in fields:
                        value = getattr(obj, field)
                        if value:
                            try:
                                with value.open() as f:
                                    tar.addfile(
                                        tar.gettarinfo(value.name, value.name, f),
                                        f,
                                    )
                            except IOError:
                                logger.exception(
                                    f"Failed to read file stored in {field} of {obj}."
                                )

            # workaround for https://code.djangoproject.com/ticket/32798
            t = Thread(target=_dump)
            t.start()
            t.join()
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
    yield buffer.getvalue()


def dumpmedia(request: HttpRequest) -> StreamingHttpResponse:
    return StreamingHttpResponse(
        _streaming_content(request.GET.getlist("model")),
        content_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="media.tar.gz"'},
    )
