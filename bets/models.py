from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User

class PartidoStatus(models.TextChoices):
    PROGRAMADO = 'programado', 'Programado'
    EN_CURSO = 'en curso', 'En Curso'
    FINALIZADO = 'finalizado', 'Finalizado'
    CANCELADO = 'cancelado', 'Cancelado'

class ApuestaStatus(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    GANADA = 'ganada', 'Ganada'
    PERDIDA = 'perdida', 'Perdida'
    CANCELADA = 'cancelada', 'Cancelada'

class MensajeStatus(models.TextChoices):
    ACTIVO = 'activo', 'Activo'
    ELIMINADO = 'eliminado', 'Eliminado'
    REPORTADO = 'reportado', 'Reportado'

class Pais(models.Model):
    id_pais = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    continente = models.CharField(max_length=50)
    bandera = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'pais'
        verbose_name_plural = 'Paises'

class Escenario(models.Model):
    id_escenario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    capacidad = models.IntegerField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'escenario'


class Usuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil', null=True)
    id_usuario = models.AutoField(primary_key=True)
    nombre_usuario = models.CharField(max_length=100)
    correo = models.EmailField(unique=True, max_length=100)
    contrasena = models.CharField(max_length=255)  
    fecha_registro = models.DateTimeField(auto_now_add=True)
    puntos_totales = models.IntegerField(default=0)

    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    celular = models.CharField(max_length=15, blank=True, null=True)
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)

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
        indexes = [
            models.Index(fields=['id_usuario']),
            models.Index(fields=['id_sala']),
        ]


class Deporte(models.Model):
    id_deporte = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)  # Corregido el typo en "descripcion"

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'deportes'


class Competencia(models.Model):
    id_competencia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, db_column='id_deporte', blank=True, null=True)
    temporada = models.CharField(max_length=10, blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    logo = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'competencias'
        verbose_name_plural = 'Competencias'


class Equipo(models.Model):
    id_equipo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    logo = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, db_column='id_deporte', blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'equipos'
        verbose_name_plural = 'Equipos'


class Deportista(models.Model):
    id_deportista = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(Pais, on_delete=models.SET_NULL, db_column='id_pais', blank=True, null=True)
    foto = models.CharField(max_length=255, blank=True, null=True)
    id_equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, db_column='id_equipo', blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, db_column='id_deporte', blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'deportista'


class Partidos(models.Model):
    # En esta tabla se almacenarán equipos (para deportes colectivos) o deportistas (para deportes individuales)
    id_partidos = models.AutoField(primary_key=True)
    equipo_local = models.ForeignKey(Equipo, on_delete=models.CASCADE, db_column='equipo_local', related_name='partidos_local')
    equipo_visitante = models.ForeignKey(Equipo, on_delete=models.CASCADE, db_column='equipo_visitante', related_name='partidos_visitante')
    deportista_local = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='deportista_local', related_name='partidos_local', blank=True, null=True)
    deportista_visitante = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='deportista_visitante', related_name='partidos_visitante', blank=True, null=True)
    resultado_local = models.IntegerField(default=0)
    resultado_visitante = models.IntegerField(default=0)
    id_competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, db_column='id_competencia', blank=True, null=True)
    fecha_partido = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=PartidoStatus.choices, default=PartidoStatus.PROGRAMADO)
    id_escenario = models.ForeignKey(Escenario, on_delete=models.CASCADE, db_column='id_escenario', blank=True, null=True)

    def __str__(self):
        return f"{self.equipo_local.nombre} vs {self.equipo_visitante.nombre}"

    class Meta:
        db_table = 'partidos'
        verbose_name_plural = 'Partidos'
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_partido']),
            models.Index(fields=['id_competencia']),
        ]


