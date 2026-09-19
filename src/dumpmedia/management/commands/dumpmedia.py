from django.core.management.base import BaseCommand, CommandError
import tarfile
from django.db.models import FileField
from django.apps import apps


class Command(BaseCommand):
    help = "Dump media"

    def add_arguments(self, parser):
        parser.add_argument("models", nargs="*")

    def handle(self, *args, **options):
        models = options["models"]
        with tarfile.open("media.tar.gz", "w|gz") as tar:
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
                                self.stdout.write(
                                    self.style.ERROR(f"Failed to read {value.name}.")
                                )
                            else:
                                if options["verbosity"] > 1:
                                    self.stdout.write(
                                        self.style.SUCCESS(f"Added {value.name}")
                                    )
