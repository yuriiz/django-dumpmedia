import logging
import tarfile
from io import BytesIO
from threading import Thread
from typing import Iterator, List
from multiprocessing import Pipe

from django.apps import apps
from django.db.models import FileField
from django.http import HttpRequest, StreamingHttpResponse

logger = logging.getLogger(__name__)


def _dump(models: List[str], out) -> None:
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
            for obj in Model.objects.only(*fields).iterator():
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
                            logger.exception(f"Failed to read {value.name}.")
                out.send_bytes(buffer.getvalue())
                buffer.seek(0)
                buffer.truncate()
    out.send_bytes(buffer.getvalue())
    out.close()


def _streaming_content(models: List[str]) -> Iterator[bytes]:
    ours, theirs = Pipe()
    # workaround for https://code.djangoproject.com/ticket/32798
    t = Thread(target=_dump, args=(models, theirs))
    t.start()
    while True:
        try:
            yield ours.recv_bytes()
        except EOFError:
            break
    t.join()


def dumpmedia(request: HttpRequest) -> StreamingHttpResponse:
    return StreamingHttpResponse(
        _streaming_content(request.GET.getlist("model")),
        content_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="media.tar.gz"'},
    )
