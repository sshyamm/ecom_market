from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import *
from decimal import Decimal
from store.forms import *
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.templatetags.static import static

def display_username(obj):
    if obj.user:
        first_user = obj.user.first()
        if first_user:
            return first_user.username
    return "None"

def display_item(obj):
    if obj:
        return str(obj)
    else:
        return "None"

def display_item_image(obj):
    if obj.image:
        return format_html('<img src="{}" style="max-width:100px; max-height:100px;">'.format(obj.image.url))
    else:
        default_image_url = '/static/img/default.jpg'  
        return format_html('<img src="{}" style="max-width:100px; max-height:100px;">'.format(default_image_url))
        
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'manage_items_link')

    def manage_items_link(self, obj):
        manage_items_url = reverse('admin:store_item_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">Manage Items</a>', manage_items_url)

    manage_items_link.short_description = 'Manage Items'

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'categoryName', 'item_name', 'display_root_image', 'item_desc', 'item_year', 'item_country', 
        'item_material', 'item_weight', 'rate', 
        'item_status', display_username, 'featured_item', 'view_images', 'is_deleted', 'starting_bid', 'end_time', 
        'incremental_value', 'owner_profit_amount', 'highest_bid', 
        'display_highest_bidder', 'display_auto_bidder', 'auto_bid_amount', 'manage_bids_link'
    )
    form = ItemForm

    def display_highest_bidder(self, obj):
        if obj.highest_bidder:
            first_user = obj.highest_bidder.first()
            if first_user:
                return first_user.username
        return "None"
    def display_auto_bidder(self, obj):
        if obj.auto_bidder:
            first_user = obj.auto_bidder.first()
            if first_user:
                return first_user.username
        return "None"
    
    def categoryName(self, obj):
        category = obj.category.first()
        if category:
            return category.category_name
        return "None"

    def display_root_image(self, obj):
        # Fetch the root image for the item
        root_image = ItemImage.objects.filter(item=obj, root_image='yes').first()
        if root_image and root_image.image:
            return format_html('<img src="{}" style="max-width:100px; max-height:100px;">', root_image.image.url)
        else:
            default_image_url = static('img/default.jpg')
            return format_html('<img src="{}" style="max-width:100px; max-height:100px;" alt="{}">', default_image_url, obj.item_name)

    display_root_image.short_description = 'Root Image'

    def view_images(self, obj):
        view_url = reverse('admin:store_itemimage_changelist') + f'?item__id__exact={obj.id}'
        return format_html('<a href="{}">View Images</a>', view_url)

    view_images.short_description = 'Images'

    def add_view(self, request, form_url='', extra_context=None):
        category_id = request.GET.get('category_id')
        if category_id:
            category = get_object_or_404(Category, pk=category_id)
            request.POST = request.POST.copy()
            request.POST['category'] = category.id
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        category_id = request.GET.get('category__id__exact')
        if category_id:
            add_url = reverse('admin:store_item_add') + f'?category_id={category_id}'
            if extra_context is None:
                extra_context = {}
            extra_context['add_url'] = add_url
        return super().changelist_view(request, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        category_id = obj.category.first().id
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return HttpResponseRedirect(reverse('admin:store_item_changelist') + f'?category__id__exact={category_id}')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'category' in form.base_fields:
            form.base_fields['category'].widget.attrs['style'] = 'display:none;'
        return form
    
    def manage_bids_link(self, obj):
        view_url = reverse('admin:store_bid_changelist') + f'?item__id__exact={obj.id}'
        return format_html('<a href="{}">Manage Bids</a>', view_url)

    view_images.short_description = 'Manage_bids'

    def has_module_permission(self, request):
        return False

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = (
        display_item, 'display_bidder', 'bid_amount', 'timestamp'
    )
    form = BidAdminForm

    def display_bidder(self, obj):
        if obj.bidder:
            first_user = obj.bidder.first()
            if first_user:
                return first_user.username
        return "None"

    def add_view(self, request, form_url='', extra_context=None):
        item_id = request.GET.get('item_id')
        if item_id:
            item = get_object_or_404(Item, pk=item_id)
            request.POST = request.POST.copy()
            request.POST['item'] = item.id
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        item_id = request.GET.get('item__id__exact')
        if item_id:
            add_url = reverse('admin:store_bid_add') + f'?item_id={item_id}'
            if extra_context is None:
                extra_context = {}
            extra_context['add_url'] = add_url
        return super().changelist_view(request, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        item_id = obj.item.first().id
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return HttpResponseRedirect(reverse('admin:store_bid_changelist') + f'?item__id__exact={item_id}')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'item' in form.base_fields:
            form.base_fields['item'].widget.attrs['style'] = 'display:none;'
        return form
    
    def has_module_permission(self, request):
        return False
    
@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    form = ItemImageForm
    list_display = ('display_item', display_item_image, 'root_image')

    def display_item(self, obj):
        return display_item(obj.item.first())

    display_item.short_description = 'Item'

    def add_view(self, request, form_url='', extra_context=None):
        item_id = request.GET.get('item_id')
        if item_id:
            item = get_object_or_404(Item, pk=item_id)
            request.POST = request.POST.copy()
            request.POST['item'] = item.id
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        item_id = request.GET.get('item__id__exact')
        if item_id:
            add_url = reverse('admin:store_itemimage_add') + f'?item_id={item_id}'
            if extra_context is None:
                extra_context = {}
            extra_context['add_url'] = add_url
        return super().changelist_view(request, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        item_id = obj.item.first().id
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return HttpResponseRedirect(reverse('admin:store_itemimage_changelist') + f'?item__id__exact={item_id}')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'item' in form.base_fields:
            form.base_fields['item'].widget.attrs['style'] = 'display:none;'
        return form
    
    def has_module_permission(self, request):
        return False

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (display_username, 'bio', 'state', 'country', 'phone_no', 'website')
    form = ProfileForm

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (display_username, 'display_item', 'quantity', 'price', 'created_at')
    form = CartItemForm

    def display_item(self, obj):
        return display_item(obj)

    display_item.short_description = 'Item'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', display_username, 'order_date', 'get_shipping_address', 'status', 'get_offer', 'view_order_items', 'total_amount')
    form = OrderForm
    search_fields = ['invoice_no', 'user__username', 'shippingaddress__address', 'shippingaddress__city', 'shippingaddress__state', 'shippingaddress__postal_code']
    list_filter = ['invoice_no', 'user__username', 'order_date', 'status', 'shippingaddress__city', 'shippingaddress__state', 'offer__name']


    def get_shipping_address(self, obj):
        shipping_address = obj.shippingaddress.first()
        if shipping_address:
            return f"{shipping_address.address}, {shipping_address.city}, {shipping_address.state}, {shipping_address.postal_code}"
        return "None"
    
    def get_offer(self, obj):
        offers = obj.offer.all()  # Changed from .first() to .all()
        if offers:
            return ", ".join([offer.name for offer in offers])
        return "None"
    
    get_shipping_address.short_description = 'Shipping Address'

    def view_order_items(self, obj):
        view_url = reverse('admin:store_orderitem_changelist') + f'?order__id__exact={obj.id}'
        return format_html('<a href="{}">View Orders</a>', view_url)
    
    def total_amount(self, obj):
        return obj.calculate_discounted_total_amount()

    total_amount.short_description = 'Total Amount'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('get_invoice_no', 'display_item', 'quantity', 'price')
    form = OrderItemForm

    def get_invoice_no(self, obj):
        order = obj.order.first()
        if order:
            return order.invoice_no
        return "None"

    def display_item(self, obj):
        return display_item(obj)

    display_item.short_description = 'Item'
    get_invoice_no.short_description = 'Invoice No'

    def add_view(self, request, form_url='', extra_context=None):
        order_id = request.GET.get('order_id')
        if order_id:
            order = get_object_or_404(Order, pk=order_id)
            request.POST = request.POST.copy()
            request.POST['order'] = order.id
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        order_id = request.GET.get('order__id__exact')
        if order_id:
            add_url = reverse('admin:store_orderitem_add') + f'?order_id={order_id}'
            if extra_context is None:
                extra_context = {}
            extra_context['add_url'] = add_url
        return super().changelist_view(request, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        order_id = obj.order.first().id
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return HttpResponseRedirect(reverse('admin:store_orderitem_changelist') + f'?order__id__exact={order_id}')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'order' in form.base_fields:
            form.base_fields['order'].widget.attrs['style'] = 'display:none;'
        return form
    
    def has_module_permission(self, request):
        return False

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = (display_username, 'phone_no', 'address', 'state', 'city', 'postal_code', 'country')
    form = ShippingAddressForm

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'city', 'state', 'postal_code', 'country', 'email', 'contact_no', 'shipping_charge')

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'discount_percentage', 'min_order_amount', 'max_discount_percentage', 'num_orders', 'discount_percentage')
    form = OfferForm

@admin.register(ShippingCharge)
class ShippingChargeAdmin(admin.ModelAdmin):
    list_display = ('state', 'country', 'charge')

@admin.register(CartItemLog)
class CartItemLogAdmin(admin.ModelAdmin):
    list_display = ('get_cart', display_username, 'action', 'timestamp', 'changes')

    def get_cart(self, obj):
        cart = obj.cart_item.first()
        if cart:
            item = cart.item.first()  # Assuming item is an ArrayReferenceField containing one item
            if item:
                return item.item_name
        return "None"
    get_cart.short_description = 'Cart Item Name'