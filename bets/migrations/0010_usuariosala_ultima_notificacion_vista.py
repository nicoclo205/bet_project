from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0009_roominvitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuariosala',
            name='ultima_notificacion_vista',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
