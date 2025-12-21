from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User
from django.utils import timezone
import json

# Status enums
class PartidoStatus(models.TextChoices):
    PROGRAMADO = 'programado', 'Programado'
    EN_CURSO = 'en curso', 'En Curso'
    FINALIZADO = 'finalizado', 'Finalizado'
    CANCELADO = 'cancelado', 'Cancelado'
    POSPUESTO = 'pospuesto', 'Pospuesto'
    SUSPENDIDO = 'suspendido', 'Suspendido'

class ApuestaStatus(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    GANADA = 'ganada', 'Ganada'
    PERDIDA = 'perdida', 'Perdida'
    CANCELADA = 'cancelada', 'Cancelada'

class MensajeStatus(models.TextChoices):
    ACTIVO = 'activo', 'Activo'
    ELIMINADO = 'eliminado', 'Eliminado'
    REPORTADO = 'reportado', 'Reportado'

# Core user models
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
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_usuario
    
    def save(self, *args, **kwargs):
        # Hash la contraseña si es una nueva contraseña
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Usuario.save() called for: {self.nombre_usuario}")
        logger.info(f"  id_usuario: {self.id_usuario}")
        logger.info(f"  contrasena starts with 'pbkdf2_': {self.contrasena.startswith('pbkdf2_') if self.contrasena else False}")

        if not self.id_usuario or not self.contrasena.startswith('pbkdf2_'):
            logger.info(f"  Hashing password...")
            old_pass = self.contrasena
            self.contrasena = make_password(self.contrasena)
            logger.info(f"  Password hashed: {old_pass} -> {self.contrasena[:50]}...")
        else:
            logger.info(f"  Password already hashed, skipping hash")

        super().save(*args, **kwargs)
        logger.info(f"  Usuario saved to database")
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.contrasena)

    class Meta:
        db_table = 'usuario'

class Sala(models.Model):
    id_sala = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    max_miembros = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    codigo_sala = models.CharField(unique=True, max_length=100, blank=True, null=True)
    avatar_sala = models.CharField(max_length=200, blank=True, null=True, default='/avatars/messi_avatar.svg')

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

# Reference data tables (minimal data from API)
class Deporte(models.Model):
    id_deporte = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    api_sport_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'deportes'

class ApiPais(models.Model):
    id_pais = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, null=True) # API country code
    bandera_url = models.CharField(max_length=255, blank=True, null=True)
    api_id = models.IntegerField(blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'api_paises'
        verbose_name_plural = 'API Paises'

class ApiLiga(models.Model):
    id_liga = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(ApiPais, on_delete=models.SET_NULL, blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)  # 'league' or 'cup'
    temporada_actual = models.CharField(max_length=10, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    api_id = models.IntegerField(blank=True, null=True)
    tiene_eventos = models.BooleanField(default=False)
    tiene_alineaciones = models.BooleanField(default=False)
    tiene_estadisticas = models.BooleanField(default=False)
    tiene_clasificacion = models.BooleanField(default=False)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.temporada_actual or 'Sin temporada'})"

    class Meta:
        db_table = 'api_ligas'
        verbose_name_plural = 'API Ligas'

