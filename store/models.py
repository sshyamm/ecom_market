from djongo import models
from django.contrib.auth.models import User
import uuid
from django.core.exceptions import ValidationError
from decimal import Decimal
from bson.decimal128 import create_decimal128_context
import decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_countries.fields import CountryField
from django.db import transaction
from django.utils import timezone

D128_CTX = create_decimal128_context()

class Category(models.Model):
    category_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.category_name 

class Item(models.Model):
    # Define choices for item status
    STATUS_CHOICES = (
        ('Select', 'Select'),  # Placeholder option
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('pending', 'Pending'),
    )
    FEATURED_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No'),
    )
    DELETED_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No'),
    )
    PURPOSE_CHOICES = (
    ('sale', 'Sale'),
    ('auction', 'Auction'),
    )
    purpose = models.CharField(max_length=15, choices=PURPOSE_CHOICES)
    category = models.ArrayReferenceField(to=Category, null=True, blank=True, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100)
    item_desc = models.TextField()
    item_year = models.IntegerField(null=True, blank=True)
    item_country = models.CharField(max_length=50, null=True, blank=True)
    item_material = models.CharField(max_length=50, null=True, blank=True)
    item_weight = models.FloatField(null=True, blank=True)
    rate = models.FloatField(null=True, blank=True)
    item_status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)
    featured_item = models.CharField(max_length=3, choices=FEATURED_CHOICES, default='no')
    user = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE)
    is_deleted = models.CharField(max_length=3, choices=DELETED_CHOICES, default='no')
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    incremental_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    owner_profit_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    highest_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    highest_bidder = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE, related_name='highest_bids')
    auto_bidder = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE, related_name='auto_bidder')
    auto_bid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Convert Decimal128 fields to Python Decimal before saving
        if self.starting_bid:
            self.starting_bid = Decimal(str(self.starting_bid))
        if self.incremental_value:
            self.incremental_value = Decimal(str(self.incremental_value))
        if self.highest_bid:
            self.highest_bid = Decimal(str(self.highest_bid))
        if self.owner_profit_amount:
            self.owner_profit_amount = Decimal(str(self.owner_profit_amount))
        if self.auto_bid_amount:
            self.auto_bid_amount = Decimal(str(self.auto_bid_amount))

        super().save(*args, **kwargs) 

    def __str__(self):
        return self.item_name  # Return the item name as its string representation

class Bid(models.Model):
    item = models.ArrayReferenceField(to=Item, on_delete=models.CASCADE, null=True, blank=True)
    bidder = models.ArrayReferenceField(to=User, on_delete=models.CASCADE, null=True, blank=True)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bidder.first()} bid {self.bid_amount} on {self.item.first()}"
    
class ItemImage(models.Model):
    ROOT_IMAGE_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No'),
    )

    item = models.ArrayReferenceField(to=Item, null=True, blank=True, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='coin_images/', null=True, blank=True)
    root_image = models.CharField(max_length=3, choices=ROOT_IMAGE_CHOICES, default='no')

    def __str__(self):
        return f"Item: {self.item.first()} on Root: {self.root_image}"
    
    def clean(self):
        # Check if more than one ItemImage is marked as root_image='yes' for the same Item
        if self.root_image == 'yes' and self.item.first().itemimage_set.filter(root_image='yes').exclude(pk=self.pk).count() > 0:
            raise ValidationError("Only one ItemImage can be marked as root_image='yes' for a Item.")
        if self.root_image == 'yes' and not self.image:
            raise ValidationError("Cannot set root_image to 'yes' without uploading an image.")
        super().clean()
           
@receiver(post_save, sender=Item)
def update_related_calculations(sender, instance, **kwargs):
    if kwargs.get('created', False):  # Check if a new instance of Item is created
        return  # If it's a new instance, no need to update calculations
    else:
        # Update calculations related to OrderItem and CartItem
        for order_item in OrderItem.objects.filter(item=instance):
            order_item.calculate_price()
            order_item.save()
        
        for cart_item in CartItem.objects.filter(item=instance):
            cart_item.calculate_price()
            cart_item.save()

