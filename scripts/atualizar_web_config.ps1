# Redireciona para o script unificado (atualiza web.config e demais itens).
& (Join-Path $PSScriptRoot "configurar_iis.ps1") @args
