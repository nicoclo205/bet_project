from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bets', '0008_salanotificacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomInvitation',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('invited_email', models.EmailField(max_length=254)),
                ('token', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('is_used', models.BooleanField(default=False)),
                ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_invitations', to='bets.usuario')),
                ('sala', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='bets.sala')),
            ],
            options={
                'db_table': 'room_invitation',
            },
        ),
    ]
