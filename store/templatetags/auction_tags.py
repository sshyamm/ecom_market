from django import template
from store.models import OrderItem

register = template.Library()

@register.filter
def get_order_by_item(orders, item):
    for order in orders:
        if OrderItem.objects.filter(order=order, item=item).count() > 0:
            return order
    return None