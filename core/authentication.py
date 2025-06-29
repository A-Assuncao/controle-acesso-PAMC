"""
Backend de autenticação externa para Canaimé.

Este módulo implementa autenticação via request HTTP para o sistema Canaimé,
extraindo informações do usuário e criando/autenticando localmente.
"""

import logging
import os
import requests
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup
import urllib3
from .models import PerfilUsuario

# Desabilita warnings de SSL para o Canaimé
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

User = get_user_model()


class CanaimeAuthBackend(BaseBackend):
    """
    Backend de autenticação que valida credenciais no Canaimé.
    
    Fluxo:
    1. Faz request POST para o Canaimé com login/senha
    2. Extrai nome completo e foto da resposta HTML
    3. Cria ou atualiza usuário local como OPERADOR
    4. Retorna o usuário autenticado
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Backend Canaimé - APENAS para criação de novos usuários.
        
        NÃO interfere no login de usuários existentes no banco local.
        Só é usado quando explicitamente chamado pela view.
        
        Args:
            request: Request HTTP
            username: Login
            password: Senha
            
        Returns:
            None - este backend não autentica automaticamente
        """
        # Este backend não autentica automaticamente
        # Ele é usado apenas para validação manual via _authenticate_canaime
        return None
    
    def get_user(self, user_id):
        """Retorna usuário pelo ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _authenticate_canaime(self, username, password):
        """
        Faz autenticação no Canaimé e extrai dados do usuário.
        
        Args:
            username: Login
            password: Senha
            
        Returns:
            dict com dados do usuário ou None se falhar
        """
        # URL de login alternativa sem reCAPTCHA
        login_url = os.getenv('CANAIME_LOGIN_URL', "https://canaime.com.br/sgp2rr/login/login_principal.php")
        
        # Headers de navegador sem JavaScript para evitar reCAPTCHA
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://canaime.com.br/sgp2rr/login/login_principal.php',
        }
        
        # Dados de login (baseado nos nomes dos campos do formulário)
        data = {
            'usuario': username,  # Campo correto é "usuario", não "login"
            'senha': password,
        }
        
        try:
            # Cria sessão para manter cookies
            session = requests.Session()
            session.headers.update(headers)
            
            # Primeiro, pega a página de login para obter cookies de sessão
            logger.info("Obtendo página de login para cookies de sessão...")
            login_page = session.get(
                login_url,
                verify=False,
                timeout=30
            )
            
            # Faz request POST para login ignorando certificados SSL
            logger.info(f"Fazendo login para usuário: {username}")
            response = session.post(
                login_url, 
                data=data, 
                verify=False,  # Ignora erros de certificado
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.warning(f"Canaimé retornou status {response.status_code}")
                return None
            
            # Verifica se o login foi bem-sucedido (procura pelo iframe das áreas)
            if 'iframe' not in response.text or 'areas/unidades/index.php' not in response.text:
                logger.warning(f"Login falhou - estrutura esperada não encontrada. URL final: {response.url}")
                return None
            
            # Agora precisa buscar os dados do usuário na página de áreas
            logger.info("Buscando dados do usuário na página de áreas...")
            areas_url = os.getenv('CANAIME_AREAS_URL', "https://canaime.com.br/sgp2rr/areas/unidades/index.php")
            areas_response = session.get(
                areas_url,
                verify=False,
                timeout=30
            )
            
            if areas_response.status_code != 200:
                logger.warning(f"Falha ao acessar página de áreas: {areas_response.status_code}")
                return None
            
            # Pega o HTML como bytes brutos para preservar encoding original
            nome_completo = None
            html_bytes = areas_response.content
            
            try:
                # Decodifica como ISO-8859-1 (que preserva todos os bytes como chars)
                html_bruto = html_bytes.decode('iso-8859-1')
                
                # Debug: compara HTML bruto vs processado
                logger.info(f"Tamanho HTML bytes: {len(html_bytes)}")
                logger.info(f"Tamanho HTML bruto: {len(html_bruto)}")
                logger.info(f"Tamanho HTML processado: {len(areas_response.text)}")
                
                # Procura por diferenças no nome especificamente
                if 'tituloAmarelo' in html_bruto:
                    # Extrai um trecho pequeno com o nome para comparar
                    inicio = html_bruto.find('tituloAmarelo')
                    if inicio != -1:
                        trecho_bruto = html_bruto[inicio:inicio+200]
                        logger.info(f"Trecho bruto: {repr(trecho_bruto)}")
                        
                if 'tituloAmarelo' in areas_response.text:
                    inicio = areas_response.text.find('tituloAmarelo')
                    if inicio != -1:
                        trecho_processado = areas_response.text[inicio:inicio+200]
                        logger.info(f"Trecho processado: {repr(trecho_processado)}")
                
                # Debug: salva HTML para análise
                try:
                    # Salva HTML bruto (preserva encoding original)
                    with open('logs/canaime_areas_bruto.html', 'w', encoding='iso-8859-1') as f:
                        f.write(html_bruto)
                    logger.info("HTML bruto salvo em logs/canaime_areas_bruto.html")
                    
                    # Salva HTML processado para comparação
                    with open('logs/canaime_areas_processado.html', 'w', encoding='utf-8') as f:
                        f.write(areas_response.text)
                    logger.info("HTML processado salvo em logs/canaime_areas_processado.html")
                except Exception as e:
                    logger.warning(f"Erro ao salvar HTML debug: {e}")
                
                # Busca por padrão no HTML bruto que contém o nome
                import re
                
                # Padrão para capturar conteúdo da classe tituloAmarelo
                padrao_titulo = r'class="tituloAmarelo"[^>]*>(.*?)</strong>'
                matches = re.findall(padrao_titulo, html_bruto, re.DOTALL | re.IGNORECASE)
                
                logger.info(f"Total de matches encontrados: {len(matches)}")
                
                for i, match in enumerate(matches):
                    logger.info(f"=== MATCH {i+1} ===")
                    logger.info(f"Match bruto: {repr(match)}")
                    
                    # Remove tags HTML
                    texto_limpo = re.sub(r'<br[^>]*>', '\n', match, flags=re.IGNORECASE)
                    texto_limpo = re.sub(r'<[^>]+>', '', texto_limpo)
                    
                    # Separa por quebras de linha
                    linhas = []
                    for linha in texto_limpo.split('\n'):
                        linha_limpa = re.sub(r'\s+', ' ', linha.strip())
                        if linha_limpa:
                            linhas.append(linha_limpa)
                    
                    logger.info(f"Linhas extraídas: {linhas}")
                    
                    # Procura pela linha que contém o nome (não é o username)
                    for j, linha in enumerate(linhas):
                        logger.info(f"  Linha {j+1}: '{linha}'")
                        
                        if (len(linha) > 10 and 
                            ' ' in linha and 
                            linha != username and
                            not linha.isalnum()):
                            
                            logger.info(f"  ✅ LINHA APROVADA: {linha}")
                            
                            # CORREÇÃO: Usa a lógica que funciona no teste manual
                            # Remove o username se estiver concatenado
                            nome_sem_username = linha
                            if username in linha:
                                nome_sem_username = linha.replace(username, '')
                                logger.info(f"  🔧 Username removido: '{linha}' -> '{nome_sem_username}'")
                            
                            # Aplica correção CP1252 apenas se detectar encoding corrompido
                            if '\x87' in nome_sem_username or 'Ã\x83' in nome_sem_username:
                                try:
                                    # Correção genérica de encoding corrompido do Canaimé
                                    # Mapeamento de caracteres corrompidos mais comuns
                                    correcoes_encoding = {
                                        'Ã\x87Ã\x83': 'Ç',  # ÇÃO
                                        'Ã\x87': 'Ç',       # Ç
                                        'Ã\x83': 'Ã',       # Ã
                                        'Ã\x81': 'Á',       # Á
                                        'Ã\x89': 'É',       # É
                                        'Ã\x8d': 'Í',       # Í
                                        'Ã\x93': 'Ó',       # Ó
                                        'Ã\x9a': 'Ú',       # Ú
                                        'Ã\x80': 'À',       # À
                                        'Ã\x88': 'È',       # È
                                        'Ã\x82': 'Â',       # Â
                                        'Ã\x8a': 'Ê',       # Ê
                                        'Ã\x94': 'Ô',       # Ô
                                    }
                                    
                                    nome_corrigido = nome_sem_username
                                    for corrompido, correto in correcoes_encoding.items():
                                        nome_corrigido = nome_corrigido.replace(corrompido, correto)
                                    
                                    nome_completo = nome_corrigido.strip()
                                    logger.info(f"  ✅ CORREÇÃO DE ENCODING APLICADA: '{nome_sem_username}' -> '{nome_completo}'")
                                except Exception as e:
                                    nome_completo = nome_sem_username.strip()
                                    logger.info(f"  ⚠️ CORREÇÃO FALHOU ({e}): mantendo '{nome_sem_username}'")
                            else:
                                # Nome já está correto, não precisa de correção
                                nome_completo = nome_sem_username.strip()
                                logger.info(f"  ✅ NOME JÁ CORRETO: '{nome_completo}'")
                            break
                        else:
                            logger.info(f"  ❌ Linha rejeitada")
                            
                    if nome_completo:
                        logger.info(f"✅ NOME ENCONTRADO NO MATCH {i+1}: {nome_completo}")
                        break
                        
            except Exception as e:
                logger.debug(f"Erro ao extrair nome do HTML bruto: {str(e)}")
                
            # Fallback: usa BeautifulSoup se não conseguiu extrair do HTML bruto
            if not nome_completo:
                soup = BeautifulSoup(areas_response.text, 'html.parser')
                elementos_titulo = soup.select('.tituloAmarelo')
                for elem in elementos_titulo:
                    texto_completo = elem.get_text()
                    if '\n' in texto_completo:
                        linhas = [linha.strip() for linha in texto_completo.split('\n') if linha.strip()]
                        for linha in linhas:
                            if (len(linha) > 10 and ' ' in linha and linha != username):
                                nome_completo = linha
                                logger.info(f"Nome encontrado via BeautifulSoup fallback: {nome_completo}")
                                break
                        if nome_completo:
                            break
            
            if nome_completo:
                # Limpa e processa o nome
                nome_completo = self._processar_nome(nome_completo, username)
                logger.info(f"Nome processado: {nome_completo}")
            else:
                # Se não encontrou nome, usa o username como fallback
                logger.warning("Nome não encontrado na página de áreas, usando username como fallback")
                nome_completo = username.title()
            
            # Extrai foto de /html/body/table[1]/tbody/tr/td[3]/img
            foto_url = None
            try:
                # Cria BeautifulSoup se ainda não existe
                if 'soup' not in locals():
                    soup = BeautifulSoup(areas_response.text, 'html.parser')
                    
                foto_element = soup.select('body > table:nth-of-type(1) tbody tr td:nth-of-type(3) img')
                if not foto_element:
                    foto_element = soup.select('table:first-of-type tbody tr td:nth-of-type(3) img')
                    
                if foto_element:
                    foto_src = foto_element[0].get('src')
                    if foto_src:
                        # Se for URL relativa, faz absoluta
                        if foto_src.startswith('/'):
                            foto_url = f"https://canaime.com.br{foto_src}"
                        elif not foto_src.startswith('http'):
                            foto_url = f"https://canaime.com.br/sgp2rr/areas/{foto_src}"
                        else:
                            foto_url = foto_src
                        logger.info(f"Foto extraída: {foto_url}")
            except Exception as e:
                logger.warning(f"Erro ao extrair foto: {str(e)}")
            
            # Valida se conseguiu extrair pelo menos o nome
            if not nome_completo or len(nome_completo.strip()) < 3:
                logger.warning(f"Nome extraído inválido: '{nome_completo}'")
                return None
            
            # Separa primeiro nome e sobrenome
            partes_nome = nome_completo.strip().split()
            if len(partes_nome) >= 2:
                first_name = partes_nome[0]
                last_name = ' '.join(partes_nome[1:])
            else:
                first_name = nome_completo.strip()
                last_name = ''
            
            return {
                'nome_completo': nome_completo,
                'first_name': first_name,
                'last_name': last_name,
                'foto_url': foto_url,
                'username': username
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao conectar SGP2RR: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado na autenticação SGP2RR: {str(e)}")
            return None
    
    def _processar_nome(self, nome_bruto, username):
        """
        Processa o nome extraído do Canaimé.
        
        - Remove o username se estiver concatenado
        - Corrige problemas de encoding
        - Retorna apenas primeiro e último nome
        
        Args:
            nome_bruto: Nome como extraído do HTML
            username: Login do usuário para remover se estiver concatenado
            
        Returns:
            Nome limpo no formato "Primeiro Último"
        """
        try:
            logger.info(f"🎯 Processando nome encontrado: '{nome_bruto}'")
            
            # Remove o username se estiver no final do nome (mais seguro)
            if username in nome_bruto:
                # Remove apenas se estiver no final (evita remover partes do nome)
                if nome_bruto.endswith(username):
                    nome_limpo = nome_bruto[:-len(username)]
                    logger.info(f"🔧 Username removido do final: '{nome_bruto}' -> '{nome_limpo}'")
                else:
                    nome_limpo = nome_bruto.replace(username, '')
                    logger.info(f"🔧 Username removido: '{nome_bruto}' -> '{nome_limpo}'")
            else:
                nome_limpo = nome_bruto
                logger.info(f"🔧 Username não encontrado no nome, mantendo: '{nome_limpo}'")
            
            # Remove caracteres especiais e números extras, mas preserva acentos
            import re
            nome_limpo = re.sub(r'[^\w\sÀ-ÿ]', ' ', nome_limpo)
            logger.info(f"🔧 Após remover caracteres especiais: '{nome_limpo}'")
            
            # Remove espaços extras e normaliza
            nome_limpo = ' '.join(nome_limpo.split())
            logger.info(f"🔧 Após normalizar espaços: '{nome_limpo}'")
            
            # Converte para title case
            nome_limpo = nome_limpo.title()
            logger.info(f"🔧 Após title case: '{nome_limpo}'")
            
            # Extrai apenas primeiro e último nome
            partes = nome_limpo.split()
            if len(partes) >= 2:
                primeiro_nome = partes[0]
                ultimo_nome = partes[-1]
                nome_final = f"{primeiro_nome} {ultimo_nome}"
                logger.info(f"✅ Nome final (primeiro + último): '{nome_final}'")
            elif len(partes) == 1:
                nome_final = partes[0]
                logger.info(f"✅ Nome final (apenas um): '{nome_final}'")
            else:
                nome_final = "Usuário"
                logger.info(f"⚠️ Nome final (fallback): '{nome_final}'")
            
            return nome_final
            
        except Exception as e:
            logger.error(f"Erro ao processar nome '{nome_bruto}': {str(e)}")
            # Fallback: usa apenas o primeiro nome se possível
            try:
                primeira_palavra = nome_bruto.split()[0] if nome_bruto.split() else "Usuário"
                return primeira_palavra.title()
            except:
                return "Usuário"
    
    def _create_or_update_user(self, username, canaime_data, password=None):
        """
        Cria ou atualiza usuário local com dados do Canaimé.
        
        Args:
            username: Login do usuário
            canaime_data: Dados extraídos do Canaimé
            password: Senha do usuário (opcional)
            
        Returns:
            User object
        """
        try:
            # Tenta encontrar usuário existente
            try:
                user = User.objects.get(username=username)
                # Atualiza dados do usuário existente
                user.first_name = canaime_data['first_name']
                user.last_name = canaime_data['last_name']
                
                # Se uma senha foi fornecida, atualiza ela também
                if password:
                    user.set_password(password)
                
                user.save()
                logger.info(f"Usuário existente atualizado: {username}")
                
            except User.DoesNotExist:
                # Cria novo usuário
                user = User.objects.create_user(
                    username=username,
                    first_name=canaime_data['first_name'],
                    last_name=canaime_data['last_name'],
                    is_staff=False,  # Usuários Canaimé não são staff por padrão
                    is_active=True
                )
                
                # Define a senha do Canaimé para permitir login local futuro
                if password:
                    user.set_password(password)
                    logger.info(f"Senha definida para usuário: {username}")
                else:
                    # Fallback: senha temporária baseada no username
                    user.set_password(f"{username}_temp_2024")
                    logger.warning(f"Senha temporária definida para usuário: {username}")
                
                user.save()
                logger.info(f"Novo usuário criado: {username}")
            
            # Cria ou atualiza perfil como OPERADOR
            perfil, created = PerfilUsuario.objects.get_or_create(
                usuario=user,
                defaults={
                    'tipo_usuario': 'OPERADOR',
                    'precisa_trocar_senha': False,  # Não precisa trocar pois usa mesma senha do Canaimé
                    'foto_sgp2rr': canaime_data.get('foto_url', '')
                }
            )
            
            if not created:
                # Atualiza foto se mudou
                if canaime_data.get('foto_url'):
                    perfil.foto_sgp2rr = canaime_data['foto_url']
                    perfil.save()
            
            return user
            
        except Exception as e:
            logger.error(f"Erro ao criar/atualizar usuário {username}: {str(e)}")
            return None 