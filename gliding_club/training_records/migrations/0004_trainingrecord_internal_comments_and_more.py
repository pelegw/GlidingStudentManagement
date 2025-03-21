# Generated by Django 5.1.7 on 2025-03-20 01:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training_records', '0003_trainingrecord_is_solo'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingrecord',
            name='internal_comments',
            field=models.TextField(blank=True, help_text='Internal comments visible only to instructors'),
        ),
        migrations.AddField(
            model_name='trainingrecord',
            name='tow_height',
            field=models.PositiveIntegerField(blank=True, help_text='Height of aerotow in feet', null=True),
        ),
    ]
