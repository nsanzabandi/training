from django import template
import os
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def dict_get(value, key):
    return value.get(key) if isinstance(value, dict) else ''


register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)