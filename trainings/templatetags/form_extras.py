from django import template
from django.forms.boundfield import BoundField  # ✅ import this to check the type

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    if isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css})
    return field  # return original value if it's not a form field
