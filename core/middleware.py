# -*- coding: utf-8 -*-
from django.shortcuts import redirect
from django.urls import reverse
import logging
import traceback
import sys

logger = logging.getLogger('core')

class TrocaSenhaMiddleware:
    """
    Middleware que verifica se o usuário precisa trocar a senha e redireciona 
    para a página de troca de senha se necessário.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verifica se o usuário está autenticado
        if request.user.is_authenticated:
            # Verifica se o usuário tem um perfil
            try:
                perfil = request.user.perfil
            except:
                # Se o usuário não tem perfil, cria um novo
                from core.models import PerfilUsuario
                perfil = PerfilUsuario.objects.create(
                    usuario=request.user,
                    precisa_trocar_senha=False,
                    tipo_usuario='OPERADOR'  # Define como operador por padrão
                )
            
            try:
                # Se o usuário precisa trocar a senha e não está na página de troca de senha
                if perfil.precisa_trocar_senha:
                    # Lista de páginas permitidas mesmo quando precisa trocar senha
                    paginas_permitidas = [
                        reverse('logout'),      # Permite sair do sistema
                        reverse('trocar_senha'),  # Permite acessar a página de troca de senha
                    ]
                    
                    # Verifica se o caminho atual está na lista de permitidos
                    for pagina in paginas_permitidas:
                        if request.path.startswith(pagina):
                            return self.get_response(request)
                    
                    # Permite arquivos estáticos (CSS, JS, imagens, etc.)
                    if (request.path.startswith('/static/') or 
                        request.path.startswith('/media/') or
                        request.path.startswith('/staticfiles/')):
                        return self.get_response(request)
                    
                    # Garante que a página de login seja acessível para evitar loops
                    if request.path.startswith(reverse('login')):
                        return self.get_response(request)
                    
                    # Redireciona para a página de troca de senha
                    return redirect('trocar_senha')
            except Exception as e:
                # Se o usuário não tem perfil ou ocorreu um erro, registra o erro
                logger.error(f"Erro no TrocaSenhaMiddleware: {str(e)}\n{traceback.format_exc()}")
                pass
                
        # Processa normalmente se não precisa trocar a senha
        response = self.get_response(request)
        return response


class ErrorLoggingMiddleware:
    """
    Middleware para capturar e logar todos os erros com traceback detalhado
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # Captura informações detalhadas do erro
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            traceback_text = ''.join(tb_lines)
            
            # Informações da requisição
            request_info = {
                'method': request.method,
                'url': request.get_full_path(),
                'user': getattr(request.user, 'username', 'Anônimo') if hasattr(request, 'user') else 'Anônimo',
                'ip': request.META.get('REMOTE_ADDR', 'Desconhecido'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Desconhecido'),
                'referer': request.META.get('HTTP_REFERER', 'Nenhum'),
            }
            
            # Log detalhado do erro
            logger.error(
                f"ERRO CAPTURADO NO MIDDLEWARE:\n"
                f"Tipo: {exc_type.__name__}\n"
                f"Mensagem: {str(exc_value)}\n"
                f"URL: {request_info['url']}\n"
                f"Método: {request_info['method']}\n"
                f"Usuário: {request_info['user']}\n"
                f"IP: {request_info['ip']}\n"
                f"Traceback:\n{traceback_text}"
            )
            
            # Re-levanta a exceção para que o Django processe normalmente
            raise

    def process_exception(self, request, exception):
        """
        Processa exceções que não foram capturadas no __call__
        """
        # Captura informações detalhadas do erro
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        traceback_text = ''.join(tb_lines)
        
        # Informações da requisição
        request_info = {
            'method': request.method,
            'url': request.get_full_path(),
            'user': getattr(request.user, 'username', 'Anônimo') if hasattr(request, 'user') else 'Anônimo',
            'ip': request.META.get('REMOTE_ADDR', 'Desconhecido'),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Desconhecido'),
            'referer': request.META.get('HTTP_REFERER', 'Nenhum'),
        }
        
        # Log detalhado do erro
        logger.error(
            f"EXCEÇÃO CAPTURADA NO MIDDLEWARE:\n"
            f"Tipo: {type(exception).__name__}\n"
            f"Mensagem: {str(exception)}\n"
            f"URL: {request_info['url']}\n"
            f"Método: {request_info['method']}\n"
            f"Usuário: {request_info['user']}\n"
            f"IP: {request_info['ip']}\n"
            f"Traceback:\n{traceback_text}"
        )
        
        # Retorna None para que o Django processe a exceção normalmente
        return None 