class ApiEquipo(models.Model):
    id_equipo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    nombre_corto = models.CharField(max_length=50, blank=True, null=True)
    id_pais = models.ForeignKey(ApiPais, on_delete=models.SET_NULL, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    api_id = models.IntegerField(blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=[('National', 'Selección Nacional'), ('Club', 'Club')], default='Club', blank=True, null=True)
    fundado = models.IntegerField(blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'api_equipos'
        verbose_name_plural = 'API Equipos'

class ApiJugador(models.Model):
    id_jugador = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(ApiPais, on_delete=models.SET_NULL, blank=True, null=True)
    id_equipo = models.ForeignKey(ApiEquipo, on_delete=models.SET_NULL, blank=True, null=True)
    id_deporte = models.ForeignKey(Deporte, on_delete=models.SET_NULL, blank=True, null=True)
    api_id = models.IntegerField(blank=True, null=True)
    foto_url = models.CharField(max_length=255, blank=True, null=True)
    posicion = models.CharField(max_length=50, blank=True, null=True)
    numero = models.IntegerField(blank=True, null=True)
    edad = models.IntegerField(blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'api_jugadores'
        verbose_name_plural = 'API Jugadores'

class ApiVenue(models.Model):
    id_venue = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    id_pais = models.ForeignKey(ApiPais, on_delete=models.SET_NULL, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    capacidad = models.IntegerField(blank=True, null=True)
    superficie = models.CharField(max_length=50, blank=True, null=True)
    api_id = models.IntegerField(blank=True, null=True)
    imagen_url = models.CharField(max_length=255, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'api_venues'
        verbose_name_plural = 'API Venues'

# Main fixture model with API integration
class ApiPartido(models.Model):
    id_partido = models.AutoField(primary_key=True)
    api_fixture_id = models.IntegerField(unique=True)
    id_liga = models.ForeignKey(ApiLiga, on_delete=models.CASCADE, db_column='id_liga')
    temporada = models.CharField(max_length=10)
    fecha = models.DateTimeField()
    ronda = models.CharField(max_length=50, blank=True, null=True)
    
    # Teams
    equipo_local = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE, related_name='partidos_local')
    equipo_visitante = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE, related_name='partidos_visitante')
    
    # Scores
    goles_local = models.IntegerField(null=True, blank=True)
    goles_visitante = models.IntegerField(null=True, blank=True)
    
    # Additional info
    estado = models.CharField(max_length=20, choices=PartidoStatus.choices, default=PartidoStatus.PROGRAMADO)
    tiempo_partido = models.CharField(max_length=20, blank=True, null=True)  # For storing halftime, etc
    id_venue = models.ForeignKey(ApiVenue, on_delete=models.SET_NULL, blank=True, null=True)
    
    # Tracking fields
    eventos_cargados = models.BooleanField(default=False)
    alineaciones_cargadas = models.BooleanField(default=False)
    estadisticas_cargadas = models.BooleanField(default=False)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.equipo_local.nombre} vs {self.equipo_visitante.nombre} ({self.fecha.strftime('%Y-%m-%d')})"
    
    def actualizar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        self.ultima_actualizacion = timezone.now()
        self.save()
    
    class Meta:
        db_table = 'api_partidos'
        verbose_name_plural = 'API Partidos'
        indexes = [
            models.Index(fields=['api_fixture_id']),
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['id_liga', 'temporada']),
        ]

# Detailed entities for cached API data
class ApiPartidoEstadisticas(models.Model):
    id_estadistica = models.AutoField(primary_key=True)
    id_partido = models.ForeignKey(ApiPartido, on_delete=models.CASCADE, related_name='estadisticas')
    id_equipo = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE)
    
    # Common statistics
    posesion = models.FloatField(blank=True, null=True)
    tiros_total = models.IntegerField(blank=True, null=True)
    tiros_a_puerta = models.IntegerField(blank=True, null=True)
    tiros_fuera = models.IntegerField(blank=True, null=True)
    tiros_bloqueados = models.IntegerField(blank=True, null=True)
    corners = models.IntegerField(blank=True, null=True)
    offsides = models.IntegerField(blank=True, null=True)
    faltas = models.IntegerField(blank=True, null=True)
    tarjetas_amarillas = models.IntegerField(blank=True, null=True)
    tarjetas_rojas = models.IntegerField(blank=True, null=True)
    
    # Additional stats as JSON
    estadisticas_extra = models.JSONField(blank=True, null=True)
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Estadísticas: {self.id_partido} - {self.id_equipo.nombre}"
    
    class Meta:
        db_table = 'api_partido_estadisticas'
        verbose_name_plural = 'API Partido Estadísticas'
        unique_together = (('id_partido', 'id_equipo'),)

