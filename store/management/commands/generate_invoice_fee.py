from django.core.management.base import BaseCommand
from store.models import FeatureBanner, Order, OrderItem
from decimal import Decimal

class Command(BaseCommand):
    help = 'Generates invoices and creates orders for items ready for auction.'

    def handle(self, *args, **options):
        feature_banners = FeatureBanner.objects.all()

        for fb in feature_banners:
            if not fb.asked_for:
                continue
            user = fb.user.first() if fb.user.count()>0 else None
            item = fb.item.first()

            if user and item:
                # Check if an order already exists for this user and item
                existing_order = Order.objects.filter(user=user, orderitem__item=item, order_for='FeatureBanner').first()
                if existing_order:
                    self.stdout.write(self.style.WARNING(f'Skipping FeatureBanner ID: {fb.id}. Order already exists for user and item.'))
                    continue         
                # Create Order
                order = Order.objects.create(status='Pending')
                order.user.add(user)
                order.order_for = 'FeatureBanner'
                order.save()
                
                # Determine price based on 'asked_for'
                item = fb.item.first()
                price = Decimal(0)
                if fb.asked_for == 'featured':
                    price = Decimal(item.featured_fee.to_decimal())
                elif fb.asked_for == 'banner':
                    price = Decimal(item.banner_fee.to_decimal())
                elif fb.asked_for == 'both':
                    price = Decimal(item.featured_fee.to_decimal()) + Decimal(item.banner_fee.to_decimal())

                # Create OrderItem
                order_item = OrderItem()
                order_item.order.add(order)
                order_item.item.add(fb.item.first())
                order_item.quantity = 1
                order_item.price = price
                order_item.save(skip_calculate_price=True)

                fb.order.add(order)
                fb.save()

                self.stdout.write(self.style.SUCCESS(f'Order and OrderItem created for FeatureBanner ID: {fb.id}'))
            else:
                self.stdout.write(self.style.WARNING(f'No user found for FeatureBanner ID: {fb.id}'))
