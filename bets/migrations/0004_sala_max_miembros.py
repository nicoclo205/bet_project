# Generated manually on 2025-12-19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0003_saladeporte_salaliga_salapartido'),
    ]

    operations = [
        migrations.AddField(
            model_name='sala',
            name='max_miembros',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
