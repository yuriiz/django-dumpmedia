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


def _dump(models: List[str], out, compress) -> None:
    buffer = BytesIO()
    with tarfile.open(
        "media",
        "w|gz" if compress else "w",
        fileobj=buffer,
    ) as tar:
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


def _streaming_content(models: List[str], compress: bool) -> Iterator[bytes]:
    ours, theirs = Pipe()
    # workaround for https://code.djangoproject.com/ticket/32798
    t = Thread(target=_dump, args=(models, theirs, compress))
    t.start()
    while True:
        try:
            yield ours.recv_bytes()
        except EOFError:
            break
    t.join()


def dumpmedia(request: HttpRequest) -> StreamingHttpResponse:
    compress = "nocompress" not in request.GET
    return StreamingHttpResponse(
        _streaming_content(request.GET.getlist("model"), compress),
        content_type="application/x-tar",
        headers={
            "Content-Disposition": 'attachment; filename="media.tar{}"'.format(
                ".gz" if compress else ""
            )
        },
    )
