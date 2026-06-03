# Redireciona para o script unificado.
param([int]$Porta = 3000, [string]$NomeSite = "controle-acesso-PAMC")
& (Join-Path $PSScriptRoot "configurar_iis.ps1") -Porta $Porta -NomeSite $NomeSite @args
