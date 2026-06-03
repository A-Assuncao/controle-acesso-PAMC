#!/usr/bin/env python
"""Ponto de entrada do uvicorn no IIS (HttpPlatformHandler).

Grava logs em logs/iis_startup.log para diagnostico. O HttpPlatformHandler
costuma criar arquivos stdout com sufixo de PID (ex.: uvicorn_1234.log).
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
