# Generated by Django 5.1.7 on 2025-06-02 14:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_auction_current_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuctionReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auction_title', models.CharField(max_length=255)),
                ('auction_uuid', models.CharField(max_length=100)),
                ('reason', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('auction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports_received', to='api.auction')),
                ('auction_seller', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reported_auctions', to=settings.AUTH_USER_MODEL)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports_made', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('reporter', 'auction')},
            },
        ),
    ]
