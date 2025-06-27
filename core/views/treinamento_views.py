"""
Views do ambiente de treinamento e funções auxiliares.

Responsável por:
- Ambiente de treinamento (versão paralela do sistema principal)
- Todas as funcionalidades espelhadas para treinamento
- Tutoriais e documentação
- Funções auxiliares do sistema
- Handlers de erro
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from ..utils import (
    processar_registro_acesso_helper, exportar_excel_helper,
    saida_definitiva_helper, limpar_dashboard_helper,
    buscar_servidores_helper
)


def is_superuser(user):
    """Verifica se o usuário é superusuário."""
    return user.is_superuser


@login_required
def ambiente_treinamento(request):
    """
    View principal do ambiente de treinamento.
    
    Esta view é uma cópia espelhada da home principal,
    mas operando em um ambiente isolado para treinamento.
    """
    # Implementação complexa mantida do original
    from ..views_original import ambiente_treinamento as original_ambiente
    return original_ambiente(request)


@login_required
def registros_plantao_treinamento(request):
    """API que retorna registros do dashboard de treinamento."""
    # Implementação complexa mantida do original
    from ..views_original import registros_plantao_treinamento as original_registros
    return original_registros(request)


@login_required
def registro_detalhe_treinamento(request, registro_id):
    """Retorna detalhes de um registro de treinamento."""
    # Implementação complexa mantida do original
    from ..views_original import registro_detalhe_treinamento as original_detalhe
    return original_detalhe(request, registro_id)


@login_required
def buscar_servidor_treinamento(request):
    """API para busca de servidores no ambiente de treinamento."""
    query = request.GET.get('q', '')
    resultados = buscar_servidores_helper(query, formato='simples')
    return JsonResponse(resultados, safe=False)


@login_required
def registro_acesso_treinamento_create(request):
    """Cria registro de acesso no ambiente de treinamento."""
    if request.method == 'POST':
        sucesso, mensagem, redirect_url = processar_registro_acesso_helper(request, is_treinamento=True)
        
        if sucesso:
            return JsonResponse({'status': 'success', 'message': mensagem})
        else:
            return JsonResponse({'status': 'error', 'message': mensagem})
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})


@login_required
def registro_manual_treinamento_create(request):
    """Cria registro manual no ambiente de treinamento."""
    # Implementação complexa mantida do original
    from ..views_original import registro_manual_treinamento_create as original_manual
    return original_manual(request)


@login_required
def saida_definitiva_treinamento(request):
    """Registra saída definitiva no ambiente de treinamento."""
    if request.method == 'POST':
        resultado = saida_definitiva_helper(request, is_treinamento=True)
        return JsonResponse(resultado)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    })


@login_required
def limpar_dashboard_treinamento(request):
    """Limpa dashboard do ambiente de treinamento."""
    if request.method == 'POST':
        resultado = limpar_dashboard_helper(request, is_treinamento=True)
        
        # Adiciona código de status HTTP baseado no resultado
        if resultado['status'] == 'error':
            if 'Senha não fornecida' in resultado['message']:
                status_code = 400
            elif 'Senha incorreta' in resultado['message']:
                status_code = 401
            else:
                status_code = 500
            return JsonResponse(resultado, status=status_code)
        
        return JsonResponse(resultado)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido. Use POST para esta operação.'
    }, status=405)


@login_required
def exportar_excel_treinamento(request):
    """Exporta registros do treinamento para Excel."""
    # Implementação complexa mantida do original
    from ..views_original import exportar_excel_treinamento as original_excel
    return original_excel(request)


@login_required
def registro_acesso_treinamento_update(request, registro_id):
    """
    Atualiza registro de acesso no ambiente de treinamento.
    
    Esta view é extremamente complexa (~150 linhas) e espelha
    toda a funcionalidade de edição do ambiente principal.
    """
    # Implementação complexa mantida do original
    from ..views_original import registro_acesso_treinamento_update as original_update
    return original_update(request, registro_id)


@login_required
def excluir_registro_treinamento(request, registro_id):
    """Exclui registro no ambiente de treinamento."""
    # Implementação complexa mantida do original
    from ..views_original import excluir_registro_treinamento as original_excluir
    return original_excluir(request, registro_id)


@login_required
def registrar_saida_treinamento(request, registro_id):
    """Registra saída no ambiente de treinamento."""
    # Implementação complexa mantida do original
    from ..views_original import registrar_saida_treinamento as original_saida
    return original_saida(request, registro_id)


@login_required
def tutoriais_treinamento(request):
    """Exibe tutoriais do sistema."""
    return render(request, 'core/tutoriais.html')


@login_required
def retirar_faltas_treinamento(request):
    """
    Relatório de faltas no ambiente de treinamento.
    
    Lista servidores que deveriam estar presentes mas não estão registrados no treinamento.
    """
    # Implementação complexa mantida do original
    from ..views_original import retirar_faltas_treinamento as original_retirar_faltas_treinamento
    return original_retirar_faltas_treinamento(request)


def handler500(request):
    """Handler customizado para erros 500."""
    return render(request, '500.html', status=500) 