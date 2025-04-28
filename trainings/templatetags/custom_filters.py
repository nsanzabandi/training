from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key) if isinstance(d, dict) else None


@register.filter
def status_color(status):
    color_map = {
        'approved': 'success',
        'pending': 'warning text-dark',
        'rejected': 'danger',
        'in_progress': 'info',
        'completed': 'primary',
        'canceled': 'secondary',
    }
    return color_map.get(status.lower(), 'secondary')
