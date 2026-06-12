"""
Views do ambiente de treinamento e funções auxiliares.

Responsável por:
- Ambiente de treinamento (versão paralela do sistema principal)
- Tutoriais e handlers de erro
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from ..utils import (
    processar_registro_acesso_helper,
    saida_definitiva_helper,
    limpar_dashboard_helper,
    buscar_servidores_helper,
)
from .treinamento_extended import (
    ambiente_treinamento,
    exportar_excel_treinamento,
    excluir_registro_treinamento,
    registro_acesso_treinamento_update,
    registro_detalhe_treinamento,
    registro_manual_treinamento_create,
    registrar_saida_treinamento,
    registros_plantao_treinamento,
    retirar_faltas_treinamento,
)


def is_superuser(user):
    """Verifica se o usuário é superusuário."""
    return user.is_superuser


@login_required
def buscar_servidor_treinamento(request):
    """
    API para busca de servidores no ambiente de treinamento.

    Busca no cadastro principal (Servidor), sem alterar dashboard/historico de producao.
    Contrato JSON compativel com static/js/shared.js: ?query=... -> {status, resultados}.
    """
    query = (request.GET.get('query') or request.GET.get('q') or '').strip()

    if len(query) < 2:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'Digite pelo menos 2 caracteres para buscar.',
            },
            status=400,
        )

    resultados_raw = buscar_servidores_helper(query, formato='detalhado')
    resultados = [
        {
            'id': item['id'],
            'nome': item['nome'],
            'documento': item['documento'],
            'setor': item['setor'],
            'veiculo': item['veiculo'],
            'tipo_funcionario': item.get('tipo_funcionario'),
            'plantao': item.get('plantao'),
        }
        for item in resultados_raw
    ]

    return JsonResponse({'status': 'success', 'resultados': resultados})


@login_required
def registro_acesso_treinamento_create(request):
    """Cria registro de acesso no ambiente de treinamento."""
    if request.method == 'POST':
        sucesso, mensagem, redirect_url = processar_registro_acesso_helper(
            request, is_treinamento=True
        )

        if sucesso:
            return JsonResponse({'status': 'success', 'message': mensagem})
        return JsonResponse({'status': 'error', 'message': mensagem})

    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})


@login_required
def saida_definitiva_treinamento(request):
    """Registra saída definitiva no ambiente de treinamento."""
    if request.method == 'POST':
        resultado = saida_definitiva_helper(request, is_treinamento=True)
        return JsonResponse(resultado)

    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido',
    })


@login_required
def limpar_dashboard_treinamento(request):
    """Limpa dashboard do ambiente de treinamento."""
    if request.method == 'POST':
        resultado = limpar_dashboard_helper(request, is_treinamento=True)

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
        'message': 'Método não permitido. Use POST para esta operação.',
    }, status=405)


@login_required
def tutoriais_treinamento(request):
    """Exibe tutoriais do sistema."""
    return render(request, 'core/tutoriais.html')


def handler500(request):
    """Handler customizado para erros 500."""
    return render(request, '500.html', status=500)
