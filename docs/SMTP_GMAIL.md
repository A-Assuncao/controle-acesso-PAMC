# Configuração SMTP com Gmail

Este guia explica como configurar o Gmail para envio de emails
transacionais (credenciais de novos usuários / reset de senha) no
**Controle de Acesso PAMC**.

## Por que Gmail?

- **Sem custo**: usa qualquer conta Google (pessoal ou Workspace).
- **Limite confortável**: ~500 emails/dia (pessoal) ou 2.000/dia
  (Workspace). Para 1-10 senhas/dia sobra de folga.
- **Sem precisar de domínio próprio** — ideal para unidades que
  ainda não têm DNS configurado (Mailgun exige).
- **Setup em 5 minutos** — só precisa de uma App Password.

## Limitações honestas

- O `From` será **sempre o próprio email autenticado** (Gmail não
  permite enviar "em nome de" outro endereço).
- **Não use conta pessoal** com 2FA fraco: o Google pode bloquear a
  conta se detectar automação suspeita. **Recomendado**: criar uma
  conta Gmail dedicada para o sistema (ex.: `pamc.controle@gmail.com`).
- **Não use o email institucional `@pamc.am.gov.br`** nesse campo — o
  Google vai autenticar como `@gmail.com` e os destinatários verão
  o endereço errado.
- Delay de 1-3s por envio (irrelevante neste volume).

## Passo 1 — Ativar 2FA na conta Google

A App Password **só funciona com Verificação em duas etapas ativa**.

1. Acesse https://myaccount.google.com/security
2. Em "Como você faz login no Google" → **Verificação em duas etapas**
3. Siga o wizard (normalmente é confirmar via celular)

## Passo 2 — Gerar a App Password

1. Acesse https://myaccount.google.com/apppasswords
2. Em "Nome do app", clique em **Selecionar app** → **Outro (nome personalizado)**
3. Digite `PAMC Controle` (ou o nome que preferir)
4. Clique em **Gerar**
5. O Google mostra 16 caracteres no formato `abcd efgh ijkl mnop`
   — **copie imediatamente**. Aparece **apenas uma vez**.

> Cada App Password é independente: você pode revogar uma sem afetar
> as outras. Útil quando a senha vaza em chat/log.

## Passo 3 — Configurar o `.env` no servidor

Edite o `.env` do servidor de produção
(`C:\inetpub\wwwroot\controle-acesso-PAMC\.env`) e/ou o local:

```ini
# E-MAIL - Gmail SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=solucoesassuncao@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop
DEFAULT_FROM_EMAIL=PAMC Controle de Acesso <solucoesassuncao@gmail.com>
SERVER_EMAIL=solucoesassuncao@gmail.com
```

**Substitua:**
- `solucoesassuncao@gmail.com` → conta Gmail em uso (ou conta dedicada
  se preferir)
- `abcd efgh ijkl mnop` → App Password gerada no Passo 2

> ⚠️ Mantenha o `.env` no `.gitignore` (já está por padrão).
> O `.env.example` carrega apenas placeholders para documentação.

## Passo 4 — Testar

```bash
# 1. Valida configuração sem enviar
python manage.py shell -c "
from django.conf import settings
print('Host:', settings.EMAIL_HOST)
print('User:', settings.EMAIL_HOST_USER)
print('From:', settings.DEFAULT_FROM_EMAIL)
print('TLS:', settings.EMAIL_USE_TLS)
print('Backend:', settings.EMAIL_BACKEND)
"

# 2. Testa envio real (use seu email pessoal)
python manage.py shell -c "
from django.core.mail import send_mail
result = send_mail(
    subject='Teste PAMC Controle de Acesso',
    message='Se voce recebeu, Gmail SMTP esta OK.',
    from_email=None,
    recipient_list=['seu.email.pessoal@gmail.com'],
    fail_silently=False,
)
print('Emails enviados:', result)
"
```

Se aparecer `Emails enviados: 1`, deu certo. Verifique a caixa de
entrada **e spam** do destinatário.

### Erros comuns

| Erro no Django | Causa | Solução |
|---|---|---|
| `Username and Password not accepted` | App Password errada ou 2FA desativado | Gere nova App Password; verifique 2FA em myaccount.google.com/security |
| `Application-specific password required` | Tentou usar senha normal da conta | Use **só** App Password (16 caracteres com espaços) |
| `SMTP AUTH extension not supported` | `EMAIL_USE_TLS=False` com porta 587 | Confirme `EMAIL_USE_TLS=True` no `.env` |
| `Connection unexpectedly closed` | Firewall/proxy bloqueando porta 587 | Teste com `python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"` |
| Email cai no spam do destinatário | Conta nova / sem histórico | Use uma conta Gmail "quente" ou peça destinatários marcarem como "não é spam" |

## Passo 5 — Monitoramento

Gmail **não tem painel de logs** público. Para rastrear envios:

- **Logs do Django** (`logs/*.log`): cada envio loga sucesso/falha.
- **Caixa de "Enviados"** da própria conta Gmail: cada email enviado
  aparece lá com timestamp e destinatário.
- **Respostas dos destinatários**: se um email voltar (bounce), o
  Gmail notifica `SERVER_EMAIL` (no nosso caso, a própria conta).

Para volumes maiores (centenas/dia) considere migrar para Mailgun
(veja `docs/SMTP_MAILGUN.md`) que tem painel de logs nativo.

## Passo 6 — Trocar a App Password (quando necessário)

Se você acha que a senha vazou (chat, log, screenshot):

1. https://myaccount.google.com/apppasswords
2. Encontre `PAMC Controle` na lista
3. Clique no **lápis** → **Remover**
4. Gere uma nova e atualize o `.env`
5. **Não é preciso reiniciar o IIS** se o `wfastcgi` recarregar o
   processo a cada request (verifique com `iisreset` se necessário).

## Custos

- **Grátis** para qualquer volume de conta pessoal.
- **Google Workspace** (R$ ~30/mês) opcional — útil se a unidade
  quiser emails `@unidad.prisional.gov.br` no futuro.

## Referências oficiais

- App Passwords: https://support.google.com/accounts/answer/185833
- 2FA: https://support.google.com/accounts/answer/185839
- Limites SMTP: https://support.google.com/mail/answer/22839