class ApiPartidoEvento(models.Model):
    id_evento = models.AutoField(primary_key=True)
    id_partido = models.ForeignKey(ApiPartido, on_delete=models.CASCADE, related_name='eventos')
    
    tipo_evento = models.CharField(max_length=50)  # goal, card, subst, var
    minuto = models.IntegerField()
    id_equipo = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE)
    id_jugador = models.ForeignKey(ApiJugador, on_delete=models.SET_NULL, blank=True, null=True, related_name='eventos')
    id_jugador_asistencia = models.ForeignKey(ApiJugador, on_delete=models.SET_NULL, blank=True, null=True, related_name='asistencias')
    
    # Additional event details
    detalles = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.tipo_evento} - {self.id_partido} ({self.minuto}')"
    
    class Meta:
        db_table = 'api_partido_eventos'
        verbose_name_plural = 'API Partido Eventos'
        indexes = [
            models.Index(fields=['id_partido', 'tipo_evento']),
        ]

class ApiPartidoAlineacion(models.Model):
    id_alineacion = models.AutoField(primary_key=True)
    id_partido = models.ForeignKey(ApiPartido, on_delete=models.CASCADE, related_name='alineaciones')
    id_equipo = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE)
    
    formacion = models.CharField(max_length=20, blank=True, null=True)
    id_entrenador = models.IntegerField(blank=True, null=True)
    nombre_entrenador = models.CharField(max_length=100, blank=True, null=True)
    
    # Starters and substitutes as JSON
    titulares = models.JSONField(blank=True, null=True)
    suplentes = models.JSONField(blank=True, null=True)
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Alineación: {self.id_partido} - {self.id_equipo.nombre}"
    
    class Meta:
        db_table = 'api_partido_alineaciones'
        verbose_name_plural = 'API Partido Alineaciones'
        unique_together = (('id_partido', 'id_equipo'),)

# Multi-sport betting models
class ApuestaFutbol(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(ApiPartido, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    
    # Basic prediction
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    
    # Additional predictions
    primer_tiempo_local = models.IntegerField(blank=True, null=True)
    primer_tiempo_visitante = models.IntegerField(blank=True, null=True)
    segundo_tiempo_local = models.IntegerField(blank=True, null=True)
    segundo_tiempo_visitante = models.IntegerField(blank=True, null=True)
    tarjetas_amarillas_total = models.IntegerField(blank=True, null=True)
    tarjetas_rojas_total = models.IntegerField(blank=True, null=True)
    corners_total = models.IntegerField(blank=True, null=True)
    
    # Status and points
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)
    
    # Optional custom scoring rules for this bet
    reglas_puntuacion = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"Apuesta Fútbol: {self.id_usuario.nombre_usuario} - {self.id_partido}"
    
    # En models.py, dentro de la clase ApuestaFutbol, después del __str__ (línea 349)

    def calcular_y_actualizar_puntos(self):
        """
        Calcula los puntos ganados en esta apuesta y actualiza el registro

        Returns:
            int: Puntos ganados
        """
        from .points_management.scoring import calcular_puntos_futbol, determinar_estado_apuesta
        
        # Verificar que el partido esté finalizado
        if self.id_partido.estado != PartidoStatus.FINALIZADO:
            return 0
        
        # Calcular puntos
        puntos = calcular_puntos_futbol(
            self.prediccion_local,
            self.prediccion_visitante,
            self.id_partido.goles_local,
            self.id_partido.goles_visitante,
            self.reglas_puntuacion
        )
        
        # Actualizar apuesta
        self.puntos_ganados = puntos
        self.estado = determinar_estado_apuesta(puntos)
        self.save()
        
        return puntos

    
    class Meta:
        db_table = 'apuestas_futbol'
        verbose_name_plural = 'Apuestas Fútbol'
        unique_together = (('id_usuario', 'id_partido', 'id_sala'),)
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_partido']),
            models.Index(fields=['estado']),
        ]

