# Generated by Django 5.1.7 on 2025-03-20 15:39

import training_records.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training_records', '0004_trainingrecord_internal_comments_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='student_license_photo',
            field=models.ImageField(blank=True, null=True, upload_to=training_records.models.student_license_path),
        ),
        migrations.AlterField(
            model_name='user',
            name='student_medical_id_photo',
            field=models.ImageField(blank=True, null=True, upload_to=training_records.models.student_medical_path),
        ),
    ]
