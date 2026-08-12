"""Custom template filters for the app."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Return mapping[key] (e.g. a dict lookup using a template variable key)."""
    if mapping is None:
        return None
    return mapping.get(key)
