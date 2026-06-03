#!/usr/bin/env python
"""Diagnostico OPCIONAL do uvicorn no IIS.

Nao e usado pelo web.config em producao. O padrao oficial e:
  -m uvicorn controle_acesso.asgi:application --port %HTTP_PLATFORM_PORT%

Use este script manualmente se logs\uvicorn*.log estiverem vazios:
  set HTTP_PLATFORM_PORT=8765
  venv\\Scripts\\python.exe scripts\\iis_startup.py
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "iis_startup.log"


def _log(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")


def main() -> None:
    port_raw = os.environ.get("HTTP_PLATFORM_PORT", "")
    _log(f"--- inicio PID={os.getpid()} PORT={port_raw} ---")

    if not port_raw.isdigit():
        _log("ERRO: HTTP_PLATFORM_PORT ausente ou invalido")
        sys.exit(1)

    port = int(port_raw)

    try:
        import uvicorn

        _log("uvicorn importado; iniciando servidor...")
        uvicorn.run(
            "controle_acesso.asgi:application",
            host="127.0.0.1",
            port=port,
            log_level="info",
            timeout_keep_alive=120,
        )
    except Exception:
        _log("FATAL:\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