# Other sport models maintained for compatibility
class PartidoTenis(models.Model):
    id_partido_tenis = models.AutoField(primary_key=True)
    api_fixture_id = models.IntegerField(unique=True, blank=True, null=True)
    id_liga = models.ForeignKey(ApiLiga, on_delete=models.CASCADE, db_column='id_liga', blank=True, null=True)
    temporada = models.CharField(max_length=10, blank=True, null=True)
    
    # Players
    jugador_local = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='partidos_tenis_local')
    jugador_visitante = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='partidos_tenis_visitante')
    
    # Scores
    sets_local = models.IntegerField(default=0)
    sets_visitante = models.IntegerField(default=0)
    
    # Set details
    set1_local = models.IntegerField(blank=True, null=True)
    set1_visitante = models.IntegerField(blank=True, null=True)
    set2_local = models.IntegerField(blank=True, null=True)
    set2_visitante = models.IntegerField(blank=True, null=True)
    set3_local = models.IntegerField(blank=True, null=True)
    set3_visitante = models.IntegerField(blank=True, null=True)
    set4_local = models.IntegerField(blank=True, null=True)
    set4_visitante = models.IntegerField(blank=True, null=True)
    set5_local = models.IntegerField(blank=True, null=True)
    set5_visitante = models.IntegerField(blank=True, null=True)
    
    # Additional stats
    aces_local = models.IntegerField(blank=True, null=True)
    aces_visitante = models.IntegerField(blank=True, null=True)
    dobles_faltas_local = models.IntegerField(blank=True, null=True)
    dobles_faltas_visitante = models.IntegerField(blank=True, null=True)
    
    # Status
    estado = models.CharField(max_length=20, choices=PartidoStatus.choices, default=PartidoStatus.PROGRAMADO)
    fecha = models.DateTimeField()
    id_venue = models.ForeignKey(ApiVenue, on_delete=models.SET_NULL, blank=True, null=True)
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.jugador_local.nombre} vs {self.jugador_visitante.nombre} ({self.fecha.strftime('%Y-%m-%d')})"
    
    class Meta:
        db_table = 'partidos_tenis'
        verbose_name = 'Partido de Tenis'
        verbose_name_plural = 'Partidos de Tenis'

class PartidoBaloncesto(models.Model):
    id_partido_baloncesto = models.AutoField(primary_key=True)
    api_fixture_id = models.IntegerField(unique=True, blank=True, null=True)
    id_liga = models.ForeignKey(ApiLiga, on_delete=models.CASCADE, db_column='id_liga', blank=True, null=True)
    temporada = models.CharField(max_length=10, blank=True, null=True)
    
    # Teams
    equipo_local = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE, related_name='partidos_baloncesto_local')
    equipo_visitante = models.ForeignKey(ApiEquipo, on_delete=models.CASCADE, related_name='partidos_baloncesto_visitante')
    
    # Scores
    puntos_local = models.IntegerField(blank=True, null=True)
    puntos_visitante = models.IntegerField(blank=True, null=True)
    
    # Quarter scores
    q1_local = models.IntegerField(blank=True, null=True)
    q1_visitante = models.IntegerField(blank=True, null=True)
    q2_local = models.IntegerField(blank=True, null=True)
    q2_visitante = models.IntegerField(blank=True, null=True)
    q3_local = models.IntegerField(blank=True, null=True)
    q3_visitante = models.IntegerField(blank=True, null=True)
    q4_local = models.IntegerField(blank=True, null=True)
    q4_visitante = models.IntegerField(blank=True, null=True)
    
    # Status
    estado = models.CharField(max_length=20, choices=PartidoStatus.choices, default=PartidoStatus.PROGRAMADO)
    fecha = models.DateTimeField()
    id_venue = models.ForeignKey(ApiVenue, on_delete=models.SET_NULL, blank=True, null=True)
    
    # Additional stats
    estadisticas = models.JSONField(blank=True, null=True)
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.equipo_local.nombre} vs {self.equipo_visitante.nombre} ({self.fecha.strftime('%Y-%m-%d')})"
    
    class Meta:
        db_table = 'partidos_baloncesto'
        verbose_name = 'Partido de Baloncesto'
        verbose_name_plural = 'Partidos de Baloncesto'

