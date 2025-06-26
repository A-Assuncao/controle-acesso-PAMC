"""
URL configuration for controle_acesso project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

# Handlers de erro personalizados
handler500 = 'core.views.handler500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('login/', auth_views.LoginView.as_view(
        template_name='core/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        template_name='core/logout.html',
        next_page='login'
    ), name='logout'),
    
    # Adicionando rota explícita para arquivos estáticos em produção local
    # path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    # path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Configuração para servir arquivos estáticos e de mídia em desenvolvimento
if settings.DEBUG:
    # Em ambiente de desenvolvimento, o Django serve automaticamente
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Em produção, adicionamos os caminhos de mídia
    # Os arquivos estáticos já são tratados acima
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
