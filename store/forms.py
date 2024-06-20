from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from django.forms import widgets

class BidAdminForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['item', 'bidder', 'bid_amount']

    def __init__(self, *args, **kwargs):
        super(BidAdminForm, self).__init__(*args, **kwargs)
        if 'item' in self.fields:
            self.fields['item'].widget.attrs['style'] = 'display: none;'
            self.fields['item'].label = ''
            self.fields['item'].widget.can_add_related = False

class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['bid_amount']  # Specify fields you want to include from Bid model

    def clean_bid_amount(self):
        bid_amount = self.cleaned_data['bid_amount']
        return bid_amount
    
class AutoBidForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['auto_bid_amount']  # Specify fields you want to include from Bid model
        widgets = {
            'auto_bid_amount': forms.NumberInput(attrs={'class': 'form-control', 'required': True}),
        }

    def clean_auto_bid_amount(self):
        auto_bid_amount = self.cleaned_data['auto_bid_amount']
        return auto_bid_amount

class ShippingAddressWebForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['address', 'city', 'state', 'postal_code', 'country', 'phone_no']

class ItemImageForm(forms.ModelForm):
    class Meta:
        model = ItemImage
        fields = ['item', 'image', 'root_image']

    def __init__(self, *args, **kwargs):
        super(ItemImageForm, self).__init__(*args, **kwargs)
        if 'item' in self.fields:
            self.fields['item'].widget.attrs['style'] = 'display: none;'
            self.fields['item'].label = ''
            self.fields['item'].widget.can_add_related = False

class ItemWebForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Remove 'user' from kwargs
        super(ItemWebForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['user'].initial = user  # Set initial value for 'user' field
            # Hide the user field
            self.fields['user'].widget.attrs['style'] = 'display: none;'
            # Hide the user field's label
            self.fields['user'].label = ''

    class Meta:
        model = Item
        fields = ['item_name', 'item_desc', 'item_year', 'item_country', 'item_material', 'item_weight', 'rate', 'item_status', 'featured_item', 'is_deleted', 'user']

class EditUserProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    bio = forms.CharField(widget=forms.Textarea, required=False)
    state = forms.CharField(max_length=100, required=False)
    country = CountryField(blank=True)  # Use blank=True to allow empty values
    phone_no = forms.CharField(max_length=20, required=False)
    website = forms.URLField(max_length=200, required=False)

    class Meta:
        model = Profile
        fields = ['username', 'first_name', 'last_name', 'email', 'bio', 'state', 'country', 'phone_no', 'website']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_username(self):
        username = self.cleaned_data['username']
        # Check for other users with the same username
        if User.objects.filter(username=username).count() > 0:
            if self.user.username != username:
                raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        # Check for other users with the same email
        if User.objects.filter(email=email).count() > 0:
            if self.user.email != email:
                raise ValidationError("This email is already taken.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self.user

        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profile.save()
        
        return profile

class SignUpForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).count() > 0:
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).count() > 0:
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create the Profile instance
            profile = Profile.objects.create()
            profile.user.add(user)
            profile.save()
        return user

class UserValidationMixin:
    def clean_user(self):
        users = self.cleaned_data['user']
        if len(users) > 1:
            raise forms.ValidationError("Only one user can be selected.")
        return users
    
class ItemValidationMixin:
    def clean_item(self):
        items = self.cleaned_data['item']
        if len(items) > 1:
            raise forms.ValidationError("Only one item can be selected.")
        return items
    
