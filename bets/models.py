from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Pais(models.Model):
    id_pais = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    continente = models.CharField(max_length=50)
    bandera = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'pais'


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre_usuario = models.CharField(max_length=100)
    correo = models.CharField(unique=True, max_length=100)
    contrasena = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    puntos_totales = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre_usuario
    
    def save(self, *args, **kwargs):
        # Hash la contraseña si es una nueva contraseña
        if not self.id_usuario or not self.contrasena.startswith('pbkdf2_'):
            self.contrasena = make_password(self.contrasena)
        super().save(*args, **kwargs)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.contrasena)

    class Meta:
        db_table = 'usuario'


class Sala(models.Model):
    id_sala = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    codigo_sala = models.CharField(unique=True, max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'sala'


class UsuarioSala(models.Model):
    id_usuario_sala = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    rol = models.CharField(max_length=50, default='participante')

    def __str__(self):
        return f"{self.id_usuario.nombre_usuario} en {self.id_sala.nombre}"

    class Meta:
        db_table = 'usuario_sala'
        unique_together = (('id_usuario', 'id_sala'),)


class Competiciones(models.Model):
    id_competiciones = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    continente = models.CharField(max_length=50)
    temporada = models.CharField(max_length=10, blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'competiciones'


class Equipos(models.Model):
    id_equipos = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    logo = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'equipos'


class Partidos(models.Model):
    ESTADO_CHOICES = [
        ('programado', 'Programado'),
        ('en curso', 'En Curso'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id_partidos = models.AutoField(primary_key=True)
    equipo_local = models.ForeignKey(Equipos, on_delete=models.CASCADE, db_column='equipo_local', related_name='partidos_local')
    equipo_visitante = models.ForeignKey(Equipos, on_delete=models.CASCADE, db_column='equipo_visitante', related_name='partidos_visitante')
    resultado_local = models.IntegerField(default=0)
    resultado_visitante = models.IntegerField(default=0)
    id_competiciones = models.ForeignKey(Competiciones, on_delete=models.CASCADE, db_column='id_competiciones', blank=True, null=True)
    fecha_partido = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='programado')

    def __str__(self):
        return f"{self.equipo_local.nombre} vs {self.equipo_visitante.nombre}"

    class Meta:
        db_table = 'partidos'


class Apuestas(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('ganada', 'Ganada'),
        ('perdida', 'Perdida'),
        ('cancelada', 'Cancelada'),
    ]
    
    id_apuestas = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"Apuesta de {self.id_usuario.nombre_usuario} - {self.id_partido}"

    class Meta:
        db_table = 'apuestas'


class Ranking(models.Model):
    id_ranking = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    puntos = models.IntegerField(default=0)
    posicion = models.IntegerField(blank=True, null=True)
    periodo = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Ranking de {self.id_usuario.nombre_usuario} en {self.id_sala.nombre}"

    class Meta:
        db_table = 'ranking'


class MensajesChat(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('eliminado', 'Eliminado'),
        ('reportado', 'Reportado'),
    ]
    
    id_mensaje = models.AutoField(primary_key=True)
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')

    def __str__(self):
        return f"Mensaje de {self.id_usuario.nombre_usuario} en {self.id_sala.nombre}"

    class Meta:
        db_table = 'mensajes_chat'