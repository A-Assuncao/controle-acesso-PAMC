import os
import sys
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "controle_acesso.settings")
    port = os.environ.get("HTTP_PLATFORM_PORT", "8000")
    sys.argv = ["manage.py", "runserver", f"0.0.0.0:{port}"]
    execute_from_command_line(sys.argv)
