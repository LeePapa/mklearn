# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2019-06-06 01:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orgenization', '0004_teacher_image'),
        ('courses', '0006_auto_20190606_0034'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='teacher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='orgenization.Teacher', verbose_name='讲师'),
        ),
    ]