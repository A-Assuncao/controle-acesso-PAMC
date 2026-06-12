# Sistema de Controle de Acesso

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.12--3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

Aplicação web Django para controle de acesso de servidores (entrada/saída, plantões, relatórios, ambiente de treinamento).

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| **[INSTALACAO_PRODUCAO.md](docs/INSTALACAO_PRODUCAO.md)** | IIS, scripts, update, runner GitHub, troubleshooting |
| **[CONFIGURACAO_AMBIENTE.md](docs/CONFIGURACAO_AMBIENTE.md)** | Variáveis `.env` |
| **[CHANGELOG.md](docs/CHANGELOG.md)** | Histórico de versões |

---

## Stack

- **Django 6.0** · **Python 3.12–3.14** · **SQLite**
- Produção: **IIS** + HttpPlatformHandler + **uvicorn**
- Frontend: Bootstrap 5, SweetAlert2

---

## Desenvolvimento local

```powershell
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
cd controle-acesso-PAMC

# Com uv (recomendado)
uv venv
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver

# Ou com venv clássico
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Copie `.env.example` para `.env` e ajuste conforme [CONFIGURACAO_AMBIENTE.md](docs/CONFIGURACAO_AMBIENTE.md).

---

## Produção (Windows / IIS)

```powershell
# Após clone, venv, .env e site no IIS:
powershell -ExecutionPolicy Bypass -File .\scripts\configurar_iis.ps1
python manage.py createsuperuser

# Opcional — deploy no git push:
powershell -ExecutionPolicy Bypass -File .\scripts\instalar_runner_github.ps1
```

Detalhes completos: **[docs/INSTALACAO_PRODUCAO.md](docs/INSTALACAO_PRODUCAO.md)**

### Scripts essenciais

| Arquivo | Uso |
|---------|-----|
| `scripts/configurar_iis.ps1` | Instalação/reparo IIS + update diário |
| `scripts/configurar_update_automatico.ps1` | Só reconfigurar update |
| `scripts/instalar_runner_github.ps1` | Runner GitHub (opcional) |
| `update_app.bat` → `update/update.bat` | Update manual, tarefa 00:00 ou CI |

---

## Estrutura do projeto

```
controle-acesso-PAMC/
├── controle_acesso/     # settings, urls, asgi
├── core/
│   ├── views/           # Views modulares por domínio
│   ├── models.py
│   ├── utils.py
│   └── templates/
├── docs/
├── scripts/             # PowerShell (IIS, runner)
├── update/              # update.bat
├── static/
└── manage.py
```

Módulos de views: `base_views`, `servidor_views`, `registro_views`, `user_views`, `relatorio_views`, `treinamento_views` (+ `registro_extended`, `treinamento_extended` para lógica mais extensa).

---

## Funcionalidades principais

- Dashboard em tempo real (entradas, saídas, pendências)
- CRUD de servidores e importação Excel
- Perfis de usuário (Admin, Staff, Operador, Visualização)
- Relatórios, exportação Excel/PDF, histórico com auditoria
- Ambiente de treinamento isolado
- Autenticação Canaimé (opcional, via `.env`)

---

## Comandos úteis

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py setup_groups
```

---

## Licença

MIT — veja [LICENSE](LICENSE).
