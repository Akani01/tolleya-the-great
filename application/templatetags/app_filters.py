from django import template

register = template.Library()

@register.filter
def status_color(status):
    color_map = {
        'draft': 'secondary',
        'ready': 'info',
        'analyzing': 'primary',
        'filling': 'warning',
        'waiting_review': 'info',
        'completed': 'success',
        'submitted': 'success',
        'failed': 'danger',
        'approved': 'success',
        'rejected': 'danger',
    }
    return color_map.get(status, 'secondary')