class OrderForm(UserValidationMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def clean_shippingaddress(self):
        shipping_addresses = self.cleaned_data['shippingaddress']
        if len(shipping_addresses) > 1:
            raise forms.ValidationError("Only one shipping address can be selected.")
        return shipping_addresses
    
    def clean_offer(self):
        selected_offers = self.cleaned_data['offer']
        user_based_offer_selected = False  # Flag to check if a 'UserBased' offer is selected
        other_offer_selected = False  # Flag to check if a non 'UserBased' offer is selected
        total_amount = self.instance.calculate_total_amount()

        # Check if total amount is zero
        if total_amount == 0 and selected_offers:
            raise forms.ValidationError("No offers can be selected when the total amount is zero.")
        
        if len(selected_offers) > 1:  # Check if more than one offer is selected
            # Loop through the selected offers to check the types of offers selected
            for offer in selected_offers:
                if offer.offer_type == 'UserBased':
                    if user_based_offer_selected:
                        # Raise ValidationError if more than one 'UserBased' offer is selected
                        raise forms.ValidationError("Only one 'UserBased' offer can be selected.")
                    user_based_offer_selected = True
                else:
                    if other_offer_selected:
                        # Raise ValidationError if more than one non 'UserBased' offer is selected
                        raise forms.ValidationError("Only one base offer (either 'TotalAmount') can be selected.")
                    other_offer_selected = True
        
        order = self.instance  # Get the order instance
        
        if order:
            calculated_total_amount = order.calculate_total_amount() or 0  # Get calculated total amount or assume as 0 if not found
            
            for offer in selected_offers:
                if offer.offer_type == 'TotalAmount':
                    min_order_amount_decimal = offer.min_order_amount.to_decimal()  # Convert Decimal128 to Decimal
                    if calculated_total_amount < min_order_amount_decimal:
                        raise forms.ValidationError(f"The offer '{offer}' is not eligible because the order's total amount is less than the minimum order amount required for this offer.")
                elif offer.offer_type == 'UserBased':
                    order_user = order.user.first()
                    if order_user:
                        # Get the most recent order where 'UserBased' offer was applied
                        recent_order_with_user_based_offer = Order.objects.filter(
                            user=order_user,
                            offer__offer_type='UserBased',  # Filter by 'UserBased' offer type
                            order_date__lt=order.order_date
                        ).order_by('-order_date').first()

                        if recent_order_with_user_based_offer:
                            # Count the number of orders since the most recent order with 'UserBased' offer
                            num_previous_orders = Order.objects.filter(
                                user=order_user,
                                order_date__gt=recent_order_with_user_based_offer.order_date,  # Change to greater than
                                order_date__lt=order.order_date
                            ).count()
                        else:
                            # Count all orders placed by the user if no previous order with 'UserBased' offer found
                            num_previous_orders = Order.objects.filter(
                                user=order_user,
                                order_date__lt=order.order_date
                            ).count()

                        if num_previous_orders < offer.num_orders:
                            raise forms.ValidationError(f"The offer '{offer}' is not eligible because the user has not placed enough orders to meet the eligibility criteria.")
                else:
                    raise forms.ValidationError(f"The offer '{offer}' is not a valid offer type.")

                # Check if other offer's discount percentage is greater than the max_discount_percentage of the selected UserBased offer
                if user_based_offer_selected and other_offer_selected:
                    user_based_offer = [o for o in selected_offers if o.offer_type == 'UserBased'][0]
                    if offer.discount_percentage.to_decimal() >= user_based_offer.max_discount_percentage.to_decimal():
                        raise forms.ValidationError(f"The discount percentage of '{offer}' cannot be greater than the maximum discount percentage allowed by the selected UserBased offer '{user_based_offer}'.")
        
        return selected_offers
    

class ItemForm(forms.ModelForm):
    end_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}), required=False)

    class Meta:
        model = Item
        fields = [
            'category', 'purpose', 'item_name', 'item_desc', 'item_year', 'item_country', 
            'item_material', 'item_weight', 'rate', 'item_status', 'user', 'featured_item', 
            'is_deleted', 'end_time', 'starting_bid', 'owner_profit_amount', 
            'incremental_value'
        ]
        widgets = {
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        purpose = cleaned_data.get('purpose')
        end_time = cleaned_data.get('end_time')

        # Define accepted fields for each purpose
        sale_fields = [
            'item_year', 'item_country', 'item_material', 'item_weight', 'rate', 
            'item_status'
        ]
        auction_fields = [
            'end_time', 'starting_bid', 'owner_profit_amount', 'incremental_value'
        ]
        common_fields = ['category', 'purpose', 'item_name', 'item_desc', 'user', 'featured_item', 'is_deleted']

        # Ensure fields are only present if they are in the accepted fields for the selected purpose
        if purpose == 'sale':
            for field in auction_fields:
                if cleaned_data.get(field):
                    self.add_error(field, f"{field.replace('_', ' ').capitalize()} should not be provided for sale purpose.")
        elif purpose == 'auction':
            for field in sale_fields:
                if cleaned_data.get(field):
                    self.add_error(field, f"{field.replace('_', ' ').capitalize()} should not be provided for auction purpose.")
        
        # Validate end_time is after the current datetime
        #if purpose == 'auction' and end_time:
        #    if end_time <= timezone.now():
        #        self.add_error('end_time', 'End time must be in the future for auction purpose.')

        return cleaned_data

    #def clean_end_time(self):
    #    end_time = self.cleaned_data.get('end_time')
    #    if end_time:
    #        if end_time.weekday() != 6:  # 6 corresponds to Sunday
    #            raise ValidationError('End time must be on a Sunday.')
    #    return end_time

    def __init__(self, *args, **kwargs):
        super(ItemForm, self).__init__(*args, **kwargs)
        if 'category' in self.fields:
            self.fields['category'].widget.attrs['style'] = 'display: none;'
            self.fields['category'].label = ''
            self.fields['category'].widget.can_add_related = False

        # Set custom labels for fields
        self.fields['item_year'].label = 'Item Year (Sale Purpose)'
        self.fields['item_country'].label = 'Item Country (Sale Purpose)'
        self.fields['item_material'].label = 'Item Material (Sale Purpose)'
        self.fields['item_weight'].label = 'Item Weight (Sale Purpose)'
        self.fields['rate'].label = 'Rate (Sale Purpose)'
        self.fields['item_status'].label = 'Item Status (Sale Purpose)'
        self.fields['end_time'].label = 'End Time (Auction Purpose)'
        self.fields['starting_bid'].label = 'Starting Bid (Auction Purpose)'
        self.fields['owner_profit_amount'].label = 'Owner Profit Amount (Auction Purpose)'
        self.fields['incremental_value'].label = 'Incremental Value (Auction Purpose)'
    
class ProfileForm(UserValidationMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = '__all__'
    
class CartItemForm(UserValidationMixin, ItemValidationMixin, forms.ModelForm):
    class Meta:
        model = CartItem
        fields = '__all__'
    
class ShippingAddressForm(UserValidationMixin, forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = '__all__'
    
class OrderItemForm(ItemValidationMixin, forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['order', 'item', 'quantity']

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        if 'order' in self.fields:
            self.fields['order'].widget.attrs['style'] = 'display: none;'
            self.fields['order'].label = ''
            self.fields['order'].widget.can_add_related = False

    def clean_order(self):
        orders = self.cleaned_data['order']
        if len(orders) > 1:
            raise forms.ValidationError("Only one order can be selected.")
        return orders
    
class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add onchange event to offer_type field
        self.fields['offer_type'].widget.attrs['onchange'] = 'toggleFields()'

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        discount_percentage = cleaned_data.get('discount_percentage')
        max_discount_percentage = cleaned_data.get('max_discount_percentage')

        if offer_type == 'TotalAmount':
            if max_discount_percentage or cleaned_data.get('num_orders'):
                self.add_error('max_discount_percentage', 'This field is not applicable for TotalAmount offers.')
                self.add_error('num_orders', 'This field is not applicable for TotalAmount offers.')
        elif offer_type == 'UserBased':
            if cleaned_data.get('min_order_amount'):
                self.add_error('min_order_amount', 'This field is not applicable for UserBased offers.')

        if discount_percentage is not None and max_discount_percentage is not None:
            if discount_percentage > max_discount_percentage:
                self.add_error('discount_percentage', 'Discount percentage cannot be greater than the maximum discount percentage.')

        return cleaned_data