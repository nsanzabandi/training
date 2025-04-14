from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def dict_get(value, key):
    return value.get(key) if isinstance(value, dict) else ''
