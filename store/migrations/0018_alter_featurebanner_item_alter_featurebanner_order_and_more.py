# Generated by Django 4.1.13 on 2024-07-04 15:47

from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0017_remove_featurebanner_owner_featurebanner_user_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='featurebanner',
            name='item',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item', to='store.item'),
        ),
        migrations.AlterField(
            model_name='featurebanner',
            name='order',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order', to='store.order'),
        ),
        migrations.AlterField(
            model_name='featurebanner',
            name='user',
            field=djongo.models.fields.ArrayReferenceField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user', to=settings.AUTH_USER_MODEL),
        ),
    ]
