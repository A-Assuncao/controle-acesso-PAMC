"""
Views de gerenciamento de servidores.

Responsável por:
- CRUD completo de servidores
- Busca de servidores
- Importação via CSV
- Limpeza do banco de servidores
- Verificação de entradas pendentes
"""

import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q

from ..models import Servidor, RegistroDashboard, LogAuditoria
from ..forms import ServidorForm
from ..decorators import pode_gerenciar_servidores, admin_required
from ..utils import buscar_servidores_helper


@login_required
@pode_gerenciar_servidores
def servidor_list(request):
    """Lista todos os servidores com filtro de busca."""
    query = request.GET.get('q')
    servidores = Servidor.objects.all().order_by('nome')
    
    if query:
        print(f"Busca realizada com o termo: '{query}'")
        servidores = servidores.filter(
            Q(nome__icontains=query) |
            Q(numero_documento__icontains=query) |
            Q(setor__icontains=query)
        )
        print(f"Resultados encontrados: {servidores.count()}")
    
    return render(request, 'core/servidor_list.html', {'servidores': servidores})


@login_required
@pode_gerenciar_servidores
def servidor_create(request):
    """Cria um novo servidor."""
    if request.method == 'POST':
        form = ServidorForm(request.POST)
        if form.is_valid():
            servidor = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='CRIACAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Criação do servidor {servidor.nome}'
            )
            messages.success(request, 'Servidor cadastrado com sucesso!')
            return redirect('servidor_list')
    else:
        form = ServidorForm()
    return render(request, 'core/servidor_form.html', {'form': form})


@login_required
@pode_gerenciar_servidores
def servidor_update(request, pk):
    """Atualiza um servidor existente."""
    servidor = get_object_or_404(Servidor, pk=pk)
    
    if request.method == 'POST':
        form = ServidorForm(request.POST, instance=servidor)
        if form.is_valid():
            servidor = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EDICAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Edição de servidor: {servidor.nome}'
            )
            messages.success(request, 'Servidor atualizado com sucesso!')
            return redirect('servidor_list')
    else:
        form = ServidorForm(instance=servidor)
    
    return render(request, 'core/servidor_form.html', {'form': form})


@login_required
@admin_required
@pode_gerenciar_servidores
def servidor_delete(request, pk):
    """Exclui um servidor."""
    if request.method == 'POST':
        try:
            servidor = get_object_or_404(Servidor, pk=pk)
            nome_servidor = servidor.nome
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Exclusão do servidor {nome_servidor}'
            )
            
            # Exclui o servidor
            servidor.delete()
            
            messages.success(request, f'Servidor {nome_servidor} excluído com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir servidor: {str(e)}')
            return redirect('servidor_list')
    
    return redirect('servidor_list')


@login_required
def buscar_servidor(request):
    """API para busca de servidores (autocomplete)."""
    query = request.GET.get('q', '')
    resultados = buscar_servidores_helper(query, formato='simples')
    return JsonResponse(resultados, safe=False)


@login_required
def verificar_entrada(request, servidor_id):
    """Verifica se existe uma entrada sem saída para o servidor."""
    tem_entrada = RegistroDashboard.objects.filter(
        servidor_id=servidor_id,
        tipo_acesso='ENTRADA',
        saida_pendente=True
    ).exists()
    
    return JsonResponse({'tem_entrada': tem_entrada})