class Profile(models.Model):
    user = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = CountryField()
    phone_no = models.CharField(max_length=20, null=True, blank=True) 
    website = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.user.count() > 0:  # Check if there are any referenced users
            usernames = ', '.join([u.username for u in self.user.all()])
            return f"{usernames}"
        else:
            return "Empty Profile"

class CartItem(models.Model):
    user = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE)
    item = models.ArrayReferenceField(to=Item, null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, null=True, blank=True)
    price = models.FloatField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original field values for change tracking
        for field in self._meta.fields:
            setattr(self, f"_original_{field.name}", getattr(self, field.name))

    def calculate_price(self):
        if self.item and self.item.first():
            item_rate = self.item.first().rate
            if item_rate is not None:
                self.price = self.quantity * item_rate
            else:
                raise ValueError("Item rate is not defined.")
        else:
            raise ValueError("Item is not selected.")

    def save(self, *args, **kwargs):
        self.calculate_price()  # Recalculate the price every time the object is saved
        super().save(*args, **kwargs)

    def __str__(self):
        item_str = ', '.join([str(c) for c in self.item.all()])
        return f"{item_str}"

class CartItemLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )

    cart_item = models.ArrayReferenceField(to=CartItem, on_delete=models.SET_NULL, null=True)
    user = models.ArrayReferenceField(to=User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    changes = models.JSONField(null=True, blank=True)  # To store the changes made

    def __str__(self):
        return f"{self.user.first()} - {self.action} - {self.timestamp}"


@receiver(post_save, sender=CartItem)
def log_cart_item_save(sender, instance, created, **kwargs):
    action = 'create' if created else 'update'
    changes = {}
    
    # Include the ID and username of the user
    user_instance = instance.user.first() if instance.user.count() > 0 else None
    if user_instance:
        changes['user_id'] = str(user_instance.id)
        changes['username'] = user_instance.username
    
    # Include the ID of the item
    changes['item_id'] = str(instance.id)
    
    if not created:
        # Identify changed fields
        for field in instance._meta.fields:
            field_name = field.name
            if field_name != 'id':
                old_value = getattr(instance, f"_original_{field_name}", None)
                new_value = getattr(instance, field_name)
                if old_value != new_value:
                    changes[field_name] = {'old': old_value, 'new': new_value}
    
    cart_item_log = CartItemLog(
        action=action,
        changes=changes or {}  # Use an empty dictionary if changes is None
    )
    cart_item_log.save()
    cart_item_log.cart_item.add(instance)

    if user_instance:
        cart_item_log.user.add(user_instance)
    
    # Store current field values for future comparisons
    for field in instance._meta.fields:
        setattr(instance, f"_original_{field.name}", getattr(instance, field.name))

@receiver(post_delete, sender=CartItem)
def log_cart_item_delete(sender, instance, **kwargs):
    user_instance = instance.user.first() if instance.user.count() > 0 else None
    changes = {'deleted_item': str(instance), 'deleted_item_id': str(instance.id)}  # Include the deleted item's ID
    if user_instance:
        changes['user_id'] = str(user_instance.id)
        changes['username'] = user_instance.username
    
    cart_item_log = CartItemLog(
        action='delete',
        changes=changes
    )
    cart_item_log.save()
    cart_item_log.cart_item.add(instance)
    if user_instance:
        cart_item_log.user.add(user_instance)

class ShippingCharge(models.Model):
    state = models.CharField(max_length=100, null=True, blank=True)
    country = CountryField()
    charge = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.country.name}, {self.state}: {self.charge}"

class ShippingAddress(models.Model):
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = CountryField(null=True, blank=True)
    phone_no = models.CharField(max_length=20, null=True, blank=True) 
    user = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE)

    def get_shipping_charge(self):
        try:
            shipping_charge = ShippingCharge.objects.get(state__iexact=self.state, country=self.country)
        except ShippingCharge.DoesNotExist:
            shipping_charge = None

        if shipping_charge:
            return shipping_charge.charge
        else:
            company = Company.objects.first()  # Assuming there is at least one company
            return company.shipping_charge
        
    def __str__(self):
        return f"{self.address}, {self.city}, {self.state}, {self.postal_code}"

