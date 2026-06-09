# Generated manually for adding tipo field to ApiEquipo
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiequipo',
            name='tipo',
            field=models.CharField(
                blank=True,
                choices=[('National', 'Selección Nacional'), ('Club', 'Club')],
                default='Club',
                max_length=20,
                null=True
            ),
        ),
    ]
