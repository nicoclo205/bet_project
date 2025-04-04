# Generated by Django 5.1.7 on 2025-03-16 19:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Pais",
            fields=[
                ("id_pais", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=50)),
                ("continente", models.CharField(max_length=50)),
                ("bandera", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "db_table": "pais",
            },
        ),
        migrations.CreateModel(
            name="Usuario",
            fields=[
                ("id_usuario", models.AutoField(primary_key=True, serialize=False)),
                ("nombre_usuario", models.CharField(max_length=100)),
                ("correo", models.CharField(max_length=100, unique=True)),
                ("contrasena", models.CharField(max_length=255)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
                ("puntos_totales", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "usuario",
            },
        ),
        migrations.CreateModel(
            name="Equipos",
            fields=[
                ("id_equipos", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=100)),
                ("logo", models.CharField(blank=True, max_length=255, null=True)),
                ("tipo", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "id_pais",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_pais",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="bets.pais",
                    ),
                ),
            ],
            options={
                "db_table": "equipos",
            },
        ),
        migrations.CreateModel(
            name="Competiciones",
            fields=[
                (
                    "id_competiciones",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                ("nombre", models.CharField(max_length=100)),
                ("continente", models.CharField(max_length=50)),
                ("temporada", models.CharField(blank=True, max_length=10, null=True)),
                ("fecha_inicio", models.DateField(blank=True, null=True)),
                ("fecha_fin", models.DateField(blank=True, null=True)),
                (
                    "id_pais",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_pais",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="bets.pais",
                    ),
                ),
            ],
            options={
                "db_table": "competiciones",
            },
        ),
        migrations.CreateModel(
            name="Partidos",
            fields=[
                ("id_partidos", models.AutoField(primary_key=True, serialize=False)),
                ("resultado_local", models.IntegerField(default=0)),
                ("resultado_visitante", models.IntegerField(default=0)),
                ("fecha_partido", models.DateTimeField(blank=True, null=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("programado", "Programado"),
                            ("en curso", "En Curso"),
                            ("finalizado", "Finalizado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="programado",
                        max_length=10,
                    ),
                ),
                (
                    "equipo_local",
                    models.ForeignKey(
                        db_column="equipo_local",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="partidos_local",
                        to="bets.equipos",
                    ),
                ),
                (
                    "equipo_visitante",
                    models.ForeignKey(
                        db_column="equipo_visitante",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="partidos_visitante",
                        to="bets.equipos",
                    ),
                ),
                (
                    "id_competiciones",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_competiciones",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.competiciones",
                    ),
                ),
            ],
            options={
                "db_table": "partidos",
            },
        ),
        migrations.CreateModel(
            name="Sala",
            fields=[
                ("id_sala", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=50)),
                (
                    "descripcion",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("estado", models.BooleanField(default=True)),
                (
                    "codigo_sala",
                    models.CharField(
                        blank=True, max_length=100, null=True, unique=True
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "sala",
            },
        ),
        migrations.CreateModel(
            name="Ranking",
            fields=[
                ("id_ranking", models.AutoField(primary_key=True, serialize=False)),
                ("puntos", models.IntegerField(default=0)),
                ("posicion", models.IntegerField(blank=True, null=True)),
                ("periodo", models.DateField(auto_now_add=True)),
                (
                    "id_sala",
                    models.ForeignKey(
                        db_column="id_sala",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.sala",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "ranking",
            },
        ),
        migrations.CreateModel(
            name="MensajesChat",
            fields=[
                ("id_mensaje", models.AutoField(primary_key=True, serialize=False)),
                ("contenido", models.TextField()),
                ("fecha_envio", models.DateTimeField(auto_now_add=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("activo", "Activo"),
                            ("eliminado", "Eliminado"),
                            ("reportado", "Reportado"),
                        ],
                        default="activo",
                        max_length=10,
                    ),
                ),
                (
                    "id_sala",
                    models.ForeignKey(
                        db_column="id_sala",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.sala",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "mensajes_chat",
            },
        ),
        migrations.CreateModel(
            name="Apuestas",
            fields=[
                ("id_apuestas", models.AutoField(primary_key=True, serialize=False)),
                ("prediccion_local", models.IntegerField()),
                ("prediccion_visitante", models.IntegerField()),
                ("fecha_apuesta", models.DateTimeField(auto_now_add=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("ganada", "Ganada"),
                            ("perdida", "Perdida"),
                            ("cancelada", "Cancelada"),
                        ],
                        default="pendiente",
                        max_length=10,
                    ),
                ),
                ("puntos_ganados", models.IntegerField(default=0)),
                (
                    "id_partido",
                    models.ForeignKey(
                        db_column="id_partido",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.partidos",
                    ),
                ),
                (
                    "id_sala",
                    models.ForeignKey(
                        db_column="id_sala",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.sala",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "apuestas",
            },
        ),
        migrations.CreateModel(
            name="UsuarioSala",
            fields=[
                (
                    "id_usuario_sala",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                ("fecha_ingreso", models.DateTimeField(auto_now_add=True)),
                ("rol", models.CharField(default="participante", max_length=50)),
                (
                    "id_sala",
                    models.ForeignKey(
                        db_column="id_sala",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.sala",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bets.usuario",
                    ),
                ),
            ],
            options={
                "db_table": "usuario_sala",
                "unique_together": {("id_usuario", "id_sala")},
            },
        ),
    ]
