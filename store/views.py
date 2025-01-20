from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.urls import reverse
from .models import *
from django.apps import apps
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponseRedirect
from .forms import *
from django.views.decorators.http import require_POST
from decimal import Decimal, getcontext
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
from django_countries import countries as django_countries
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from openpyxl import Workbook
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.admin.sites import site
import razorpay
from django.views.decorators.csrf import csrf_exempt
from pytz import timezone as tz
from django.http import JsonResponse
import json
from django.urls import NoReverseMatch
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist

FORMS_FOR_TABLES = { 'Order': OrderForm, 'Bid' : BidAdminForm, 'Item' : ItemForm, 'ItemImage' : ItemImageForm, 'Profile' : ProfileForm, 'CartItem' : CartItemForm, 'ShippingAddress' : ShippingAddressForm, 'OrderItem' : OrderItemForm, 'Offer' : OfferForm, }

@login_required
def submit_request(request):
    if request.method == 'POST':
        request_item_id = request.POST.get('request_item_id')
        feature_fee = 'feature_fee' in request.POST
        banner_fee = 'banner_fee' in request.POST

        try:
            # Fetch the FeatureBanner object
            feature_banner = FeatureBanner.objects.get(id=request_item_id)
            
            # Update the asked_for field based on the POST data
            if feature_fee:
                feature_banner.asked_for = 'featured'
            if banner_fee:
                feature_banner.asked_for = 'banner'
            if feature_fee and banner_fee:
                feature_banner.asked_for = 'both'

            # Save the updated FeatureBanner object
            feature_banner.save()

            # Redirect to 'my_requests'
            return redirect('my_requests')

        except FeatureBanner.DoesNotExist:
            messages.error(request, 'The requested item does not exist.')
            return redirect('error')
        
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return redirect('error')

    # If the request method is not POST, return an error response
    messages.error(request, 'Invalid request method.')
    return redirect('error')

@login_required
def my_requests(request):
    try:
        requests = FeatureBanner.objects.filter(user=request.user)
        orders = Order.objects.filter(user=request.user, order_for='FeatureBanner')

        requests_with_images = []
        for request_item in requests:
            root_image = ItemImage.objects.filter(item=request_item.item.first(), root_image='yes').first()
            requests_with_images.append((request_item, root_image))

        return render(request, 'my_requests.html', {'requests_with_images': requests_with_images, 'orders': orders})

    except FeatureBanner.DoesNotExist:
        messages.error(request, 'Feature Banner request not found.')
        return redirect('error')

    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('error')

    except ItemImage.DoesNotExist:
        messages.error(request, 'Root image not found.')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def my_items(request):
    try:
        items = Item.objects.filter(is_deleted='no', user=request.user).order_by('-created_at')

        items_with_images = []
        for item in items:
            try:
                root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            except ItemImage.DoesNotExist:
                root_image = None
                messages.warning(request, f'Root image not found for item {item.id}.')
                
            items_with_images.append((item, root_image))

        return render(request, 'my_items.html', {'items_with_images': items_with_images})

    except Item.DoesNotExist:
        messages.error(request, 'No items found.')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@csrf_exempt
@login_required
def send_request(request, item_id):
    if request.method == 'GET':
        if item_id:
            try:
                # Fetch the item or raise a 404 error if not found
                item = get_object_or_404(Item, pk=item_id)
                categories = item.category.all()  # Fetch all categories associated with the item
                
                # Check if categories are available before accessing
                if not categories:
                    messages.error(request, 'No categories found for this item.')
                    return redirect('error')

                category_id = categories[0].pk 

                # Check item status and handle accordingly
                if item.featured_item == 'yes' and item.banner_item == 'yes':
                    messages.error(request, 'This item is already a feature and banner item.')
                    return redirect('manage_category_items', category_id=category_id)

                # Create and save FeatureBanner
                feature_banner = FeatureBanner()
                feature_banner.item.add(item)
                feature_banner.user.add(request.user)  # Add the current user
                feature_banner.save()
                
                return redirect('manage_category_items', category_id=category_id)
            
            except Item.DoesNotExist:
                messages.error(request, 'Item does not exist.')
                return redirect('error')

            except FeatureBanner.DoesNotExist:
                messages.error(request, 'FeatureBanner creation failed.')
                return redirect('error')

            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
                return redirect('error')
        else:
            messages.error(request, 'Invalid item ID.')
            return redirect('home')

    else:
        messages.error(request, 'Invalid request method.')
        return redirect('error')

@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.payment_initiated_at = timezone.now()
        order.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)

@login_required
def pay_order(request, order_id):
    try:
        # Fetch the order object
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if request.method == 'POST':
            # Extract parameters from POST request
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            # Initialize Razorpay client
            client = razorpay.Client(auth=("rzp_test_qdTCzfVwGhvWtW", "9gVT5GX19E1QijlSdN9SopuQ"))

            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(params_dict)

            # Update the order
            order.status = 'Paid'
            order.razorpay_order_id = razorpay_order_id
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.payment_completed_at = timezone.now()
            order.save()

            if order.order_for == 'FeatureBanner':
                # Fetch associated FeatureBanner record
                feature_banner = FeatureBanner.objects.filter(order=order.id).first()
                if feature_banner:
                    # Update item based on asked_for field
                    item = feature_banner.item.first()  # Assuming ArrayReferenceField gives a queryset
                    if item:
                        if feature_banner.asked_for == 'featured':
                            item.featured_item = 'yes'
                        elif feature_banner.asked_for == 'banner':
                            item.banner_item = 'yes'
                        elif feature_banner.asked_for == 'both':
                            item.featured_item = 'yes'
                            item.banner_item = 'yes'
                        item.save()

            # Calculate the amount paid
            amount_paid = order.calculate_discounted_total_amount()
            messages.success(request, f'Paid Successfully with amount {amount_paid}!!')
            return redirect(reverse('order_detail', args=[order.id]))

    except razorpay.errors.SignatureVerificationError:
        logger.error("Razorpay signature verification failed.")
        return redirect('error')

    except Order.DoesNotExist:
        logger.error("Order does not exist.")
        return redirect('error')

    except FeatureBanner.DoesNotExist:
        logger.error("FeatureBanner record does not exist.")
        return redirect('error')

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return redirect('error')

    return redirect('home')

