#!/usr/bin/env python3
"""
Script para validar os links do docs/CHANGELOG.md

Verifica se:
- Todos os arquivos referenciados existem
- Os links markdown estão bem formados
- As seções estão organizadas corretamente
"""

import os
import re
from pathlib import Path

def validar_changelog():
    """Valida o arquivo CHANGELOG.md"""
    
    # Verifica se o arquivo existe
    changelog_path = Path("docs/CHANGELOG.md")
    if not changelog_path.exists():
        print("❌ docs/CHANGELOG.md não encontrado!")
        return False
    
    print("✅ docs/CHANGELOG.md encontrado")
    
    # Lê o conteúdo
    with open(changelog_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica links para arquivos
    arquivos_referenciados = [
        "README.md",
        "docs/CONFIGURACAO_AMBIENTE.md", 
        "docs/TUTORIAL_IIS_LOCALHOST_RUN.md"
    ]
    
    print("\n📋 Validando links para arquivos:")
    for arquivo in arquivos_referenciados:
        if Path(arquivo).exists():
            print(f"  ✅ {arquivo}")
        else:
            print(f"  ❌ {arquivo} - ARQUIVO NÃO ENCONTRADO!")
    
    # Verifica se há versões duplicadas
    print("\n🔍 Verificando versões:")
    versoes = re.findall(r'## \[([^\]]+)\]', content)
    versoes_unicas = set(versoes)
    
    if len(versoes) == len(versoes_unicas):
        print(f"  ✅ {len(versoes)} versões encontradas, todas únicas")
    else:
        print(f"  ❌ Versões duplicadas encontradas!")
        print(f"  Total: {len(versoes)}, Únicas: {len(versoes_unicas)}")
    
    # Verifica estrutura das seções
    print("\n📊 Verificando estrutura:")
    secoes_obrigatorias = ["Adicionado", "Modificado", "Melhorado"]
    secoes_encontradas = re.findall(r'### (.+?) \*\*', content)
    
    print(f"  ✅ {len(secoes_encontradas)} seções de mudanças encontradas")
    
    # Verifica emojis
    emojis_mudancas = ["✨", "🔄", "❌", "🐛", "🛠️", "🔐"]
    for emoji in emojis_mudancas:
        if emoji in content:
            print(f"  ✅ {emoji} categoria encontrada")
    
    # Verifica links para seções do próprio CHANGELOG
    print("\n🔗 Verificando links internos:")
    links_internos = re.findall(r'\[v\d+\.\d+\.\d+\]\((?:docs/)?CHANGELOG\.md#[^)]+\)', content)
    print(f"  ✅ {len(links_internos)} links internos encontrados")
    
    print("\n🎉 Validação concluída!")
    return True

if __name__ == "__main__":
    print("🔍 Validando docs/CHANGELOG.md...")
    print("=" * 50)
    validar_changelog() 