class Offer(models.Model):
    OFFER_TYPE_CHOICES = (
        ('TotalAmount', 'Total Amount Based'),
        ('UserBased', 'User Based'),
    )

    name = models.CharField(max_length=100)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    num_orders = models.IntegerField(null=True, blank=True)
        
    def __str__(self):
        return f"{self.name} ---- {self.discount_percentage}%"

class Order(models.Model):
    # Define choices for order status
    ORDER_STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    invoice_no = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    user = models.ArrayReferenceField(to=User, null=True, blank=True, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    shippingaddress = models.ArrayReferenceField(to=ShippingAddress, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending', null=True, blank=True)
    offer = models.ArrayReferenceField(to=Offer, null=True, blank=True, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            # Generate invoice number
            self.invoice_no = 'INV' + str(uuid.uuid4().hex)[:6].upper()  # Generating a unique invoice number
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no
    
    def calculate_total_amount(self):
        total_amount = Decimal(0)
        order_items = self.orderitem_set.all()  # Assuming the related name for OrderItem is 'orderitem_set'
        for order_item in order_items:
            # Convert Decimal128 to Decimal
            order_item_price_decimal = Decimal(str(order_item.price))
            total_amount += order_item_price_decimal        
        return total_amount
        
    def is_user_based_offer_eligible(self, offer):
        if offer.offer_type != 'UserBased':
            return False
        
        recent_order_with_user_based_offer = Order.objects.filter(
            user=self.user.first(),
            offer__offer_type='UserBased',  # Filter by 'UserBased' offer type
            order_date__lt=self.order_date
        ).order_by('-order_date').first()

        if recent_order_with_user_based_offer:
            num_previous_orders = Order.objects.filter(
                user=self.user.first(),
                order_date__gt=recent_order_with_user_based_offer.order_date,
                order_date__lt=self.order_date
            ).count()
        else:
            num_previous_orders = Order.objects.filter(
                user=self.user.first(),
                order_date__lt=self.order_date
            ).count()

        return num_previous_orders >= offer.num_orders

    def calculate_discounted_total_amount(self):
        total_amount = self.calculate_total_amount()
        discounted_total_amount = total_amount
        
        if self.offer:
            for offer in self.offer.all(): 
                if offer.offer_type == 'TotalAmount': 
                    min_order_amount = offer.min_order_amount
                    min_order_amount_decimal = min_order_amount.to_decimal().quantize(decimal.Decimal('0.01'))
                    if discounted_total_amount >= min_order_amount_decimal:
                        discount_amount = (discounted_total_amount * decimal.Decimal(str(offer.discount_percentage))) / 100
                        discounted_total_amount -= discount_amount  # Apply discount
                elif offer.offer_type == 'UserBased':
                    if self.user.first() and self.is_user_based_offer_eligible(offer):
                        other_offer_discount = Decimal(0)
                        for other_offer in self.offer.exclude(id=offer.id):  # Exclude the current UserBased offer
                            other_offer_discount += other_offer.discount_percentage.to_decimal() 

                        combined_discount_percentage = offer.discount_percentage.to_decimal() + other_offer_discount

                        if other_offer_discount > offer.max_discount_percentage.to_decimal():
                            revised_discount_percentage = Decimal(0)
                        elif combined_discount_percentage > offer.max_discount_percentage.to_decimal():
                            revised_discount_percentage = offer.max_discount_percentage.to_decimal() - other_offer_discount
                        else:
                            revised_discount_percentage = offer.discount_percentage.to_decimal()

                        discount_amount = (discounted_total_amount * decimal.Decimal(str(revised_discount_percentage))) / 100
                        discounted_total_amount -= discount_amount  # Apply discount
        # Add shipping charge
        if self.shippingaddress and self.shippingaddress.first():
            shipping_charge = self.shippingaddress.first().get_shipping_charge()
            discounted_total_amount += Decimal(str(shipping_charge))

        return discounted_total_amount.quantize(decimal.Decimal('0.01'))

    def get_revised_user_based_discount_percentage(self):
        revised_discount_percentage = Decimal(0)
        for offer in self.offer.all():
            if offer.offer_type == 'UserBased' and self.is_user_based_offer_eligible(offer):
                other_offer_discount = Decimal(0)
                for other_offer in self.offer.exclude(id=offer.id):
                    other_offer_discount += other_offer.discount_percentage.to_decimal() 

                combined_discount_percentage = offer.discount_percentage.to_decimal()  + other_offer_discount

                if other_offer_discount > offer.max_discount_percentage.to_decimal() :
                    revised_discount_percentage = Decimal(0)
                elif combined_discount_percentage > offer.max_discount_percentage.to_decimal() :
                    revised_discount_percentage = offer.max_discount_percentage.to_decimal() - other_offer_discount
                else:
                    revised_discount_percentage = offer.discount_percentage.to_decimal() 

        return revised_discount_percentage
    
    def is_offer_eligible(self, offer):
        if offer.offer_type == 'TotalAmount':
            min_order_amount_decimal = decimal.Decimal(str(offer.min_order_amount))
            return self.calculate_total_amount() >= min_order_amount_decimal
        elif offer.offer_type == 'UserBased':
            return self.is_user_based_offer_eligible(offer)
        return False

@receiver(post_save, sender=Order)
@receiver(post_save, sender=Offer)
def remove_zero_revised_discount_offers(sender, instance, **kwargs):
    if sender == Order:
        # If an Order instance is updated
        if kwargs.get('created', False):  # If it's a new instance, do nothing
            return
        else:
            for offer in instance.offer.all():
                if offer.offer_type == 'UserBased':
                    # Check if the revised discount percentage is 0
                    if instance.get_revised_user_based_discount_percentage() == 0:
                        # Remove the offer from the order
                        instance.offer.remove(offer)
                        # Save the order
                        instance.save()
    
    elif sender == Offer:
        # If an Offer instance is updated, check all related orders
        related_orders = instance.order_set.all()
        for order in related_orders:
            for offer in order.offer.all():
                if offer.offer_type == 'UserBased':
                    # Check if the revised discount percentage is 0
                    if order.get_revised_user_based_discount_percentage() == 0:
                        # Remove the offer from the order
                        order.offer.remove(offer)
                        # Save the order
                        order.save()

@receiver(post_save, sender=Order)
def handle_order_change(sender, instance, **kwargs):
    with transaction.atomic():
        for user in User.objects.all():
            for order in user.order_set.all():
                for offer in order.offer.all():
                    # Check if the offer is eligible
                    if not order.is_offer_eligible(offer):
                        # Remove the offer from the order
                        order.offer.remove(offer)
                        # Save the order
                        order.save() 

@receiver(post_save, sender=Offer)
def handle_offer_change(sender, instance, **kwargs):
    with transaction.atomic():
        for order in Order.objects.all():
            # Check if the offer is in the order's offer array
            if instance in order.offer.all():
                # Check eligibility
                if not order.is_offer_eligible(instance):
                    # Remove the offer from the order
                    order.offer.remove(instance)
                    # Save the order
                    order.save()        

class OrderItem(models.Model):
    order = models.ArrayReferenceField(to=Order, null=True, blank=True, on_delete=models.CASCADE)
    item = models.ArrayReferenceField(to=Item, null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)  # Add price field

    def calculate_price(self):
        if self.item and self.item.first():
            item_rate = self.item.first().rate
            if item_rate is not None:
                self.price = Decimal(self.quantity) * Decimal(item_rate)
            else:
                raise ValueError("Item rate is not defined.")
        else:
            raise ValueError("Item is not selected.")

    def save(self, *args, **kwargs):
        self.calculate_price()  # Recalculate the price every time the object is saved
        super().save(*args, **kwargs)

    def __str__(self):
        item_str = ', '.join([str(c) for c in self.item.all()])
        return f"{item_str}"
        
class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = CountryField()
    email = models.EmailField(max_length=255)
    contact_no = models.CharField(max_length=20)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name