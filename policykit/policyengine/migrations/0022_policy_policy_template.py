# Generated by Django 3.2.25 on 2024-12-18 18:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0021_alter_policyvariable_default_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='policy',
            name='policy_template',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='policy', to='policyengine.policytemplate'),
        ),
    ]