class CarreraF1(models.Model):
    id_carrera_f1 = models.AutoField(primary_key=True)
    api_fixture_id = models.IntegerField(unique=True, blank=True, null=True)
    id_liga = models.ForeignKey(ApiLiga, on_delete=models.CASCADE, db_column='id_liga', blank=True, null=True)
    temporada = models.CharField(max_length=10, blank=True, null=True)
    
    nombre_gp = models.CharField(max_length=100)
    fecha = models.DateTimeField()
    id_venue = models.ForeignKey(ApiVenue, on_delete=models.SET_NULL, blank=True, null=True)
    
    # Status
    estado = models.CharField(max_length=20, choices=PartidoStatus.choices, default=PartidoStatus.PROGRAMADO)
    
    # Results stored as JSON
    resultados = models.JSONField(blank=True, null=True)
    pilotos_puntos = models.JSONField(blank=True, null=True)
    vuelta_rapida = models.IntegerField(blank=True, null=True)  # ID del piloto
    
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"GP de {self.nombre_gp} ({self.fecha.strftime('%Y-%m-%d')})"
    
    class Meta:
        db_table = 'carreras_f1'
        verbose_name = 'Carrera de F1'
        verbose_name_plural = 'Carreras de F1'

# Apuestas for other sports
class ApuestaTenis(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(PartidoTenis, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    
    # Sets prediction
    prediccion_sets_local = models.IntegerField()
    prediccion_sets_visitante = models.IntegerField()
    
    # Optional detailed predictions
    prediccion_set1_local = models.IntegerField(blank=True, null=True)
    prediccion_set1_visitante = models.IntegerField(blank=True, null=True)
    prediccion_set2_local = models.IntegerField(blank=True, null=True)
    prediccion_set2_visitante = models.IntegerField(blank=True, null=True)
    prediccion_set3_local = models.IntegerField(blank=True, null=True)
    prediccion_set3_visitante = models.IntegerField(blank=True, null=True)
    
    # Status and points
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Apuesta Tenis: {self.id_usuario.nombre_usuario} - {self.id_partido}"
    
    class Meta:
        db_table = 'apuestas_tenis'
        verbose_name_plural = 'Apuestas Tenis'
        unique_together = (('id_usuario', 'id_partido', 'id_sala'),)
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_partido']),
            models.Index(fields=['estado']),
        ]

class ApuestaBaloncesto(models.Model):
    id_apuesta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_partido = models.ForeignKey(PartidoBaloncesto, on_delete=models.CASCADE, db_column='id_partido')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    
    # Points prediction
    prediccion_local = models.IntegerField()
    prediccion_visitante = models.IntegerField()
    
    # Optional quarter predictions
    prediccion_q1_local = models.IntegerField(blank=True, null=True)
    prediccion_q1_visitante = models.IntegerField(blank=True, null=True)
    prediccion_q2_local = models.IntegerField(blank=True, null=True)
    prediccion_q2_visitante = models.IntegerField(blank=True, null=True)
    
    # Status and points
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Apuesta Baloncesto: {self.id_usuario.nombre_usuario} - {self.id_partido}"
    
    class Meta:
        db_table = 'apuestas_baloncesto'
        verbose_name_plural = 'Apuestas Baloncesto'
        unique_together = (('id_usuario', 'id_partido', 'id_sala'),)
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
    
    # Top 3 predictions
    prediccion_p1 = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='apuestas_f1_p1')
    prediccion_p2 = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='apuestas_f1_p2', blank=True, null=True)
    prediccion_p3 = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='apuestas_f1_p3', blank=True, null=True)
    
    # Optional additional predictions
    prediccion_vuelta_rapida = models.ForeignKey(ApiJugador, on_delete=models.CASCADE, related_name='apuestas_f1_vuelta_rapida', blank=True, null=True)
    
    # Store additional position predictions as JSON
    predicciones_adicionales = models.JSONField(blank=True, null=True)
    
    # Status and points
    fecha_apuesta = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ApuestaStatus.choices, default=ApuestaStatus.PENDIENTE)
    puntos_ganados = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Apuesta F1: {self.id_usuario.nombre_usuario} - {self.id_carrera}"
    
    class Meta:
        db_table = 'apuestas_f1'
        verbose_name_plural = 'Apuestas F1'
        unique_together = (('id_usuario', 'id_carrera', 'id_sala'),)
        indexes = [
            models.Index(fields=['id_usuario', 'id_sala']),
            models.Index(fields=['id_carrera']),
            models.Index(fields=['estado']),
        ]

