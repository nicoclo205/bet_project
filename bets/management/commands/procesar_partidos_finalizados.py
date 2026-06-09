"""
Comando Django para procesar partidos finalizados y calcular puntos de apuestas.

Este comando:
1. Busca partidos con estado 'finalizado' que tengan apuestas pendientes
2. Calcula los puntos de cada apuesta según el resultado
3. Actualiza el estado de las apuestas (ganada/perdida)
4. Actualiza los puntos totales de cada usuario
5. Actualiza el ranking de las salas

Uso:
    # Procesar todos los partidos finalizados con apuestas pendientes
    python manage.py procesar_partidos_finalizados

    # Procesar un partido específico
    python manage.py procesar_partidos_finalizados --partido-id 123

    # Procesar solo partidos de una sala específica
    python manage.py procesar_partidos_finalizados --sala-id 5

    # Modo dry-run (simular sin guardar cambios)
    python manage.py procesar_partidos_finalizados --dry-run
"""

from django.core.management.base import BaseCommand
from django.db.models import Q, Sum
from django.db import models
from django.utils import timezone
from bets.models import (
    ApiPartido, ApuestaFutbol, Usuario, Ranking, Sala,
    PartidoStatus, ApuestaStatus
)


class Command(BaseCommand):
    help = 'Procesa partidos finalizados y calcula puntos de apuestas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--partido-id',
            type=int,
            help='ID de un partido específico a procesar',
        )
        parser.add_argument(
            '--sala-id',
            type=int,
            help='ID de sala para filtrar apuestas',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin guardar cambios en la base de datos',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada de cada apuesta procesada',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("⚽ PROCESAMIENTO DE PARTIDOS FINALIZADOS"))
        if self.dry_run:
            self.stdout.write(self.style.WARNING("🔍 MODO DRY-RUN (sin guardar cambios)"))
        self.stdout.write("="*80 + "\n")

        # Estadísticas
        self.stats = {
            'partidos_procesados': 0,
            'apuestas_procesadas': 0,
            'apuestas_ganadas': 0,
            'apuestas_perdidas': 0,
            'usuarios_actualizados': 0,
            'rankings_actualizados': 0,
            'errores': 0,
        }

        # Buscar partidos a procesar
        partidos = self.get_partidos_a_procesar(
            options.get('partido_id'),
            options.get('sala_id')
        )

        if not partidos.exists():
            self.stdout.write(self.style.WARNING(
                "⚠️  No hay partidos finalizados con apuestas pendientes\n"
            ))
            return

        self.stdout.write(f"📊 Partidos a procesar: {partidos.count()}\n")

        # Procesar cada partido
        for partido in partidos:
            self.procesar_partido(partido, options.get('sala_id'))

        # Mostrar resumen
        self.mostrar_resumen()

    def get_partidos_a_procesar(self, partido_id, sala_id):
        """
        Obtiene los partidos finalizados que tienen apuestas pendientes
        """
        # Filtro base: partidos finalizados
        query = Q(estado=PartidoStatus.FINALIZADO)

        # Filtro adicional: que tengan marcadores
        query &= Q(goles_local__isnull=False, goles_visitante__isnull=False)

        # Si se especificó un partido concreto
        if partido_id:
            query &= Q(id_partido=partido_id)

        # Obtener partidos
        partidos = ApiPartido.objects.filter(query).select_related(
            'equipo_local',
            'equipo_visitante',
            'id_liga'
        )

        # Filtrar solo los que tengan apuestas pendientes
        partidos_con_apuestas_pendientes = []
        for partido in partidos:
            apuestas_query = Q(id_partido=partido, estado=ApuestaStatus.PENDIENTE)
            if sala_id:
                apuestas_query &= Q(id_sala_id=sala_id)

            if ApuestaFutbol.objects.filter(apuestas_query).exists():
                partidos_con_apuestas_pendientes.append(partido.id_partido)

        return ApiPartido.objects.filter(id_partido__in=partidos_con_apuestas_pendientes)

    def procesar_partido(self, partido, sala_id_filter):
        """
        Procesa todas las apuestas de un partido finalizado
        """
        self.stdout.write(self.style.WARNING(
            f"\n📅 Procesando: {partido.equipo_local.nombre} {partido.goles_local} - "
            f"{partido.goles_visitante} {partido.equipo_visitante.nombre}"
        ))

        # Buscar apuestas pendientes de este partido
        apuestas_query = Q(
            id_partido=partido,
            estado=ApuestaStatus.PENDIENTE
        )
        if sala_id_filter:
            apuestas_query &= Q(id_sala_id=sala_id_filter)

        apuestas = ApuestaFutbol.objects.filter(apuestas_query).select_related(
            'id_usuario',
            'id_sala',
            'id_partido'
        )

        if not apuestas.exists():
            self.stdout.write("   Sin apuestas pendientes")
            return

        self.stdout.write(f"   Apuestas a procesar: {apuestas.count()}")

        # Diccionario para acumular puntos por usuario
        puntos_por_usuario = {}
        salas_afectadas = set()

        # Procesar cada apuesta
        for apuesta in apuestas:
            try:
                # Calcular puntos
                puntos = apuesta.calcular_y_actualizar_puntos()

                if self.verbose:
                    self.stdout.write(
                        f"      {apuesta.id_usuario.nombre_usuario}: "
                        f"Predicción {apuesta.prediccion_local}-{apuesta.prediccion_visitante} "
                        f"→ {puntos} puntos ({apuesta.estado})"
                    )

                # Acumular estadísticas
                self.stats['apuestas_procesadas'] += 1
                if apuesta.estado == ApuestaStatus.GANADA:
                    self.stats['apuestas_ganadas'] += 1
                else:
                    self.stats['apuestas_perdidas'] += 1

                # Acumular puntos por usuario y sala
                if not self.dry_run:
                    usuario_id = apuesta.id_usuario.id_usuario
                    if usuario_id not in puntos_por_usuario:
                        puntos_por_usuario[usuario_id] = {
                            'usuario': apuesta.id_usuario,
                            'puntos': 0,
                            'salas': set()
                        }
                    puntos_por_usuario[usuario_id]['puntos'] += puntos
                    puntos_por_usuario[usuario_id]['salas'].add(apuesta.id_sala.id_sala)
                    salas_afectadas.add(apuesta.id_sala.id_sala)

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"      ❌ Error procesando apuesta {apuesta.id_apuesta}: {e}"
                ))
                self.stats['errores'] += 1

        # Actualizar puntos totales de usuarios
        if not self.dry_run:
            for usuario_id, data in puntos_por_usuario.items():
                usuario = data['usuario']
                puntos = data['puntos']

                usuario.puntos_totales += puntos
                usuario.save()

                self.stats['usuarios_actualizados'] += 1

                if self.verbose:
                    self.stdout.write(
                        f"   ✅ Usuario {usuario.nombre_usuario}: "
                        f"+{puntos} puntos (Total: {usuario.puntos_totales})"
                    )

            # Actualizar rankings de las salas afectadas
            for sala_id in salas_afectadas:
                self.actualizar_ranking_sala(sala_id)

        self.stats['partidos_procesados'] += 1

    def actualizar_ranking_sala(self, sala_id):
        """
        Actualiza el ranking de una sala específica
        """
        from datetime import date
        from bets.models import UsuarioSala

        try:
            sala = Sala.objects.get(id_sala=sala_id)
            periodo_actual = date.today()

            # Obtener todos los miembros de la sala
            miembros = UsuarioSala.objects.filter(id_sala=sala).select_related('id_usuario')

            # Crear o actualizar ranking para cada miembro
            for miembro in miembros:
                usuario = miembro.id_usuario

                # Calcular puntos totales del usuario en esta sala
                puntos_sala = ApuestaFutbol.objects.filter(
                    id_usuario=usuario,
                    id_sala=sala,
                    estado=ApuestaStatus.GANADA
                ).aggregate(total=models.Sum('puntos_ganados'))['total'] or 0

                # Crear o actualizar registro de ranking
                ranking, created = Ranking.objects.update_or_create(
                    id_usuario=usuario,
                    id_sala=sala,
                    periodo=periodo_actual,
                    defaults={'puntos': puntos_sala}
                )

            # Calcular posiciones ordenando por puntos
            rankings = Ranking.objects.filter(
                id_sala=sala,
                periodo=periodo_actual
            ).order_by('-puntos')

            posicion = 1
            for ranking in rankings:
                ranking.posicion = posicion
                ranking.save()
                posicion += 1

            self.stats['rankings_actualizados'] += 1

            if self.verbose:
                self.stdout.write(
                    f"   📊 Ranking actualizado para sala: {sala.nombre}"
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"   ❌ Error actualizando ranking de sala {sala_id}: {e}"
            ))
            self.stats['errores'] += 1

    def mostrar_resumen(self):
        """
        Muestra el resumen de la ejecución
        """
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ PROCESAMIENTO COMPLETADO"))
        self.stdout.write("="*80 + "\n")

        self.stdout.write(f"⚽ Partidos procesados: {self.stats['partidos_procesados']}")
        self.stdout.write(f"🎲 Apuestas procesadas: {self.stats['apuestas_procesadas']}")
        self.stdout.write(f"   ✅ Ganadas: {self.stats['apuestas_ganadas']}")
        self.stdout.write(f"   ❌ Perdidas: {self.stats['apuestas_perdidas']}")
        self.stdout.write(f"👥 Usuarios actualizados: {self.stats['usuarios_actualizados']}")
        self.stdout.write(f"📊 Rankings actualizados: {self.stats['rankings_actualizados']}")

        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(
                f"⚠️  Errores encontrados: {self.stats['errores']}"
            ))

        self.stdout.write("")
