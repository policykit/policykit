# Generated by Django 3.2.2 on 2024-10-22 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0020_alter_policyvariable_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='policyvariable',
            name='default_value',
            field=models.CharField(max_length=1000),
        ),
    ]