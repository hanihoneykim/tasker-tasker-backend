# Generated by Django 3.2 on 2023-10-13 12:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20231013_1207'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='team',
        ),
    ]
