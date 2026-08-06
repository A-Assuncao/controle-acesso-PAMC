"""
Filtros customizados para templates do app core.

Uso:
    {% load core_extras %}
    {{ meu_dict|get_item:minha_chave }}
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Acessa dictionary[key] de forma segura - retorna string vazia se nao existir."""
    if not dictionary:
        return ''
    try:
        return dictionary[key]
    except (KeyError, TypeError):
        return ''
