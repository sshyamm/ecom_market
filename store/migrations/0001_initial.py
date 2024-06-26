# Generated by Django 4.1.13 on 2024-06-20 09:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_countries.fields
import djongo.models.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Auction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('starting_bid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('incremental_value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('owner_profit_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('highest_bid', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('auto_bid_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('auto_bidder', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_bidderi', to=settings.AUTH_USER_MODEL)),
                ('highest_bidder', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='highest_bidsi', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(blank=True, default=1, null=True)),
                ('price', models.FloatField(blank=True, editable=False, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_name', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('address', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('postal_code', models.CharField(max_length=20)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('email', models.EmailField(max_length=255)),
                ('contact_no', models.CharField(max_length=20)),
                ('shipping_charge', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purpose', models.CharField(choices=[('sale', 'Sale'), ('auction', 'Auction')], max_length=15)),
                ('item_name', models.CharField(max_length=100)),
                ('item_desc', models.TextField()),
                ('item_year', models.IntegerField(blank=True, null=True)),
                ('item_country', models.CharField(blank=True, max_length=50, null=True)),
                ('item_material', models.CharField(blank=True, max_length=50, null=True)),
                ('item_weight', models.FloatField(blank=True, null=True)),
                ('rate', models.FloatField(blank=True, null=True)),
                ('item_status', models.CharField(blank=True, choices=[('Select', 'Select'), ('available', 'Available'), ('sold', 'Sold'), ('pending', 'Pending')], max_length=50, null=True)),
                ('featured_item', models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], default='no', max_length=3)),
                ('is_deleted', models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], default='no', max_length=3)),
                ('starting_bid', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('incremental_value', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('owner_profit_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('highest_bid', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('auto_bid_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('auto_bidder', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auto_bidder', to=settings.AUTH_USER_MODEL)),
                ('category', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.category')),
                ('highest_bidder', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='highest_bids', to=settings.AUTH_USER_MODEL)),
                ('user', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('offer_type', models.CharField(choices=[('TotalAmount', 'Total Amount Based'), ('UserBased', 'User Based')], max_length=20)),
                ('min_order_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('discount_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('max_discount_percentage', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('num_orders', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_no', models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True)),
                ('order_date', models.DateTimeField(auto_now_add=True, null=True)),
                ('status', models.CharField(blank=True, choices=[('Pending', 'Pending'), ('Processing', 'Processing'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20, null=True)),
                ('offer', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.offer')),
            ],
        ),
        migrations.CreateModel(
            name='ShippingCharge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('charge', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='ShippingAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('country', django_countries.fields.CountryField(blank=True, max_length=2, null=True)),
                ('phone_no', models.CharField(blank=True, max_length=20, null=True)),
                ('user', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SearchHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_text', models.CharField(blank=True, max_length=255, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True, max_length=500, null=True)),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('phone_no', models.CharField(blank=True, max_length=20, null=True)),
                ('website', models.URLField(blank=True, null=True)),
                ('user', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(blank=True, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=10, null=True)),
                ('item', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.item')),
                ('order', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.order')),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='shippingaddress',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=djongo.models.fields.ArrayReferenceField._on_delete, to='store.shippingaddress'),
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='ItemImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='coin_images/')),
                ('root_image', models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], default='no', max_length=3)),
                ('item', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.item')),
            ],
        ),
        migrations.CreateModel(
            name='CartItemLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')], max_length=10)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('changes', djongo.models.fields.JSONField(blank=True, null=True)),
                ('cart_item', djongo.models.fields.ArrayReferenceField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.cartitem')),
                ('user', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='cartitem',
            name='item',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.item'),
        ),
        migrations.AddField(
            model_name='cartitem',
            name='user',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Bid',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bid_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('auction', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.auction')),
                ('bidder', djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='auction',
            name='item',
            field=djongo.models.fields.ArrayReferenceField(on_delete=django.db.models.deletion.CASCADE, to='store.item'),
        ),
        migrations.AddField(
            model_name='auction',
            name='owner',
            field=djongo.models.fields.ArrayReferenceField(on_delete=django.db.models.deletion.CASCADE, related_name='owned_auctionsi', to=settings.AUTH_USER_MODEL),
        ),
    ]