class PartidoFutbol(models.Model):
    id_partido_futbol = models.AutoField(primary_key=True)
    id_partido = models.OneToOneField(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    goles_local = models.IntegerField(default=0)
    goles_visitante = models.IntegerField(default=0)
    tarjeta_amarilla_local = models.IntegerField(default=0)
    tarjeta_amarilla_visitante = models.IntegerField(default=0)
    tarjeta_roja_local = models.IntegerField(default=0)
    tarjeta_roja_visitante = models.IntegerField(default=0)
    goles_local_1 = models.IntegerField(default=0)
    goles_visitante_1 = models.IntegerField(default=0)
    goles_local_2 = models.IntegerField(default=0)
    goles_visitante_2 = models.IntegerField(default=0)
    penales_local = models.IntegerField(default=0)
    penales_visitante = models.IntegerField(default=0)
    tiros_esquina_local = models.IntegerField(default=0)
    tiros_esquina_visitante = models.IntegerField(default=0)

    def __str__(self):
        return f"Partido de Fútbol: {self.id_partido}"

    class Meta:
        db_table = 'partidos_futbol'
        verbose_name = 'Partido de Fútbol'
        verbose_name_plural = 'Partidos de Fútbol'


class PartidoTenis(models.Model):
    id_partido_tenis = models.AutoField(primary_key=True)
    id_partido = models.OneToOneField(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    sets_totales = models.IntegerField(default=0)
    games_totales = models.IntegerField(default=0)
    marcador_local_1 = models.IntegerField(default=0)
    marcador_visitante_1 = models.IntegerField(default=0)
    marcador_local_2 = models.IntegerField(default=0)
    marcador_visitante_2 = models.IntegerField(default=0)
    marcador_local_3 = models.IntegerField(default=0)
    marcador_visitante_3 = models.IntegerField(default=0)
    marcador_local_4 = models.IntegerField(default=0)
    marcador_visitante_4 = models.IntegerField(default=0)
    marcador_local_5 = models.IntegerField(default=0)
    marcador_visitante_5 = models.IntegerField(default=0)
    aces_local = models.IntegerField(default=0)
    aces_visitante = models.IntegerField(default=0)
    dobles_faltas_local = models.IntegerField(default=0)
    dobles_faltas_visitante = models.IntegerField(default=0)
    max_sets = models.IntegerField(default=0)
    tiebreak_1 = models.IntegerField(default=0)
    tiebreak_2 = models.IntegerField(default=0)
    tiebreak_3 = models.IntegerField(default=0)
    tiebreak_4 = models.IntegerField(default=0)
    tiebreak_5 = models.IntegerField(default=0)

    def __str__(self):
        return f"Partido de Tenis: {self.id_partido}"

    class Meta:
        db_table = 'partidos_tenis'
        verbose_name = 'Partido de Tenis'
        verbose_name_plural = 'Partidos de Tenis'


class PartidoBaloncesto(models.Model):
    id_partido_baloncesto = models.AutoField(primary_key=True)
    id_partido = models.OneToOneField(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    puntos_local = models.IntegerField(default=0)
    puntos_visitante = models.IntegerField(default=0)
    resultado_local_1 = models.IntegerField(default=0)
    resultado_visitante_1 = models.IntegerField(default=0)
    resultado_local_2 = models.IntegerField(default=0)
    resultado_visitante_2 = models.IntegerField(default=0)
    resultado_local_3 = models.IntegerField(default=0)
    resultado_visitante_3 = models.IntegerField(default=0)
    resultado_local_4 = models.IntegerField(default=0)
    resultado_visitante_4 = models.IntegerField(default=0)
    rebotes_local = models.IntegerField(default=0)
    rebotes_visitante = models.IntegerField(default=0)
    asistencias_local = models.IntegerField(default=0)
    asistencias_visitante = models.IntegerField(default=0)
    robos_local = models.IntegerField(default=0)
    robos_visitante = models.IntegerField(default=0)
    tapones_local = models.IntegerField(default=0)
    tapones_visitante = models.IntegerField(default=0)
    tiros_libres_local = models.IntegerField(default=0)
    tiros_libres_visitante = models.IntegerField(default=0)
    tiros_3_local = models.IntegerField(default=0)
    tiros_3_visitante = models.IntegerField(default=0)
    faltas_local = models.IntegerField(default=0)
    faltas_visitante = models.IntegerField(default=0)

    def __str__(self):
        return f"Partido de Baloncesto: {self.id_partido}"

    class Meta:
        db_table = 'partidos_baloncesto'
        verbose_name = 'Partido de Baloncesto'
        verbose_name_plural = 'Partidos de Baloncesto'


class CarreraF1(models.Model):
    id_carrera_f1 = models.AutoField(primary_key=True)
    id_escenario = models.ForeignKey(Escenario, on_delete=models.CASCADE, db_column='id_escenario', blank=True, null=True)
    id_competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, db_column='id_competencia', blank=True, null=True)
    fecha_carrera = models.DateTimeField(blank=True, null=True)
    vueltas = models.IntegerField(default=0)
    posicion_1 = models.IntegerField(default=0)
    posicion_2 = models.IntegerField(default=0)
    posicion_3 = models.IntegerField(default=0)
    posicion_4 = models.IntegerField(default=0)
    posicion_5 = models.IntegerField(default=0)
    posicion_6 = models.IntegerField(default=0)
    posicion_7 = models.IntegerField(default=0)
    posicion_8 = models.IntegerField(default=0)
    posicion_9 = models.IntegerField(default=0)
    posicion_10 = models.IntegerField(default=0)
    vuelta_rapida = models.IntegerField(default=0)
    id_equipo_competencia = models.ForeignKey(Equipo, on_delete=models.SET_NULL, related_name='carreras_equipo', db_column='id_equipo_competencia', blank=True, null=True)
    id_deportista_competencia = models.ForeignKey(Deportista, on_delete=models.SET_NULL, related_name='competencias_deportista', db_column='id_deportista_competencia', blank=True, null=True)
    id_pais_competencia = models.ForeignKey(Pais, on_delete=models.SET_NULL, related_name='carreras_pais', db_column='id_pais_competencia', blank=True, null=True)
    id_deportista = models.ForeignKey(Deportista, on_delete=models.SET_NULL, related_name='carreras', db_column='id_deportista', blank=True, null=True)
    
    def __str__(self):
        return f"Carrera de F1: {self.id_escenario.nombre if self.id_escenario else 'Sin escenario'}"

    class Meta:
        db_table = 'carreras_f1'
        verbose_name = 'Carrera de F1'
        verbose_name_plural = 'Carreras de F1'


class ApuestaFutbol(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    resultado_local_1 = models.IntegerField(default=0)
    resultado_visitante_1 = models.IntegerField(default=0)
    resultado_local_2 = models.IntegerField(default=0)
    resultado_visitante_2 = models.IntegerField(default=0)
    tarjeta_amarilla_local = models.IntegerField(default=0)
    tarjeta_amarilla_visitante = models.IntegerField(default=0)
    tarjeta_roja_local = models.IntegerField(default=0)
    tarjeta_roja_visitante = models.IntegerField(default=0)
    tiros_esquina_local = models.IntegerField(default=0)
    tiros_esquina_visitante = models.IntegerField(default=0)
    penales_local = models.IntegerField(default=0)
    penales_visitante = models.IntegerField(default=0)  
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"Apuesta de {self.id_usuario.nombre_usuario} - {self.id_partido}"

    class Meta:
        db_table = 'apuestasFutbol'
        verbose_name_plural = 'ApuestasFutbol'
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_partido']),
            models.Index(fields=['estado']),
        ]

class ApuestaTenis(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    marcador_local_1 = models.IntegerField(default=0)
    marcador_visitante_1 = models.IntegerField(default=0)
    marcador_local_2 = models.IntegerField(default=0)
    marcador_visitante_2 = models.IntegerField(default=0)
    marcador_local_3 = models.IntegerField(default=0)
    marcador_visitante_3 = models.IntegerField(default=0)
    marcador_local_4 = models.IntegerField(default=0)
    marcador_visitante_4 = models.IntegerField(default=0)
    marcador_local_5 = models.IntegerField(default=0)
    marcador_visitante_5 = models.IntegerField(default=0)
    games_totales = models.IntegerField(default=0)
    sets_totales = models.IntegerField(default=0)
    aces_local = models.IntegerField(default=0)
    aces_visitante = models.IntegerField(default=0)
    dobles_faltas_local = models.IntegerField(default=0)
    dobles_faltas_visitante = models.IntegerField(default=0)
    tiebreak_1 = models.IntegerField(default=0)
    tiebreak_2 = models.IntegerField(default=0)
    tiebreak_3 = models.IntegerField(default=0)
    tiebreak_4 = models.IntegerField(default=0)
    tiebreak_5 = models.IntegerField(default=0)
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"Apuesta de {self.id_usuario.nombre_usuario} - {self.id_partido}"

    class Meta:
        db_table = 'apuestasTenis'
        verbose_name_plural = 'ApuestasTenis'
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_partido']),
            models.Index(fields=['estado']),
        ]

class ApuestaBaloncesto(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(Partidos, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    resultado_local_1 = models.IntegerField(default=0)
    resultado_visitante_1 = models.IntegerField(default=0)
    resultado_local_2 = models.IntegerField(default=0)
    resultado_visitante_2 = models.IntegerField(default=0)
    resultado_local_3 = models.IntegerField(default=0)
    resultado_visitante_3 = models.IntegerField(default=0)
    resultado_local_4 = models.IntegerField(default=0)
    resultado_visitante_4 = models.IntegerField(default=0)
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"Apuesta de {self.id_usuario.nombre_usuario} - {self.id_partido}"

    class Meta:
        db_table = 'apuestasBaloncesto'
        verbose_name_plural = 'ApuestasBaloncesto'
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_partido']),
            models.Index(fields=['estado']),
        ]

class ApuestaF1(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_carrera = models.ForeignKey(CarreraF1, on_delete=models.CASCADE, db_column='id_carrera')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    prediccion_piloto_1 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto', related_name='apuestas_f1')
    prediccion_piloto_2 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_2', related_name='apuestas_f1_2', blank=True, null=True)
    prediccion_piloto_3 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_3', related_name='apuestas_f1_3', blank=True, null=True)
    prediccion_piloto_4 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_4', related_name='apuestas_f1_4', blank=True, null=True)
    prediccion_piloto_5 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_5', related_name='apuestas_f1_5', blank=True, null=True)
    prediccion_piloto_6 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_6', related_name='apuestas_f1_6', blank=True, null=True)
    prediccion_piloto_7 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_7', related_name='apuestas_f1_7', blank=True, null=True)
    prediccion_piloto_8 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_8', related_name='apuestas_f1_8', blank=True, null=True)
    prediccion_piloto_9 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_9', related_name='apuestas_f1_9', blank=True, null=True)
    prediccion_piloto_10 = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_piloto_10', related_name='apuestas_f1_10', blank=True, null=True)
    prediccion_vuelta_rapida = models.ForeignKey(Deportista, on_delete=models.CASCADE, db_column='prediccion_vuelta_rapida', related_name='apuestas_f1_vuelta_rapida', blank=True, null=True)  
    
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"Apuesta de {self.id_usuario.nombre_usuario} - {self.id_carrera}"

    class Meta:
        db_table = 'apuestasF1'
        verbose_name_plural = 'ApuestasF1'
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_carrera']),
            models.Index(fields=['estado']),
        ]


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
        indexes = [
            models.Index(fields=['id_usuario']),
            models.Index(fields=['id_sala']),
            models.Index(fields=['periodo']),
        ]


class MensajeChat(models.Model):
    id_mensaje = models.AutoField(primary_key=True)
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=MensajeStatus.choices, default=MensajeStatus.ACTIVO)

    def __str__(self):
        return f"Mensaje de {self.id_usuario.nombre_usuario} en {self.id_sala.nombre}"

    class Meta:
        db_table = 'mensajes_chat'
        verbose_name = 'Mensaje de Chat'
        verbose_name_plural = 'Mensajes de Chat'
        indexes = [
            models.Index(fields=['id_sala']),
            models.Index(fields=['id_usuario']),
            models.Index(fields=['fecha_envio']),
        ]