# Generated by Django 3.2.2 on 2024-10-02 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0019_auto_20240827_1819'),
    ]

    operations = [
        migrations.AlterField(
            model_name='policyvariable',
            name='value',
            field=models.CharField(blank=True, max_length=1000),
        ),
    ]