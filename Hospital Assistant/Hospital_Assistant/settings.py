"""Environment selector for Django settings modules."""

import os
import sys


if "test" in sys.argv:
    from .settings_test import *  # noqa: F401,F403
else:
    environment = os.getenv("DJANGO_ENV", "dev").strip().lower()
    if environment == "prod":
        from .settings_prod import *  # noqa: F401,F403
    else:
        from .settings_dev import *  # noqa: F401,F403


LOGIN_REDIRECT_URL = 'role_dashboard'
