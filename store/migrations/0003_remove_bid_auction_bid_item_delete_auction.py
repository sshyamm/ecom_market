# Generated by Django 4.1.13 on 2024-06-20 13:31

from django.db import migrations
import django.db.models.deletion
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_alter_auction_start_time'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bid',
            name='auction',
        ),
        migrations.AddField(
            model_name='bid',
            name='item',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='store.item'),
        ),
        migrations.DeleteModel(
            name='Auction',
        ),
    ]