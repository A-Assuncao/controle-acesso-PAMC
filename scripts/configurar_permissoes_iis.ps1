# Redireciona para o script unificado.
param([string]$NomePool = "controle-acesso-PAMC")
& (Join-Path $PSScriptRoot "configurar_iis.ps1") -NomeSite $NomePool @args
