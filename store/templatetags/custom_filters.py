# custom_filters.py

from django import template

register = template.Library()

@register.filter(name='get_attribute')
def get_attribute(obj, attr_name):
    return getattr(obj, attr_name)