@login_required
def set_primary_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)

    try:
        # Set all other addresses to not primary
        ShippingAddress.objects.filter(user=request.user).update(primary='no')

        # Set the selected address as primary
        address.primary = 'yes'
        address.save()
        messages.success(request, "Primary address set successfully.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, "An error occurred while setting the primary address.")

    return redirect('view_profile')

@login_required
def won_auctions(request):
    try:
        now_utc = timezone.now()
        now_indian_time = now_utc.astimezone(timezone.get_current_timezone())
        
        # Fetch orders
        orders = Order.objects.filter(user=request.user, order_for='Auction').order_by('-order_date')
        
        # Fetch won items
        won_items = Item.objects.filter(
            purpose='auction',
            end_time__lte=now_indian_time,
            highest_bidder__in=[request.user],
            is_deleted='no'
        )

        items_with_images = []
        for item in won_items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            items_with_images.append((item, root_image))

        return render(request, 'won_auctions.html', {'items_with_images': items_with_images, 'orders': orders})

    except ObjectDoesNotExist as e:
        # Log the specific error for debugging purposes
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        # Log the database error for debugging purposes
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except Exception as e:
        # Log any other unexpected errors
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def participated_auctions(request):
    try:
        now_utc = timezone.now()
        now_indian_time = now_utc.astimezone(timezone.get_current_timezone())

        # Filter items that are auctions, have ended, and where the logged-in user has placed bids
        participated_items = Item.objects.filter(
            purpose='auction',
            end_time__lte=now_indian_time,
            is_deleted='no',
            bid__bidder=request.user.id,  # Check if the user has placed bids
        ).exclude(
            highest_bidder=request.user.id  # Exclude items where the logged-in user is the highest bidder
        ).distinct()

        items_with_images = []
        for item in participated_items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            # Get the user's last bid for this item
            last_bid = Bid.objects.filter(item=item, bidder=request.user).order_by('-timestamp').first()
            if last_bid:
                defeated_difference = Decimal(str(item.highest_bid)) - Decimal(str(last_bid.bid_amount))
            else:
                defeated_difference = None
            items_with_images.append((item, root_image, defeated_difference))

        return render(request, 'participated_auctions.html', {'items_with_images': items_with_images})

    except ObjectDoesNotExist as e:
        # Log the specific error for debugging purposes
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        # Log the database error for debugging purposes
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except Exception as e:
        # Log any other unexpected errors
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def category_items(request, category_id):
    try:
        # Fetch the category
        category = get_object_or_404(Category, pk=category_id)
        
        # Fetch items belonging to the category
        items = Item.objects.filter(category=category, is_deleted='no')

        # Prepare items with root images
        items_with_images = []
        for item in items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            items_with_images.append((item, root_image))

        return render(request, 'category_items.html', {'category': category, 'items_with_images': items_with_images})

    except Category.DoesNotExist as e:
        # Handle case where the category does not exist
        messages.error(request, f'Category not found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        # Handle database errors
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except Exception as e:
        # Handle any other unexpected errors
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def export_orders_excel(request):
    try:
        # Get order IDs from the form
        order_ids_str = request.POST.get('order_ids', '')
        if not order_ids_str:
            raise ValueError("No order IDs provided.")

        order_ids = order_ids_str.split(',')
        if not order_ids:
            raise ValueError("No valid order IDs provided.")

        # Fetch orders corresponding to the IDs
        orders = list(Order.objects.filter(id__in=order_ids))

        # Create a new Excel workbook
        wb = Workbook()
        ws = wb.active

        # Add headers to the worksheet
        headers = ['Invoice No', 'Order Date', 'Shipping Address', 'Offers', 'Total Amount', 'Status']
        ws.append(headers)

        # Add order data to the worksheet
        for order in orders:
            row = [
                order.invoice_no,
                order.order_date.strftime("%Y-%m-%d"),  # Format the date as needed
                ', '.join([f"{shipping.address},{shipping.city},{shipping.state},{shipping.country}-{shipping.postal_code}" for shipping in order.shippingaddress.all()]) if order.shippingaddress.all() else 'N/A',
                ', '.join([f"{offer.name} ({offer.discount_percentage}%)" for offer in order.offer.all()]) if order.offer.all() else 'N/A',
                order.calculate_discounted_total_amount(),
                order.status
            ]
            ws.append(row)

        # Generate the filename
        username = request.user.username
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"orders_{username}_{current_datetime}.xlsx"

        # Create HTTP response with Excel content
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Save the workbook to the response
        wb.save(response)

        return response

    except ValueError as e:
        # Handle value errors (e.g., missing or invalid order IDs)
        return HttpResponse(f"Error: {str(e)}", status=400)

    except ObjectDoesNotExist as e:
        # Handle case where orders are not found
        return HttpResponse(f"Error: Orders not found: {str(e)}", status=404)

    except DatabaseError as e:
        # Handle database errors
        return HttpResponse(f"Database error occurred: {str(e)}", status=500)

    except Exception as e:
        # Handle any other unexpected errors
        return HttpResponse(f"An unexpected error occurred: {str(e)}", status=500)

@login_required
def export_orders_pdf(request):
    try:
        # Get order IDs from the form
        order_ids_str = request.POST.get('order_ids', '')
        if not order_ids_str:
            raise ValueError("No order IDs provided.")

        order_ids = order_ids_str.split(',')
        if not order_ids:
            raise ValueError("No valid order IDs provided.")

        # Fetch orders corresponding to the IDs
        orders = Order.objects.filter(id__in=order_ids)

        # Fetch profile and company information
        profile = get_object_or_404(Profile, user=request.user)
        company = Company.objects.first()  # Assuming there's only one company in the database

        # Generate the filename
        username = request.user.username
        current_datetime = timezone.now().strftime("%Y%m%d%H%M%S")
        filename = f"orders_{username}_{current_datetime}.pdf"

        # Render HTML to string
        html_string = render_to_string('orders_pdf.html', {'orders': orders, 'profile': profile, 'company': company})

        # Generate PDF from HTML string
        pdf_file = HTML(string=html_string).write_pdf()

        # Create HTTP response with PDF content
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except ValueError as e:
        # Handle value errors (e.g., missing or invalid order IDs)
        return HttpResponse(f"Error: {str(e)}", status=400)

    except ObjectDoesNotExist as e:
        # Handle case where orders, profile, or company are not found
        return HttpResponse(f"Error: {str(e)}", status=404)

    except DatabaseError as e:
        # Handle database errors
        return HttpResponse(f"Database error occurred: {str(e)}", status=500)

    except Exception as e:
        # Handle any other unexpected errors
        return HttpResponse(f"An unexpected error occurred: {str(e)}", status=500)

@login_required
def order_history_view(request):
    try:
        orders = Order.objects.filter(user=request.user).order_by('-order_date')

        # Calculate discounted total amount for each order
        for order in orders:
            order.discounted_total_amount = order.calculate_discounted_total_amount()

        if request.method == 'POST':
            from_date = request.POST.get('from_date')
            to_date = request.POST.get('to_date')
            invoice_no = request.POST.get('invoice_no')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            total_amount_min = request.POST.get('total_amount_min')
            total_amount_max = request.POST.get('total_amount_max')
            status = request.POST.get('status')

            if from_date and to_date:
                from_date = parse_date(from_date)
                to_date = parse_date(to_date) + timedelta(days=1) - timedelta(seconds=1)
                orders = orders.filter(order_date__gte=from_date, order_date__lte=to_date)

            if invoice_no:
                orders = orders.filter(invoice_no__icontains=invoice_no)

            if city:
                orders = orders.filter(shippingaddress__city__icontains=city)

            if state:
                orders = orders.filter(shippingaddress__state__icontains=state)

            if country:
                orders = orders.filter(shippingaddress__country__icontains=country)

            if total_amount_min:
                orders = [order for order in orders if order.discounted_total_amount >= Decimal(total_amount_min)]

            if total_amount_max:
                orders = [order for order in orders if order.discounted_total_amount <= Decimal(total_amount_max)]

            if status:
                orders = [order for order in orders if order.status == status]

        return render(request, 'order_history.html', {'orders': orders, 'countries': django_countries})

    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except ValueError as e:
        messages.error(request, f'Invalid input: {str(e)}')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

def superuser_required(user):
    return user.is_superuser

@login_required
@user_passes_test(superuser_required)

@login_required
def order_history_users(request):
    try:
        orders = Order.objects.all().order_by('-order_date')

        # Calculate discounted total amount for each order
        for order in orders:
            order.discounted_total_amount = order.calculate_discounted_total_amount()

        if request.method == 'POST':
            from_date = request.POST.get('from_date')
            to_date = request.POST.get('to_date')
            invoice_no = request.POST.get('invoice_no')
            user = request.POST.get('user')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            total_amount_min = request.POST.get('total_amount_min')
            total_amount_max = request.POST.get('total_amount_max')
            status = request.POST.get('status')

            if from_date and to_date:
                from_date = parse_date(from_date)
                to_date = parse_date(to_date) + timedelta(days=1) - timedelta(seconds=1)
                orders = orders.filter(order_date__gte=from_date, order_date__lte=to_date)

            if invoice_no:
                orders = orders.filter(invoice_no=invoice_no)

            if user:
                orders = orders.filter(user__username=user)

            if city:
                orders = orders.filter(shippingaddress__city__icontains=city)

            if state:
                orders = orders.filter(shippingaddress__state__icontains=state)

            if country:
                orders = orders.filter(shippingaddress__country__icontains=country)

            if total_amount_min:
                orders = [order for order in orders if order.discounted_total_amount >= Decimal(total_amount_min)]

            if total_amount_max:
                orders = [order for order in orders if order.discounted_total_amount <= Decimal(total_amount_max)]

            if status:
                orders = [order for order in orders if order.status == status]

        return render(request, 'admin/order_history_users.html', {'orders': orders, 'countries': django_countries})

    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except ValueError as e:
        messages.error(request, f'Invalid input: {str(e)}')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')
   
@login_required
def select_shipping(request):
    try:
        user = request.user
        shipping_addresses = ShippingAddress.objects.filter(user=user)

        form = ShippingAddressWebForm()

        return render(request, 'select_shipping.html', {
            'shipping_addresses': shipping_addresses,
            'form': form,
        })
        
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@csrf_exempt
@login_required
def order_detail(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        order_items = OrderItem.objects.filter(order=order)
        company = Company.objects.first()
        shipping_address = order.shippingaddress.first() if order.shippingaddress.count()>0 else None

        feature_banner_details = None
        if order.order_for == 'FeatureBanner':
            feature_banner = FeatureBanner.objects.filter(order=order.id).first()
            if feature_banner:
                feature_banner_details = {
                    'asked_for': feature_banner.asked_for,
                }

        getcontext().prec = 28
        final_price_in_paise = order.calculate_discounted_total_amount() * Decimal('100')
        amount = str(final_price_in_paise.quantize(Decimal('1')))

        client = razorpay.Client(auth=("rzp_test_qdTCzfVwGhvWtW", "9gVT5GX19E1QijlSdN9SopuQ"))
        payment = client.order.create({'amount': amount, 'currency': 'INR', 'payment_capture': '1'})
        orderid = payment['id']

        context = {
            'order': order,
            'order_items': order_items,
            'company': company,
            'shipping_address': shipping_address,
            'amount': amount,
            'orderid': orderid,
            'feature_banner_details': feature_banner_details,
        }
        return render(request, 'order_details.html', context)

    except razorpay.errors.RazorpayError as e:
        messages.error(request, f'Razorpay API error: {str(e)}')
        return redirect('error')

    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')

    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def my_orders(request):
    try:
        orders = Order.objects.filter(user=request.user, status='Paid').order_by('-order_date')

        # Annotate each order with its discounted total amount
        orders_with_amounts = []
        for order in orders:
            order.discounted_total_amount = order.calculate_discounted_total_amount()
            orders_with_amounts.append(order)

        return render(request, 'my_orders.html', {'orders': orders_with_amounts})

    except Order.DoesNotExist:
        messages.error(request, 'No paid orders found.')
        return redirect('error')

    except AttributeError:
        messages.error(request, 'An error occurred while processing your orders.')
        return redirect('error')

    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')


@login_required
def thankyou(request, order_id):
    try:
        if request.session.get('order_placed') or request.GET.get('order_placed'):
            order = get_object_or_404(Order, id=order_id)
            context = {
                'order': order,
            }
            request.session.pop('order_placed', None)
            return render(request, 'thankyou.html', context)
        else:
            return redirect(reverse('home'))
    except ObjectDoesNotExist as e:
        # Handle case where the order does not exist
        return redirect('error')
    except DatabaseError as e:
        # Handle database errors
        return redirect('error')
    except Exception as e:
        # Handle any other unexpected errors
        return redirect('error')
    
import pytz
import logging 
# Configure logger
logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def place_order(request):
    if request.method == 'POST':
        try:
            # Extract parameters from POST request
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            # Initialize Razorpay client
            client = razorpay.Client(auth=("rzp_test_qdTCzfVwGhvWtW", "9gVT5GX19E1QijlSdN9SopuQ"))

            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(params_dict)

            # Payment signature verified, proceed with order creation
            selected_address_id = request.POST.get('selected_address_id')
            eligible_offers_ids = request.POST.getlist('eligible_offers')
            payment_initiated_at_str = request.POST.get('payment_initiated_at')

            # Convert string to datetime object
            payment_initiated_at = datetime.fromisoformat(payment_initiated_at_str.replace('Z', '+00:00'))
            eligible_offers = Offer.objects.filter(id__in=eligible_offers_ids)
                
            selected_address = get_object_or_404(ShippingAddress, pk=selected_address_id)

            # Create order with the address and eligible offers
            order = Order.objects.create(
                status='Paid',
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                payment_initiated_at=payment_initiated_at,
                payment_completed_at=timezone.now()
            )
            order.user.add(request.user)
            order.shippingaddress.add(selected_address)

            for offer in eligible_offers:
                order.offer.add(offer)

            # Fetch all cart items for the current user
            cart_items = CartItem.objects.filter(user=request.user)

            # Create order items based on cart items
            for cart_item in cart_items:
                order_item = OrderItem()
                order_item.order.add(order)
                order_item.item.add(*cart_item.item.all())
                order_item.quantity = cart_item.quantity
                order_item.save()
            cart_items.delete()
            request.session['order_placed'] = True

            # Redirect to the thank you page
            return HttpResponseRedirect(reverse('thankyou', kwargs={'order_id': order.id}))

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment signature verification failed: {str(e)}")
            messages.error(request, f"Payment signature verification failed: {str(e)}")
            return redirect('error')

        except ObjectDoesNotExist as e:
            logger.error(f"Object does not exist: {str(e)}")
            messages.error(request, f"Requested object does not exist: {str(e)}")
            return redirect('error')

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages.error(request, f"Validation error occurred: {str(e)}")
            return redirect('error')

        except DatabaseError as e:
            logger.error(f"Database error occurred: {str(e)}")
            messages.error(request, f"Database error occurred: {str(e)}")
            return redirect('error')

        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

    # If the request method is not POST or if an error occurs, redirect back to the cart page
    return redirect('cart')

@login_required
def checkout_view(request):
    user = request.user
    try:
        if request.method == 'POST':
            selected_address_id = request.POST.get('selected_address_id')
            if selected_address_id :
                address_id = request.POST.get('selected_address_id')
            else :
                form = ShippingAddressWebForm(request.POST)
                if form.is_valid():
                    shipping = form.save(commit=False)
                    shipping.user.add(request.user)  # Link the address to the current user
                    shipping.save()
                    address_id = shipping.id
            
            shipping_address = get_object_or_404(ShippingAddress, id=address_id, user=user)
            
            # Retrieve shipping charge based on address state and country
            shipping_charge = None
            try:
                shipping_charge = ShippingCharge.objects.get(state__iexact=shipping_address.state, country=shipping_address.country)
            except ShippingCharge.DoesNotExist:
                # Apply default shipping charge from the Company model
                company = Company.objects.first()  # Assuming there is only one company record
                default_shipping_charge = company.shipping_charge
                # Convert Decimal128 to Decimal
                default_shipping_charge = default_shipping_charge.to_decimal()

            cart_items = CartItem.objects.filter(user=user)
            total_price = sum(Decimal(item.price) for item in cart_items)  # Convert prices to Decimal

            cart_items_with_images = [
                (item, ItemImage.objects.filter(item=item.item.first(), root_image='yes').first())
                for item in cart_items
            ]

            # Retrieve eligible offers
            eligible_offers = {}
            current_time = timezone.now()  # Get the current date and time

            for offer in Offer.objects.all():
                if (offer.offer_type == 'TotalAmount' and total_price >= Decimal(str(offer.min_order_amount))) or \
                (offer.offer_type == 'UserBased'):
                    if offer.offer_type == 'UserBased':
                        recent_order_with_user_based_offer = Order.objects.filter(
                            user=user,
                            offer__offer_type='UserBased',  # Filter by 'UserBased' offer type
                            order_date__lt=current_time
                        ).order_by('-order_date').first()

                        if recent_order_with_user_based_offer:
                            num_previous_orders = Order.objects.filter(
                                user=user,
                                order_date__gt=recent_order_with_user_based_offer.order_date,
                                order_date__lt=current_time
                            ).count()
                        else:
                            num_previous_orders = Order.objects.filter(
                                user=user,
                                order_date__lt=current_time
                            ).count()

                        if num_previous_orders >= offer.num_orders:
                            offer_discount_percentage = Decimal(offer.discount_percentage.to_decimal())
                            if (offer.offer_type not in eligible_offers) or (offer_discount_percentage > Decimal(eligible_offers[offer.offer_type].discount_percentage.to_decimal())):
                                # Check if the 'TotalAmount' offer's discount percentage is less than or equal to the 'UserBased' offer's max_discount_percentage
                                if 'TotalAmount' not in eligible_offers or eligible_offers['TotalAmount'].discount_percentage.to_decimal() < offer.max_discount_percentage.to_decimal():
                                    eligible_offers[offer.offer_type] = offer
                    else:
                        offer_discount_percentage = Decimal(offer.discount_percentage.to_decimal())
                        if (offer.offer_type not in eligible_offers) or (offer_discount_percentage > Decimal(eligible_offers[offer.offer_type].discount_percentage.to_decimal())):
                            eligible_offers[offer.offer_type] = offer

            # Apply eligible offers to total price
            final_price = total_price
            revised_discount_percentage = Decimal('0')  # Initialize revised discount percentage for UserBased offer
            for offer in eligible_offers.values():
                discount_percentage = Decimal(str(offer.discount_percentage))
                if offer.offer_type == 'TotalAmount':
                    discount_amount = (final_price * discount_percentage) / Decimal('100')
                    final_price -= discount_amount
                elif offer.offer_type == 'UserBased':
                    if 'TotalAmount' in eligible_offers:  # If both offer types are applied
                        total_discount_percentage = discount_percentage + Decimal(eligible_offers['TotalAmount'].discount_percentage.to_decimal())
                        max_discount_percentage = Decimal(eligible_offers['UserBased'].max_discount_percentage.to_decimal())
                        if total_discount_percentage > max_discount_percentage:
                            revised_discount_percentage = max_discount_percentage - Decimal(eligible_offers['TotalAmount'].discount_percentage.to_decimal())
                    else:
                        discount_amount = (final_price * discount_percentage) / Decimal('100')
                        final_price -= discount_amount

            # Adjust final price if revised discount percentage is calculated
            if revised_discount_percentage:
                user_based_offer_discount = (final_price * revised_discount_percentage) / Decimal('100')
                final_price -= user_based_offer_discount

            # Apply shipping charge to the total price
            if shipping_charge:
                shipping_charge_decimal = shipping_charge.charge.to_decimal()
                final_price += shipping_charge_decimal
            else:
                final_price += default_shipping_charge

            getcontext().prec = 28  # Example precision, adjust as needed
            final_price_in_paise = final_price * Decimal('100')
            amount = str(final_price_in_paise.quantize(Decimal('1')))
            client = razorpay.Client(auth=("rzp_test_qdTCzfVwGhvWtW", "9gVT5GX19E1QijlSdN9SopuQ"))
            payment = client.order.create({'amount' : amount, 'currency' : 'INR', 'payment_capture' : '1'})
            orderid = payment['id']

            return render(request, 'checkout.html', {
                'cart_items': cart_items,
                'cart_items_with_images': cart_items_with_images,
                'total_price': total_price.quantize(Decimal('0.01')),  # Pass original total price to the template
                'final_price': final_price.quantize(Decimal('0.01')),  # Pass final price to the template
                'shipping_address': shipping_address,
                'eligible_offers': list(eligible_offers.values()),  # Pass eligible offers to the template
                'revised_discount_percentage': revised_discount_percentage,
                'applied_shipping_charge': shipping_charge_decimal if shipping_charge else default_shipping_charge,
                'orderid': orderid,
                'amount' : amount,
            })
        else:
            return redirect('cart')
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')
    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

 
@login_required
def add_to_cart(request, item_id):
    try:
        if request.method == 'POST':
            # Get the selected item
            item = get_object_or_404(Item, pk=item_id)
            # Get the current user
            user = request.user
            
            # Check if the item is already in the user's cart
            existing_cart_item = CartItem.objects.filter(item=item, user=user).first()
            if existing_cart_item:
                # If the item is already in the cart, increase its quantity by 1
                existing_cart_item.quantity += 1
                existing_cart_item.save()
                messages.success(request, f'Another {item.item_name} has been added to your cart!')
            else:
                # If the item is not in the cart, create a new CartItem object
                cart_item = CartItem(quantity=1)
                cart_item.item.add(item)  # Add the item to the cart item
                cart_item.user.add(user)  # Add the user to the cart item
                cart_item.save()  # Save the cart item
                messages.success(request, 'Your item has been added to the cart!')
            
            # Redirect to the cart page
            return redirect('cart')
        else:
            return redirect('cart')
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested item or user does not exist: {str(e)}')
        return redirect('error')
    except DatabaseError as e:
        messages.error(request, f'Database error occurred: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')
    
@login_required
@require_POST
def update_cart_item(request):
    item_id = request.POST.get('item_id')
    new_quantity = request.POST.get('quantity')

    try:
        cart_item = CartItem.objects.get(id=item_id, user=request.user)
        new_quantity = int(new_quantity)
        
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
            response = {
                'status': 'success',
                'item_id': item_id,
                'new_price': cart_item.item.first().rate * new_quantity,
                'total_price': sum(item.item.first().rate * item.quantity for item in CartItem.objects.filter(user=request.user))
            }
        else:
            cart_item.delete()
            response = {
                'status': 'deleted',
                'item_id': item_id,
                'total_price': sum(item.item.first().rate * item.quantity for item in CartItem.objects.filter(user=request.user))
            }
    except (CartItem.DoesNotExist, ValueError):
        response = {'status': 'error'}

    return JsonResponse(response)

@login_required
@require_POST
def remove_item(request, item_id):
    try:
        item = CartItem.objects.get(id=item_id, user=request.user)
        item.delete()
        response = {'status': 'success'}
    except CartItem.DoesNotExist:
        response = {'status': 'error', 'message': 'Item not found.'}
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}

    return JsonResponse(response)

@login_required
@require_POST
def clear_cart(request):
    try:
        CartItem.objects.filter(user=request.user).delete()
        response = {'status': 'success'}
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}

    return JsonResponse(response)

@login_required
def create_item(request):
    if request.method == 'POST':
        form = ItemWebForm(request.POST, request.FILES, user=request.user)  # Pass current user to form
        if form.is_valid():
            form.save()
            messages.success(request, 'Item created successfully!')
            return redirect(reverse('item-details', kwargs={'item_id': form.instance.pk}))
    else:
        form = ItemWebForm(user=request.user)  # Pass current user to form
    return render(request, 'create_item.html', {'form': form})

@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == 'POST':
        form = ItemWebForm(request.POST, request.FILES, instance=item, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect(reverse('item-details', kwargs={'item_id': item.id}))
    else:
        form = ItemWebForm(instance=item, user=request.user)
    return render(request, 'edit_item.html', {'form': form, 'item': item})

@login_required
def dashboard(request):
    try:
        app_config = apps.get_app_config('store')
        tables = []

        for model in app_config.get_models():
            model_admin = site._registry.get(model)
            if model_admin and model_admin.has_module_permission(request):
                tables.append(model.__name__)
        
        return render(request, 'admin/dashboard.html', {'tables': tables})
    
    except LookupError as e:
        # Handle case where the app configuration might not be found
        messages.error(request, f'App configuration error: {str(e)}')
        return redirect('error')
    
    except AttributeError as e:
        # Handle case where the model or admin might not be found
        messages.error(request, f'Attribute error: {str(e)}')
        return redirect('error')
    
    except Exception as e:
        # Handle any other unexpected errors
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def manage_item_images(request, item_id):
    try:
        item = get_object_or_404(Item, pk=item_id)
        item_images = ItemImage.objects.filter(item=item)
        category_id = request.GET.get('category_id')
        category = get_object_or_404(Category, pk=category_id)
        
        return render(request, 'admin/manage_item_images.html', {
            'item': item,
            'item_images': item_images,
            'category': category
        })
    
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def manage_order_items(request, order_id):
    try:
        order = get_object_or_404(Order, pk=order_id)
        order_items = OrderItem.objects.filter(order=order)
        
        return render(request, 'admin/manage_order_items.html', {
            'order': order,
            'order_items': order_items
        })
    
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def manage_bids(request, item_id):
    try:
        item = get_object_or_404(Item, pk=item_id)
        bids = Bid.objects.filter(item=item)
        category_id = request.GET.get('category_id')
        category = get_object_or_404(Category, pk=category_id)
        
        return render(request, 'admin/manage_bids.html', {
            'item': item,
            'bids': bids,
            'category': category
        })
    
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

@login_required
def manage_category_items(request, category_id):
    try:
        category = get_object_or_404(Category, pk=category_id)
        category_items = Item.objects.filter(category=category)
        
        # Add the logic for items with images here
        items_with_images = [
            (item, ItemImage.objects.filter(item=item, root_image='yes').first())
            for item in category_items
        ]
        
        return render(request, 'admin/manage_category_items.html', {
            'category': category,
            'category_items': category_items,
            'items_with_images': items_with_images
        })
    
    except ObjectDoesNotExist as e:
        messages.error(request, f'Requested data could not be found: {str(e)}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('error')

def get_model_class(table_name):
    try:
        return apps.get_model(app_label='store', model_name=table_name)
    except LookupError:
        raise Http404("Table '{}' does not exist".format(table_name))

class DynamicListView(ListView):
    template_name = 'admin/dynamic_list.html'
    context_object_name = 'objects'

    def get_queryset(self):
        table_name = self.kwargs['table_name']
        model_class = get_model_class(table_name)
        return model_class.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_name = self.kwargs['table_name']
        model_class = get_model_class(table_name)
        
        fields = model_class._meta.fields
        context['fields'] = fields
        context['table_name'] = table_name.lower()  # Convert table_name to lowercase
        context['model_name'] = table_name.lower()  # Convert model name to lowercase
        context['fields_length'] = len(fields)
        
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404 as e:
            messages.error(request, str(e))  # Set the error message
            return redirect('error') 

class DynamicCreateView(CreateView):
    template_name = 'admin/dynamic_form.html'
    fields = '__all__'

    def get_success_url(self):
        table_name = self.kwargs.get('table_name', '')
        if table_name:
            if table_name.lower() == 'itemimage':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_item_images', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'orderitem':
                order_id = self.request.GET.get('order_id')
                return reverse_lazy('manage_order_items', kwargs={'order_id': order_id})
            elif table_name.lower() == 'bid':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_bids', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'item':
                category_id = self.request.GET.get('category_id')
                return reverse_lazy('manage_category_items', kwargs={'category_id': category_id})
            else:
                return reverse_lazy('dynamic_list', kwargs={'table_name': table_name})
        else:
            pass

    def get_form(self, form_class=None):
        table_name = self.kwargs['table_name']
        model_class = get_model_class(table_name)
        form_class = FORMS_FOR_TABLES.get(model_class.__name__, form_class)
        if form_class:
            return form_class(**self.get_form_kwargs())
        else:
            self.model = model_class
            return super().get_form(form_class)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.kwargs['table_name'].lower() == 'item':
            if self.request.POST.get('confirm_action') == 'send_request':
                item_id = form.instance.pk  # Use form.instance.pk to get the item_id after form submission
                return redirect('send_request', item_id=item_id)
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_name = self.kwargs['table_name']
        context['table_name'] = table_name.lower()
        
        item_id = self.request.GET.get('item_id')
        order_id = self.request.GET.get('order_id')
        category_id = self.request.GET.get('category_id')
        if item_id:
            item = get_object_or_404(Item, pk=item_id)
            context['item'] = item
        if order_id:
            order = get_object_or_404(Order, pk=order_id)
            context['order'] = order
        if category_id:
            category = get_object_or_404(Category, pk=category_id)
            context['category'] = category

        return context

    def get_initial(self):
        initial = super().get_initial()
        item_id = self.request.GET.get('item_id')
        order_id = self.request.GET.get('order_id')
        category_id = self.request.GET.get('category_id')
        if item_id:
            initial['item'] = item_id
        if order_id:
            initial['order'] = order_id
        if category_id:
            initial['category'] = category_id
        return initial

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            messages.error(request, "Page not found. Invalid URL.")
            return redirect('error')
        except ValueError:
            messages.error(request, "Invalid ID. Please provide a valid ID.")
            return redirect('error')

class DynamicUpdateView(UpdateView):
    template_name = 'admin/dynamic_form.html'
    fields = '__all__'

    def get_model(self):
        table_name = self.kwargs['table_name']
        return apps.get_model(app_label='store', model_name=table_name)

    def get_queryset(self):
        model = self.get_model()
        return model.objects.all()  # You can modify this queryset as needed

    def get_success_url(self):
        table_name = self.kwargs.get('table_name', '')
        if table_name:
            if table_name.lower() == 'itemimage':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_item_images', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'orderitem':
                order_id = self.request.GET.get('order_id')
                return reverse_lazy('manage_order_items', kwargs={'order_id': order_id})
            elif table_name.lower() == 'bid':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_bids', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'item':
                category_id = self.request.GET.get('category_id')
                return reverse_lazy('manage_category_items', kwargs={'category_id': category_id})
            else:
                return reverse_lazy('dynamic_list', kwargs={'table_name': table_name})
        else:
            pass

    def get_form(self, form_class=None):
        table_name = self.kwargs['table_name']
        model_class = get_model_class(table_name)
        form_class = FORMS_FOR_TABLES.get(model_class.__name__, form_class)
        if form_class:
            return form_class(**self.get_form_kwargs())
        else:
            self.model = model_class
            return super().get_form(form_class)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.kwargs['table_name'].lower() == 'item':
            if self.request.POST.get('confirm_action') == 'send_request':
                item_id = form.instance.pk  # Use form.instance.pk to get the item_id after form submission
                return redirect('send_request', item_id=item_id)
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_name'] = self.kwargs['table_name'].lower()
        
        item_id = self.request.GET.get('item_id')
        order_id = self.request.GET.get('order_id')
        category_id = self.request.GET.get('category_id')
        
        try:
            if item_id:
                item = get_object_or_404(Item, pk=item_id)
                context['item'] = item
            if order_id:
                order = get_object_or_404(Order, pk=order_id)
                context['order'] = order
            if category_id:
                category = get_object_or_404(Category, pk=category_id)
                context['category'] = category
        except Http404:
            messages.error(self.request, "Object not found. Please provide a valid ID.")
            return redirect('error')
        except ValueError:
            messages.error(self.request, "Invalid category ID. Please provide a valid category ID.")
            return redirect('error')

        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            messages.error(request, "Page not found. Invalid ID/URL.")
            return redirect('error')
        except ValueError:
            messages.error(request, "Invalid ID. Please provide a valid ID.")
            return redirect('error')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

class DynamicDeleteView(DeleteView):
    template_name = 'admin/dynamic_confirm_delete.html'  # Template for confirmation

    def get_model(self):
        table_name = self.kwargs['table_name']
        return apps.get_model(app_label='store', model_name=table_name)

    def get_success_url(self):
        table_name = self.kwargs.get('table_name', '')
        if table_name:
            if table_name.lower() == 'itemimage':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_item_images', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'orderitem':
                order_id = self.request.GET.get('order_id')
                return reverse_lazy('manage_order_items', kwargs={'order_id': order_id})
            elif table_name.lower() == 'bid':
                item_id = self.request.GET.get('item_id')
                category_id = self.request.GET.get('category_id')
                url = reverse_lazy('manage_bids', kwargs={'item_id': item_id})
                if category_id:
                    url += f'?category_id={category_id}'
                return url
            elif table_name.lower() == 'item':
                category_id = self.request.GET.get('category_id')
                return reverse_lazy('manage_category_items', kwargs={'category_id': category_id})
            else:
                return reverse_lazy('dynamic_list', kwargs={'table_name': table_name})
        else:
            pass

    def get_queryset(self):
        model = self.get_model()
        return model.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_name'] = self.kwargs['table_name'].lower()
        
        item_id = self.request.GET.get('item_id')
        order_id = self.request.GET.get('order_id')
        category_id = self.request.GET.get('category_id')
        
        try:
            if item_id:
                item = get_object_or_404(Item, pk=item_id)
                context['item'] = item
            if order_id:
                order = get_object_or_404(Order, pk=order_id)
                context['order'] = order
            if category_id:
                category = get_object_or_404(Category, pk=category_id)
                context['category'] = category
        except Http404:
            messages.error(self.request, "Object not found. Please provide a valid ID.")
            return redirect('error')
        except ValueError:
            messages.error(self.request, "Invalid category ID. Please provide a valid category ID.")
            return redirect('error')

        return context
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            messages.error(request, "Page not found. Invalid ID/URL.")
            return redirect('error')
        except ValueError:
            messages.error(request, "Invalid ID. Please provide a valid ID.")
            return redirect('error')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')
    
@login_required
def soft_delete_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    item.is_deleted = 'yes'
    item.save()
    messages.success(request, f'{item.item_name} has been deleted.')
    return redirect('dashboard')

@login_required
def view_profile(request):
    try:
        profile = Profile.objects.filter(user=request.user).first()
        if not profile:
            raise ValueError("Profile not found")

        shipping_addresses = ShippingAddress.objects.filter(user=request.user)
        return render(request, 'registration/profile.html', {'profile': profile, 'shipping_addresses': shipping_addresses})

    except ValueError as ve:
        messages.error(request, str(ve))
        return redirect(reverse('error'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect(reverse('error'))

@login_required
def add_shipping_address(request):
    try:
        if request.method == 'POST':
            form = ShippingAddressWebForm(request.POST)
            if form.is_valid():
                shipping_address = form.save(commit=False)
                shipping_address.user = request.user  # Link the address to the current user
                shipping_address.save()
                messages.success(request, 'Shipping address added successfully.')
                return redirect('view_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = ShippingAddressWebForm()
        return render(request, 'registration/edit_shipping_address.html', {'form': form})

    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect(reverse('error'))

@login_required
def edit_shipping_address(request, address_id):
    try:
        shipping_address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        
        if request.method == 'POST':
            form = ShippingAddressWebForm(request.POST, instance=shipping_address)
            if form.is_valid():
                form.save()
                messages.success(request, 'Shipping address updated successfully.')
                return redirect('view_profile')
        else:
            form = ShippingAddressWebForm(instance=shipping_address)
        
        return render(request, 'registration/edit_shipping_address.html', {'form': form})
    
    except Http404:
        messages.error(request, 'Shipping address not found.')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('error')

@login_required
def delete_shipping_address(request, address_id):
    try:
        shipping_address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        shipping_address.delete()
        messages.success(request, 'Shipping address deleted successfully.')
        return redirect('view_profile')
        
    except Http404:
        messages.error(request, 'Shipping address not found.')
        return redirect(reverse('error'))
        
    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect(reverse('error'))

@login_required
def edit_profile(request):
    try:
        user = request.user
        profile = get_object_or_404(Profile, user=user)

        if request.method == 'POST':
            form = EditUserProfileForm(request.POST, instance=profile, user=user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your Profile details successfully updated !!')
                return redirect('view_profile')  # Redirect to the profile page after saving
            else:
                messages.error(request, 'Please correct the error below.')
        else:
            form = EditUserProfileForm(instance=profile, user=user)

        return render(request, 'registration/edit_profile.html', {'form': form})

    except Profile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect(reverse('error'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect(reverse('error'))

class CustomLoginView(auth_views.LoginView):
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

@login_required
def custom_password_change(request):
    try:
        if request.method == 'POST':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                messages.success(request, 'Your password was successfully updated!')
                request.session['password_changed'] = True
                return redirect(reverse('password_change_done'))
            else:
                messages.error(request, 'Please correct the error below.')
        else:
            form = PasswordChangeForm(request.user)
    except ValidationError as e:
        messages.error(request, f'Validation error: {", ".join(e.messages)}')
        return HttpResponseRedirect(reverse('error'))
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return HttpResponseRedirect(reverse('error'))

    return render(request, 'registration/change-password.html', {'form': form})

@login_required
def custom_password_change_done(request):
    try:
        if request.session.get('password_changed') or request.GET.get('password_changed'):
            request.session.pop('password_changed', None)
            return render(request, 'registration/password-done.html')
        else:
            return redirect(reverse('home'))
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return HttpResponseRedirect(reverse('error'))
            
# Create your views here.
def home(request):
    try:
        items = Item.objects.filter(is_deleted='no').order_by('-created_at')  # Fetch all items
        company = Company.objects.first()  # Fetch the first company record
        
        # Fetch the root images for each item
        items_with_images = []
        for item in items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            items_with_images.append((item, root_image))
        
        has_banner_items = any(item.banner_item == 'yes' for item, _ in items_with_images)
        has_feature_items = any(item.featured_item == 'yes' for item, _ in items_with_images)
        has_auction_items = any(item.purpose == 'auction' for item, _ in items_with_images)
        
        return render(request, 'home.html', {
            'items_with_images': items_with_images,
            'company': company,
            'has_banner_items': has_banner_items,
            'has_feature_items' : has_feature_items,
            'has_auction_items' : has_auction_items
        })
    
    except DatabaseError as e:
        # Log the error or handle it as needed
        messages.error(request, f"Database Error: {str(e)}")
        return redirect(reverse('error'))  # Redirect to 'error' view
    
    except NoReverseMatch:
        # Handle NoReverseMatch exception (invalid URL accessed)
        messages.error(request, "Invalid URL accessed.")
        return redirect(reverse('error'))  # Redirect to 'error' view
    
    except Exception as e:
        # Handle other exceptions
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect(reverse('error'))  # Redirect to 'error' view


def signup(request):
    try:
        if request.user.is_authenticated:
            return redirect('home')

        if request.method == 'POST':
            form = SignUpForm(request.POST)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Your account has been created successfully. Please log in.')
                    return redirect('login')
                except ValidationError as ve:
                    messages.error(request, f'Validation error: {ve}')
                    return redirect('error')
                except DatabaseError as db_err:
                    messages.error(request, f'Database error: {db_err}')
                    return redirect('error')
                except Exception as e:
                    messages.error(request, f'An unexpected error occurred: {e}')
                    return redirect('error')
        else:
            form = SignUpForm()

        company = Company.objects.first()
        return render(request, 'registration/signup.html', {'form': form, 'company': company})

    except DatabaseError as db_err:
        messages.error(request, f'Database error: {db_err}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {e}')
        return redirect('error')

def auctions(request):
    try:
        # Fetch all items where is_deleted is 'no' and purpose is 'auction'
        items = Item.objects.filter(is_deleted='no', purpose='auction').order_by('-created_at')

        items_with_images = []
        for item in items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            items_with_images.append((item, root_image))

        # Get current datetime in Indian Standard Time (IST)
        ist = tz('Asia/Kolkata')
        current_time = datetime.now(ist)

        return render(request, 'auctions.html', {'items_with_images': items_with_images, 'current_time': current_time})

    except DatabaseError as db_err:
        messages.error(request, f'Database error: {db_err}')
        return redirect('error')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {e}')
        return redirect('error')

def ongoing_auctions(request):
    try:
        # Get current datetime in Indian Standard Time (IST)
        ist = tz('Asia/Kolkata')
        current_time = datetime.now(ist)

        # Fetch all items where is_deleted is 'no', purpose is 'auction', and end_time is greater than current time
        items = Item.objects.filter(is_deleted='no', purpose='auction', end_time__gt=current_time).order_by('-created_at')

        items_with_images = []
        for item in items:
            root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
            items_with_images.append((item, root_image))

        return render(request, 'ongoing_auctions.html', {'items_with_images': items_with_images, 'current_time': current_time})

    except DatabaseError as db_err:
        messages.error(request, "A database error occurred. Please try again later.")
        return redirect(reverse('error'))
    except ObjectDoesNotExist as obj_err:
        messages.error(request, "Some required objects were not found. Please check your data and try again.")
        return redirect(reverse('error'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect(reverse('error'))

@login_required
def auction_details(request, item_id):
    try:
        # Fetch the item and related images
        item = get_object_or_404(Item, id=item_id)
        root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
        item_images = ItemImage.objects.filter(item=item)

        # Determine if the danger text should be shown
        if item.highest_bid and Decimal(str(item.highest_bid)) >= Decimal(str(item.owner_profit_amount)):
            show_danger_text = False
        else:
            show_danger_text = True

        # Get current datetime in Indian Standard Time (IST)
        ist = tz('Asia/Kolkata')
        current_time = datetime.now(ist)

        # Fetch the latest bid
        latest_bid = Bid.objects.filter(item=item).order_by('-timestamp').first()

        # Initialize the bid forms
        bid_form = BidForm()
        auto_bid_form = AutoBidForm()

        context = {
            'item': item,
            'root_image': root_image,
            'item_images': item_images,
            'bid_form': bid_form,
            'auto_bid_form': auto_bid_form,
            'latest_bid': latest_bid,
            'show_danger_text': show_danger_text,
            'current_time': current_time,
        }

        return render(request, 'auction_details.html', context)

    except ObjectDoesNotExist:
        messages.error(request, 'The requested item does not exist.')
        return redirect('error')

    except DatabaseError as e:
        messages.error(request, 'A database error occurred. Please try again later.')
        return redirect('error')

    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('error')


@login_required
def place_bid(request, item_id):
    try:
        item = get_object_or_404(Item, id=item_id)

        # Check if item end_time has passed current Indian time
        now_utc = timezone.now()
        now_indian_time = now_utc.astimezone(timezone.get_current_timezone())
        if item.end_time <= now_indian_time:
            messages.error(request, "Bidding for this item has ended.")
            return redirect('auction-details', item_id=item.id)
        
        latest_bid = Bid.objects.filter(item=item).order_by('-timestamp').first()

        # Check if the logged-in user has created at least one shipping address
        if not ShippingAddress.objects.filter(user=request.user).count() > 0:
            messages.error(request, "You must create a shipping address before placing a bid.")
            return redirect('auction-details', item_id=item.id)
        
        if request.method == 'POST':
            bid_form = BidForm(request.POST)

            if bid_form.is_valid():
                bid_amount = bid_form.cleaned_data['bid_amount']

                # Convert Decimal128 fields to Python Decimal
                if latest_bid:
                    current_highest_bid = Decimal(str(latest_bid.bid_amount))
                else:
                    current_highest_bid = Decimal(str(item.starting_bid))

                incremental_value = Decimal(str(item.incremental_value))

                # Check if bid amount exceeds current highest bid + incremental value
                min_required_bid = current_highest_bid + incremental_value

                if item.highest_bid and request.user in item.highest_bidder.all():
                    messages.error(request, f"You cannot place another bid as you are the master bidder.")
                    return redirect('auction-details', item_id=item.id)
                
                if item.highest_bid:
                    if Decimal(str(item.highest_bid)) < Decimal(str(item.owner_profit_amount)):
                        if bid_amount <= min_required_bid:
                            messages.error(request, f"Your bid amount must exceed the current highest bid by {item.incremental_value}/-")
                            return redirect('auction-details', item_id=item.id)  # Redirect with auction_id parameter
                else:
                    if bid_amount <= min_required_bid:
                        messages.error(request, f"Your bid amount must exceed the current highest bid by {item.incremental_value}/-")
                        return redirect('auction-details', item_id=item.id)  # Redirect with auction_id parameter

                # Save the bid
                bid = bid_form.save(commit=False)
                bid.item.add(item)
                bid.bidder.add(request.user)
                bid.save()

                # Update highest_bid in Auction model if this bid is higher
                item.highest_bid = bid_amount
                item.highest_bidder.clear()
                item.highest_bidder.add(request.user)
                item.save()

                # Auto-bid logic
                if item.auto_bid_amount and item.auto_bid_amount > bid_amount:
                    auto_bidder = item.auto_bidder.first()
                    new_auto_bid_amount = bid_amount + incremental_value

                    # Create a new bid instance for auto-bidder
                    auto_bid = Bid(bid_amount=new_auto_bid_amount)
                    auto_bid.save()
                    auto_bid.item.add(item)
                    auto_bid.bidder.add(auto_bidder)
                    auto_bid.save()

                    # Update highest_bid in Auction model
                    item.highest_bid = new_auto_bid_amount
                    item.highest_bidder.clear()
                    item.highest_bidder.add(auto_bidder)
                    item.save()

                if item.highest_bid:
                    if Decimal(str(item.highest_bid)) < Decimal(str(item.owner_profit_amount)):
                        new_bid_without_user = Bid(bid_amount=item.highest_bid + incremental_value)
                        new_bid_without_user.save()
                        new_bid_without_user.item.add(item)
                        new_bid_without_user.save()

                messages.success(request, 'Your bid has been placed successfully.')
                return redirect('auction-details', item_id=item.id)
    except DatabaseError as e:
        messages.error(request, 'A database error occurred. Please try again later.')
        return redirect('error')

    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('error')

    return redirect('auctions')

@login_required
def place_auto_bid(request, item_id):
    try:
        item = get_object_or_404(Item, id=item_id)

        # Check if item end_time has passed current Indian time
        now_utc = timezone.now()
        now_indian_time = now_utc.astimezone(timezone.get_current_timezone())
        if item.end_time <= now_indian_time:
            messages.error(request, "Bidding for this item has ended.")
            return redirect('auction-details', item_id=item.id)
        
        # Check if the logged-in user has created at least one shipping address
        if not ShippingAddress.objects.filter(user=request.user).count() > 0:
            messages.error(request, "You must create a shipping address before placing a bid.")
            return redirect('auction-details', item_id=item.id)
        
        if request.method == 'POST':
            auto_bid_form = AutoBidForm(request.POST)
            
            if auto_bid_form.is_valid():
                auto_bid_amount = auto_bid_form.cleaned_data['auto_bid_amount']


                # Determine the higher value between the highest bid and the current auto-bid amount
                highest_existing_bid = max(
                    Decimal(str(item.highest_bid)) if item.highest_bid else Decimal('0'),
                    Decimal(str(item.auto_bid_amount)) if item.auto_bid_amount else Decimal('0')
                ) + Decimal(str(item.incremental_value))

                # Check if new auto-bid amount is greater than the highest existing bid plus incremental value
                if auto_bid_amount <= highest_existing_bid:
                    messages.error(request, f"Your auto-bid amount must be greater than the current highest bid or the previous auto-bid amount by at least {item.incremental_value}.")
                    return redirect('auction-details', item_id=item.id)
                
                # Convert Decimal128 fields to Python Decimal
                latest_bid = Bid.objects.filter(item=item).order_by('-timestamp').first()
                if latest_bid:
                    current_highest_bid = Decimal(str(latest_bid.bid_amount))
                else:
                    current_highest_bid = Decimal(str(item.starting_bid))

                incremental_value = Decimal(str(item.incremental_value))
                new_bid_amount = current_highest_bid + incremental_value

                # Save the auto bid details in the auction
                item.auto_bidder.clear()
                item.auto_bidder.add(request.user)
                item.auto_bid_amount = auto_bid_amount
                item.save()

                # Trigger an auto-bid if the current highest bid is less than the auto-bid amount
                if new_bid_amount <= auto_bid_amount:
                    # Create a new bid instance for auto-bidder
                    auto_bid = Bid(bid_amount=new_bid_amount)
                    auto_bid.save()
                    auto_bid.item.add(item)
                    auto_bid.bidder.add(request.user)
                    auto_bid.save()

                    # Update highest_bid in Auction model
                    item.highest_bid = new_bid_amount
                    item.highest_bidder.clear()
                    item.highest_bidder.add(request.user)
                    item.save()

                    if item.highest_bid:
                        if Decimal(str(item.highest_bid)) < Decimal(str(item.owner_profit_amount)):
                            # Create another bid instance without user
                            new_bid_without_user = Bid(bid_amount=new_bid_amount + incremental_value)
                            new_bid_without_user.save()
                            new_bid_without_user.item.add(item)
                            new_bid_without_user.save()

                messages.success(request, 'Your auto bid has been set successfully.')
                return redirect('auction-details', item_id=item.id)
    except DatabaseError as e:
        messages.error(request, 'A database error occurred. Please try again later.')
        return redirect('error')

    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('error')

    return redirect('auctions')

@login_required
def check_master_bidder(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    
    if request.user in item.highest_bidder.all():
        message = 'You are the Master Bidder!'
        status = 'success'
    else:
        message = 'You are not the Master Bidder.'
        status = 'error'
    
    return JsonResponse({'message': message, 'status': status})

@login_required
def item_details(request, item_id):
    try:
        item = get_object_or_404(Item, id=item_id)
        company = Company.objects.first()

        # Fetch the root image for the item
        root_image = ItemImage.objects.filter(item=item, root_image='yes').first()

        # Fetch all images for the item
        item_images = ItemImage.objects.filter(item=item)

        return render(request, 'coin-details.html', {
            'item': item,
            'company': company,
            'root_image': root_image,
            'item_images': item_images
        })
    except DatabaseError as e:
        # Handle database errors
        messages.error(request, 'A database error occurred. Please try again later.')
        return redirect('error')
    except Http404:
        # Handle 404 errors (object not found)
        messages.error(request, 'The item you are looking for does not exist.')
        return redirect('error')
    except Exception as e:
        # Handle any other unexpected errors
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('error')

@login_required
def cart(request):
    try:
        user = request.user
        cart_items = CartItem.objects.filter(user=user)
        total_price = sum(product.price for product in cart_items)

        # Fetch the root images for each item in the cart items
        cart_items_with_images = []
        for product in cart_items:
            item = product.item.first()  # Get the item associated with the cart item
            if item:  # Ensure the item exists
                root_image = ItemImage.objects.filter(item=item, root_image='yes').first()
                cart_items_with_images.append((product, root_image))
            else:
                cart_items_with_images.append((product, None))

        return render(request, 'cart.html', {
            'cart_items': cart_items,
            'cart_items_with_images': cart_items_with_images,
            'total_price': total_price
        })

    except ObjectDoesNotExist:
        messages.error(request, 'An item in your cart no longer exists.')
        return redirect('error')

    except DatabaseError:
        messages.error(request, 'A database error occurred. Please try again later.')
        return redirect('error')

    except Exception as e:
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('error')

def contact(request):
    company = Company.objects.first()
    return render(request, 'contact.html', {'company': company})

from django.http import Http404
def error(request, exception=None):
    company = Company.objects.first()
    return render(request, 'error.html', {'company': company})

def page_not_found(request, exception):
    return error(request, exception=exception)