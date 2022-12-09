# Generated by Django 3.2.2 on 2022-11-20 17:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('policyengine', '0014_auto_20221120_1737'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='policy',
            name='variables',
        ),
        migrations.AddField(
            model_name='policyvariable',
            name='policy',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='variables', to='policyengine.policy'),
            preserve_default=False,
        ),
    ]