# Generated by Django 3.2.25 on 2025-04-05 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0024_auto_20250405_0758'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transformer',
            name='name',
            field=models.TextField(blank=True, default=''),
        ),
    ]
