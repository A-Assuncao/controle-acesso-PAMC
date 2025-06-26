# 🚀 Tutorial: Rodando Projeto Django Localmente com IIS e Acesso Externo via Localhost.run

<div align="center">
  <img src="https://img.shields.io/badge/Django-4.2%2B-092E20?style=for-the-badge&logo=django" alt="Django">
  <img src="https://img.shields.io/badge/IIS-0078D4?style=for-the-badge&logo=microsoft" alt="IIS">
  <img src="https://img.shields.io/badge/localhost.run-00FF00?style=for-the-badge" alt="localhost.run">
</div>

---

## 📋 Índice

- [🎯 Objetivo](#-objetivo)
- [🐍 1. Instalar o Python](#-1-instalar-o-python)
- [🧰 2. Instalar o Git](#-2-instalar-o-git)
- [🌐 3. Ativar o IIS e Componentes](#-3-ativar-o-iis-e-componentes)
- [🔁 4. Instalar o HttpPlatformHandler](#-4-instalar-o-httpplatformhandler)
- [🔓 5. Desbloquear Handlers no IIS](#-5-desbloquear-handlers-no-iis)
- [⬇️ 6. Clonar o Repositório](#️-6-clonar-o-repositório)
- [⚙️ 7. Configurar o Site no IIS](#️-7-configurar-o-site-no-iis)
- [✅ 8. Executar o Django Localmente](#-8-executar-o-django-localmente)
- [🌍 9. Acesso Externo com Localhost.run](#-9-acesso-externo-com-localhostrun)
- [🔧 Configuração Adicional](#-configuração-adicional)
- [🐛 Troubleshooting](#-troubleshooting)

---

## 🎯 Objetivo

Este tutorial irá guiá-lo através do processo completo de configuração do **Sistema de Controle de Acesso PAMC** para rodar localmente usando o **Internet Information Services (IIS)** do Windows e disponibilizar acesso externo através do **localhost.run**.

### ✅ O que você conseguirá ao final:

- ✅ Sistema Django rodando localmente no IIS
- ✅ Acesso via rede local (IP da máquina)
- ✅ Acesso externo via localhost.run
- ✅ Configuração completa e funcional

---

## 🐍 1. Instalar o Python

### 📥 Download e Instalação

1. **Acesse**: https://www.python.org/downloads/windows/
2. **Baixe** a versão mais recente do Python (3.9+)
3. **Execute** o instalador como Administrador

### ⚙️ Configurações Importantes

Durante a instalação, certifique-se de marcar:

- ✅ **"Add Python to PATH"** (Adicionar Python ao PATH)
- ✅ **"Install for all users"** (Instalar para todos os usuários)
- ✅ **"Customize installation"** para instalar em `C:\Program Files\Python311\`

### 🔍 Verificação

Após a instalação, abra o PowerShell e execute:

```powershell
python --version
pip --version
```

Deve retornar as versões instaladas.

---

## 🧰 2. Instalar o Git

### 📥 Download e Instalação

1. **Acesse**: https://git-scm.com/downloads
2. **Baixe** a versão para Windows
3. **Execute** o instalador com configurações padrão

### 🔍 Verificação

Após a instalação, abra o PowerShell e execute:

```powershell
git --version
```

Deve retornar a versão do Git instalada.

---

## 🌐 3. Ativar o IIS e Componentes

### 🔧 Ativar Recursos do Windows

1. **Abra** "Ativar ou desativar recursos do Windows"
   - Pressione `Windows + R`
   - Digite: `optionalfeatures`
   - Pressione Enter

2. **Marque** os seguintes componentes:

#### ▶️ Internet Information Services (IIS)
- ✅ **Console de Gerenciamento do IIS**
- ✅ **Scripts e Ferramentas de Gerenciamento do IIS**
- ✅ **Serviço de Gerenciamento do IIS**

#### ▶️ Serviços da World Wide Web > Recursos de Desenvolvimento de Aplicativos
- ✅ **ASP**
- ✅ **ASP.NET 3.5**
- ✅ **ASP.NET 4.8**
- ✅ **CGI**
- ✅ **Extensibilidade .NET 3.5**
- ✅ **Extensibilidade .NET 4.8**
- ✅ **Filtros ISAPI**
- ✅ **Extensões ISAPI**
- ✅ **Inicialização de Aplicativos**
- ✅ **Protocolo WebSocket**
- ✅ **Server-Side Includes**

#### ▶️ Recursos HTTP Comuns
- ✅ **Todos os itens**

3. **Clique** em OK e aguarde a instalação

---

## 🔁 4. Instalar o HttpPlatformHandler

### 📥 Download e Instalação

1. **Acesse**: https://www.iis.net/downloads/microsoft/httpplatformhandler
2. **Baixe** a versão mais recente
3. **Execute** o instalador como Administrador
4. **Siga** as instruções do instalador

### 🔍 Verificação

Após a instalação, o HttpPlatformHandler deve aparecer na lista de módulos do IIS.

---

## 🔓 5. Desbloquear Handlers no IIS

### 🔧 Configurar Permissões

1. **Abra** o Gerenciador do IIS
   - Pressione `Windows + R`
   - Digite: `inetmgr`
   - Pressione Enter

2. **Navegue** até o site (após criá-lo):
   - Sites > controle-acesso-PAMC

3. **Clique** em "Manipuladores" (Handler Mappings)

4. **No painel direito**, clique em "Editar permissões de recurso" (Edit Feature Permissions...)

5. **Marque**:
   - ✅ **Executar (Execute)**

6. **Clique** em OK

---

## ⬇️ 6. Clonar o Repositório

### 📂 Preparar Diretório

1. **Abra** o PowerShell como Administrador

2. **Navegue** para o diretório do IIS:
```powershell
cd C:\inetpub\wwwroot
```

3. **Clone** o repositório:
```powershell
git clone https://github.com/A-Assuncao/controle-acesso-PAMC.git
```

### 🔍 Verificação

Verifique se o projeto foi clonado corretamente:

```powershell
ls controle-acesso-PAMC
```

Deve mostrar os arquivos do projeto.

---

## ⚙️ 7. Configurar o Site no IIS

### 🌐 Criar Site

1. **No Gerenciador do IIS**:
   - Clique com o botão direito em "Sites"
   - Selecione "Adicionar Site"

2. **Configure** o site:
   - **Nome do site**: `controle-acesso-PAMC`
   - **Caminho físico**: `C:\inetpub\wwwroot\controle-acesso-PAMC`
   - **Porta**: `80`
   - **Hostname**: (deixe em branco)

3. **Clique** em OK

### 🔧 Configurar Pool de Aplicativos

1. **Selecione** o site criado
2. **No painel direito**, clique em "Configurações Básicas"
3. **Clique** em "Selecionar" ao lado de "Pool de aplicativos"
4. **Crie** um novo pool ou use o existente
5. **Configure**:
   - **Versão do .NET**: "Sem código gerenciado"
   - **Modo de pipeline gerenciado**: "Integrado"

---

## ✅ 8. Executar o Django Localmente

### 🐍 Configurar Ambiente Python

1. **Navegue** para o diretório do projeto:
```powershell
cd C:\inetpub\wwwroot\controle-acesso-PAMC
```

2. **Crie** ambiente virtual (se não existir):
```powershell
python -m venv venv
```

3. **Ative** o ambiente virtual:
```powershell
.\venv\Scripts\Activate.ps1
```

4. **Instale** dependências:
```powershell
pip install -r requirements.txt
```

### 🗄️ Configurar Banco de Dados

1. **Execute** as migrações:
```powershell
python manage.py migrate
```

2. **Crie** superusuário (opcional):
```powershell
python manage.py createsuperuser
```

### 🚀 Testar Acesso Local

1. **Abra** o navegador
2. **Acesse**: `http://localhost` ou `http://127.0.0.1`
3. **Verifique** se o sistema está funcionando

### 🌐 Acesso via Rede Local

Para acessar de outros dispositivos na mesma rede:

1. **Descubra** o IP da máquina:
```powershell
ipconfig
```

2. **Acesse** de qualquer dispositivo na rede:
   - `http://192.168.0.10` (substitua pelo IP real)

---

## 🌍 9. Acesso Externo com Localhost.run

### 🔗 Configurar Túnel

Para disponibilizar acesso externo à internet:

1. **Abra** o terminal/PowerShell

2. **Execute** o comando SSH:
```bash
ssh -o ServerAliveInterval=60 -R 80:localhost:80 nokey@localhost.run
```

### 📋 Resultado

Após executar o comando, será exibido algo como:

```
https://gray-cloud.localhost.run
```

### 🔍 Como Funciona

- **URL pública**: `https://gray-cloud.localhost.run`
- **Acesso**: Qualquer pessoa com o link pode acessar
- **Duração**: Enquanto o terminal estiver aberto
- **Segurança**: Acesso temporário e controlado

### ⚠️ Importante

- O túnel permanece ativo apenas enquanto o terminal estiver aberto
- Para acesso permanente, considere usar um VPS ou serviço de hospedagem
- O localhost.run é gratuito mas tem limitações

---

## 🔧 Configuração Adicional

### 🔐 Configurar HTTPS (Opcional)

Para maior segurança, configure HTTPS:

1. **Instale** certificado SSL
2. **Configure** binding HTTPS no IIS
3. **Redirecione** HTTP para HTTPS

### 📊 Monitoramento

Configure logs para monitoramento:

1. **IIS Logs**: Ative logs detalhados
2. **Django Logs**: Configure logging no settings.py
3. **Performance**: Monitore uso de recursos

### 🔄 Atualizações Automáticas

Configure atualizações automáticas:

1. **Script** de pull automático
2. **Agendamento** via Task Scheduler
3. **Notificações** de atualizações

---

## 🐛 Troubleshooting

### ❌ Problemas Comuns

#### 🔴 Erro 500 - Internal Server Error
**Solução**:
```powershell
# Verificar logs do IIS
# Verificar permissões de arquivo
# Verificar configuração do web.config
```

#### 🔴 Erro 404 - Not Found
**Solução**:
```powershell
# Verificar caminho físico do site
# Verificar configuração de handlers
# Verificar arquivo web.config
```

#### 🔴 Erro de Permissão
**Solução**:
```powershell
# Dar permissões completas ao usuário IIS_IUSRS
# Verificar permissões da pasta do projeto
```

#### 🔴 Django não carrega
**Solução**:
```powershell
# Verificar ambiente virtual
# Verificar dependências instaladas
# Verificar configuração do HttpPlatformHandler
```

### 📞 Suporte

Se encontrar problemas:

1. **Verifique** os logs do IIS
2. **Consulte** a documentação do Django
3. **Abra** uma issue no GitHub do projeto

---

## 🎉 Conclusão

Parabéns! Você configurou com sucesso o **Sistema de Controle de Acesso PAMC** para rodar localmente com IIS e acesso externo via localhost.run.

### ✅ Checklist Final

- ✅ Python instalado e configurado
- ✅ Git instalado
- ✅ IIS ativado com componentes necessários
- ✅ HttpPlatformHandler instalado
- ✅ Repositório clonado
- ✅ Site configurado no IIS
- ✅ Django rodando localmente
- ✅ Acesso via rede local funcionando
- ✅ Túnel localhost.run configurado (opcional)

### 🚀 Próximos Passos

1. **Explore** as funcionalidades do sistema
2. **Configure** usuários e permissões
3. **Teste** o ambiente de treinamento
4. **Personalize** conforme necessário

---

<div align="center">
  <p><strong>🎯 Sistema configurado e pronto para uso!</strong></p>
  <p><em>Para dúvidas ou problemas, consulte a documentação ou abra uma issue no GitHub.</em></p>
</div> 