@login_required
@admin_required
def importar_servidores(request):
    """Importa servidores via arquivo CSV."""
    if request.method == 'POST':
        try:
            arquivo = request.FILES['arquivo']
            
            # Tentativa de leitura com diferentes codificações
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252']
            decoded_file = None
            successful_encoding = None
            
            for encoding in encodings:
                try:
                    # Tenta decodificar com a codificação atual
                    arquivo.seek(0)  # Reseta o ponteiro do arquivo
                    decoded_file = arquivo.read().decode(encoding).splitlines()
                    successful_encoding = encoding
                    break
                except UnicodeDecodeError:
                    # Se falhar, continua para a próxima codificação
                    continue
            
            if decoded_file is None:
                raise Exception(f"Não foi possível ler o arquivo com nenhuma das codificações suportadas ({', '.join(encodings)}). Certifique-se de salvar o arquivo como CSV com codificação UTF-8.")
                
            print(f"Arquivo CSV lido com sucesso usando codificação: {successful_encoding}")
            
            # Tenta identificar o delimitador (vírgula ou ponto-e-vírgula)
            primeira_linha = decoded_file[0] if decoded_file else ""
            delimiter = ';' if ';' in primeira_linha else ','
            print(f"Delimitador identificado: {delimiter}")
            
            # Usa o delimitador detectado
            reader = csv.DictReader(decoded_file, delimiter=delimiter)
            
            # Verificação e normalização dos nomes das colunas
            colunas_esperadas = ['Nome', 'Número do Documento', 'Setor', 'Veículo']
            colunas_reader = reader.fieldnames
            
            # Verificar se há colunas necessárias no CSV
            if not colunas_reader:
                raise Exception("Arquivo CSV não contém cabeçalhos de colunas")
                
            # Criar mapeamento para normalizar nomes de colunas
            mapeamento_colunas = {}
            for coluna_esperada in colunas_esperadas:
                # Verifica coluna exata
                if coluna_esperada in colunas_reader:
                    mapeamento_colunas[coluna_esperada] = coluna_esperada
                    continue
                
                # Verifica variação sem acentos e case insensitive
                coluna_normalizada = coluna_esperada.lower().replace('ú', 'u').replace('í', 'i')
                for coluna in colunas_reader:
                    if coluna and coluna.lower().replace('ú', 'u').replace('í', 'i') == coluna_normalizada:
                        mapeamento_colunas[coluna_esperada] = coluna
                        break
            
            # Verifica se todas as colunas necessárias foram encontradas
            colunas_faltantes = [col for col in colunas_esperadas if col not in mapeamento_colunas]
            if colunas_faltantes:
                colunas_encontradas = ", ".join([f"'{c}'" for c in colunas_reader if c])
                colunas_necessarias = ", ".join([f"'{c}'" for c in colunas_faltantes])
                raise Exception(f"Colunas não encontradas: {colunas_necessarias}. Colunas disponíveis: {colunas_encontradas}")
            
            servidores_criados = 0
            servidores_atualizados = 0
            
            for row in reader:
                try:
                    # Verifica se a linha tem dados válidos
                    if not row[mapeamento_colunas['Nome']] or not row[mapeamento_colunas['Número do Documento']]:
                        continue  # Pula linhas vazias ou sem dados essenciais
                        
                    servidor, created = Servidor.objects.update_or_create(
                        numero_documento=row[mapeamento_colunas['Número do Documento']],
                        defaults={
                            'nome': row[mapeamento_colunas['Nome']],
                            'setor': row[mapeamento_colunas['Setor']],
                            'veiculo': row[mapeamento_colunas['Veículo']],
                            'ativo': True
                        }
                    )
                    
                    if created:
                        servidores_criados += 1
                    else:
                        servidores_atualizados += 1
                    
                    LogAuditoria.objects.create(
                        usuario=request.user,
                        tipo_acao='CRIACAO' if created else 'EDICAO',
                        modelo='Servidor',
                        objeto_id=servidor.id,
                        detalhes=f"{'Criação' if created else 'Atualização'} de servidor via importação: {servidor.nome}"
                    )
                except Exception as row_error:
                    # Adiciona informações sobre a linha que falhou
                    raise Exception(f"Erro na linha {reader.line_num}: {str(row_error)}. Dados: {row}")
            
            messages.success(request, f'{servidores_criados} servidores criados e {servidores_atualizados} atualizados com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao importar servidores: {str(e)}')
            return redirect('importar_servidores')
    
    return render(request, 'core/importar_servidores.html')


@login_required
@admin_required
def download_modelo_importacao(request):
    """Baixa modelo CSV para importação de servidores."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=modelo_importacao.csv'
    
    # Configura encoding UTF-8 com BOM para compatibilidade com Excel
    response.write('\ufeff')
    
    # Estas colunas DEVEM corresponder exatamente às esperadas na função importar_servidores
    colunas = ['Nome', 'Número do Documento', 'Setor', 'Veículo']
    
    # Configura o CSV para usar ponto-e-vírgula como delimitador (melhor compatibilidade com Excel brasileiro)
    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(colunas)
    writer.writerow(['João da Silva', '12.345.678-9', 'Administrativo', 'ABC1234'])
    writer.writerow(['Maria Oliveira', '98.765.432-1', 'RH', ''])
    
    return response


@login_required
@admin_required
def limpar_banco_servidores(request):
    """Limpa todos os servidores do banco de dados."""
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                messages.error(request, 'Senha incorreta!')
                return redirect('servidor_list')
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='Servidor',
                objeto_id=0,
                detalhes='Limpeza do banco de servidores'
            )
            
            # Exclui todos os registros do dashboard primeiro
            RegistroDashboard.objects.all().delete()
            
            # Exclui todos os servidores
            Servidor.objects.all().delete()
            
            messages.success(request, 'Banco de servidores limpo com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao limpar banco de servidores: {str(e)}')
            return redirect('servidor_list')
    
    return redirect('servidor_list') 