# django-dumpmedia

Django view for downloading backup of all media files.

## Install

```bash
pip install git+https://github.com/yuriiz/django-dumpmedia.git
```

## Usage

1. Add `dumpmedia.views.dumpmedia` to `urls.py`.

```python
from dumpmedia.views import dumpmedia

urlpatterns = [
    ...
    path("dumpmedia/", user_passes_test(lambda u: u.is_superuser)(dumpmedia)),
    ...
]
```

2. Visit http://127.0.0.1:8000/dumpmedia/ to download all media files or http://127.0.0.1:8000/dumpmedia/?model=MyModel to download all media files related to model `MyModel`.
