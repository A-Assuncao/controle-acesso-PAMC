# Redireciona para o script unificado.
& (Join-Path $PSScriptRoot "configurar_iis.ps1") -SomenteVerificar @args
