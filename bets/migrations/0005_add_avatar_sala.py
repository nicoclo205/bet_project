# Generated manually for adding avatar_sala field to Sala model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0004_sala_max_miembros'),
    ]

    operations = [
        migrations.AddField(
            model_name='sala',
            name='avatar_sala',
            field=models.CharField(blank=True, default='/avatars/messi_avatar.svg', max_length=200, null=True),
        ),
    ]
