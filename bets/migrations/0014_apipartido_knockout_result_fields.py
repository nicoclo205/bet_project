"""
Migration: add knockout result fields to ApiPartido.

  resultado_tiene_tiempo_extra  – did this match go to extra time?
  resultado_tiene_penales       – did this match go to a penalty shootout?
  ganador_penales               – which team won the shootout?

These are set by admin staff when entering final results for knockout matches
and are used by calcular_bonus_ko() to award ET / penalty-winner bonuses.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0013_knockout_betting_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='apipartido',
            name='resultado_tiene_tiempo_extra',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='apipartido',
            name='resultado_tiene_penales',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='apipartido',
            name='ganador_penales',
            field=models.ForeignKey(
                blank=True,
                db_column='ganador_penales',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='partidos_ganados_penales',
                to='bets.apiequipo',
            ),
        ),
    ]
