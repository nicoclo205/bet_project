# Generated by Django 5.1.7 on 2025-03-17 16:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="apellido",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="usuario",
            name="celular",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name="usuario",
            name="foto_perfil",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="usuario",
            name="nombre",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
