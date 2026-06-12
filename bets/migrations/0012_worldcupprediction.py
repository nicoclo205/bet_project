# Generated manually for WorldCupPrediction (Django 5.2.5), 2026-06-12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0011_alter_salanotificacion_tipo_loginevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorldCupPrediction',
            fields=[
                ('id_prediccion', models.AutoField(primary_key=True, serialize=False)),
                ('group_order', models.JSONField(blank=True, default=dict)),
                ('thirds', models.JSONField(blank=True, default=list)),
                ('ko_winners', models.JSONField(blank=True, default=dict)),
                ('completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('usuario', models.OneToOneField(db_column='id_usuario', on_delete=django.db.models.deletion.CASCADE, related_name='wc_prediction', to='bets.usuario')),
            ],
            options={
                'db_table': 'worldcup_prediction',
            },
        ),
    ]
