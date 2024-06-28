# Generated by Django 4.1.13 on 2024-06-28 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_order_razorpay_order_id_order_razorpay_payment_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_duration',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_initiated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]