# Generated by Django 3.2.2 on 2022-10-16 20:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0010_baseaction_data_store'),
    ]

    operations = [
        migrations.AddField(
            model_name='policy',
            name='variables',
            field=models.JSONField(null=True, verbose_name='PolicyVariables'),
        ),
    ]