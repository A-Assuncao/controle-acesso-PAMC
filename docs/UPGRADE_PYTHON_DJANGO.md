# Upgrade Python 3.14 + Django 6.0

## Versoes alvo

| Componente | Versao |
|------------|--------|
| Python | 3.12, 3.13 ou **3.14** (recomendado: ultima estavel de python.org) |
| Django | **6.0.6** |
| django-bootstrap5 | **26.2** |

Referencia oficial: [Django 6.0 — Python 3.12 a 3.14](https://docs.djangoproject.com/en/6.0/faq/install/).

## Desenvolvimento local (uv)

```powershell
cd controle-acesso-PAMC
uv venv --python 3.14
uv pip install -r requirements.txt
uv run python manage.py migrate
uv run python manage.py check
```

Sem uv:

```powershell
C:\Python314\python.exe -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
```

## Servidor IIS (producao)

1. Instale Python de https://www.python.org/downloads/windows/
   - Marque **Install for all users**
   - Caminho global, ex.: `C:\Python314\python.exe`
   - **Nao** use Python apenas em `AppData\Local\`

2. Recrie o ambiente virtual:

```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
git pull
Remove-Item -Recurse -Force venv
& "C:\Python314\python.exe" -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
```

3. Confirme:

```powershell
Get-Content .\venv\pyvenv.cfg
.\venv\Scripts\python.exe manage.py check --deploy
```

## Notas

- O banco SQLite existente e compativel; `migrate` aplica apenas migracoes pendentes.
- Em producao, defina no `.env`: `DJANGO_DEBUG=False` e `DJANGO_SECRET_KEY` fixa.
- FastCGI/wfastcgi **nao** e suportado; use HttpPlatformHandler + uvicorn.
