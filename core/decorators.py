from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Você não tem permissão para acessar esta página. Entre em contato com um administrador.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view 