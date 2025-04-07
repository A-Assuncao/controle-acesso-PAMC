from django.shortcuts import redirect
from django.urls import reverse

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
                
                # Se o usuário precisa trocar a senha e não está na página de troca de senha
                if perfil.precisa_trocar_senha and not request.path == reverse('trocar_senha'):
                    # Lista de páginas permitidas mesmo quando precisa trocar senha
                    paginas_permitidas = [
                        reverse('logout'),      # Permite sair do sistema
                        reverse('home'),        # Permite acessar o dashboard
                        reverse('static', kwargs={'path': ''}).rstrip('/'), # Permite arquivos estáticos
                    ]
                    
                    # Verifica se o caminho atual está na lista de permitidos
                    for pagina in paginas_permitidas:
                        if request.path.startswith(pagina):
                            return self.get_response(request)
                    
                    # Garante que a página de login seja acessível para evitar loops
                    if request.path.startswith(reverse('login')):
                        return self.get_response(request)
                    
                    # Redireciona para a página de troca de senha
                    return redirect('trocar_senha')
            except Exception as e:
                # Se o usuário não tem perfil ou ocorreu um erro, ignora
                # Registra o erro em ambiente de desenvolvimento para debug
                import logging
                logging.getLogger('django').error(f"Erro no TrocaSenhaMiddleware: {str(e)}")
                pass
                
        # Processa normalmente se não precisa trocar a senha
        response = self.get_response(request)
        return response 