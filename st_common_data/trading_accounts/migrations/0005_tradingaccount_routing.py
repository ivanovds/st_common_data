# Generated by Django 4.0.7 on 2024-03-11 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading_accounts', '0004_tradingaccount_platform'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingaccount',
            name='routing',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'TRAFIX'), (1, 'LYNX'), (2, 'STERLING'), (3, 'EMULATOR')], default=None, null=True, verbose_name='Routing'),
        ),
    ]