# Ranking and Chat models
class Ranking(models.Model):
    id_ranking = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala')
    puntos = models.IntegerField(default=0)
    posicion = models.IntegerField(blank=True, null=True)
    periodo = models.DateField()
    
    def __str__(self):
        return f"Ranking de {self.id_usuario.nombre_usuario} en {self.id_sala.nombre} ({self.periodo})"
    
    class Meta:
        db_table = 'ranking'
        unique_together = (('id_usuario', 'id_sala', 'periodo'),)
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
# [MermaidChart: b67144a3-89b0-4a02-8112-a740c05d5b93]
        ]


# =============================================================================
# CONFIGURACIÓN DE SALA - Filtros de Deportes, Ligas y Partidos
# =============================================================================

class SalaDeporte(models.Model):
    """Deportes habilitados para una sala"""
    id_sala_deporte = models.AutoField(primary_key=True)
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala', related_name='deportes_habilitados')
    id_deporte = models.ForeignKey(Deporte, on_delete=models.CASCADE, db_column='id_deporte')
    fecha_activacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_sala.nombre} - {self.id_deporte.nombre}"

    class Meta:
        db_table = 'sala_deporte'
        unique_together = (('id_sala', 'id_deporte'),)
        verbose_name = 'Deporte de Sala'
        verbose_name_plural = 'Deportes de Sala'


class SalaLiga(models.Model):
    """Ligas/Torneos habilitados para una sala"""
    id_sala_liga = models.AutoField(primary_key=True)
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala', related_name='ligas_habilitadas')
    id_liga = models.ForeignKey(ApiLiga, on_delete=models.CASCADE, db_column='id_liga')
    fecha_activacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_sala.nombre} - {self.id_liga.nombre}"

    class Meta:
        db_table = 'sala_liga'
        unique_together = (('id_sala', 'id_liga'),)
        verbose_name = 'Liga de Sala'
        verbose_name_plural = 'Ligas de Sala'
        indexes = [
            models.Index(fields=['id_sala']),
            models.Index(fields=['id_liga']),
        ]


class SalaPartido(models.Model):
    """Partidos individuales habilitados manualmente por el administrador"""
    id_sala_partido = models.AutoField(primary_key=True)
    id_sala = models.ForeignKey(Sala, on_delete=models.CASCADE, db_column='id_sala', related_name='partidos_habilitados')
    id_partido = models.ForeignKey(ApiPartido, on_delete=models.CASCADE, db_column='id_partido')
    fecha_activacion = models.DateTimeField(auto_now_add=True)
    agregado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, db_column='agregado_por')

    def __str__(self):
        return f"{self.id_sala.nombre} - {self.id_partido}"

    class Meta:
        db_table = 'sala_partido'
        unique_together = (('id_sala', 'id_partido'),)
        verbose_name = 'Partido de Sala'
        verbose_name_plural = 'Partidos de Sala'
        indexes = [
            models.Index(fields=['id_sala']),
            models.Index(fields=['id_partido']),
        ]


class EmailVerificationToken(models.Model):
    """Tokens for email verification"""
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Verification token for {self.usuario.nombre_usuario}"

    class Meta:
        db_table = 'email_verification_token'


class PasswordResetToken(models.Model):
    """Tokens for password reset"""
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Reset token for {self.usuario.nombre_usuario}"

    class Meta:
        db_table = 'password_reset_token'