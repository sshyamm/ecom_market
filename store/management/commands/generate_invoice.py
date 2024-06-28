from django.core.management.base import BaseCommand
from django.utils import timezone
from store.models import Item, ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User  # Assuming User model is imported

class Command(BaseCommand):
    help = 'Generates invoices and creates orders for items ready for auction.'

    def handle(self, *args, **options):
        current_time = timezone.now()

        items_to_process = Item.objects.filter(
            is_deleted='no',
            purpose='auction',
            end_time__lte=current_time
        )

        for item in items_to_process:
            # Get the highest bidders
            highest_bidders = item.highest_bidder.all()

            for highest_bidder in highest_bidders:
                # Check if there is already an order for this user and item
                existing_order = Order.objects.filter(
                    user=highest_bidder,
                    orderitem__item=item,
                    orderitem__item__purpose='auction',
                ).first()

                if existing_order:
                    self.stdout.write(self.style.WARNING(f"Order already exists for {highest_bidder.username} for item {item.item_name}"))
                    continue
                
                # Filter ShippingAddress for each highest bidder with primary='yes'
                shipping_address = ShippingAddress.objects.filter(user=highest_bidder, primary='yes').first()

                if shipping_address:
                    # Create an Order instance
                    order = Order.objects.create(status='Pending')
                    order.user.add(highest_bidder)
                    order.shippingaddress.add(shipping_address)
                    order.save()

                    # Create OrderItem instance
                    order_item = OrderItem()
                    order_item.order.add(order)
                    order_item.item.add(item)
                    order_item.quantity = 1
                    order_item.save()

                    self.stdout.write(self.style.SUCCESS(f"Invoice generated for {highest_bidder.username} for item {item.item_name}"))

                else:
                    self.stdout.write(self.style.WARNING(f"No primary shipping address found for {highest_bidder.username}"))

            if not highest_bidders:
                self.stdout.write(self.style.WARNING(f"No highest bidders found for item {item.item_name}"))
