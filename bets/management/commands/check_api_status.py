# bets/management/commands/check_api_status.py
"""
Comando para verificar el estado de las peticiones a la API de Football.
Muestra cuántas peticiones se han usado hoy y cuántas quedan disponibles.
"""
from django.core.management.base import BaseCommand
from bets.utils.api_counter import get_stats, DAILY_LIMIT
import json


class Command(BaseCommand):
    help = 'Muestra el estado actual de las peticiones a API-Football'

    def handle(self, *args, **options):
        stats = get_stats()

        # Título
        self.stdout.write(
            f"\n{'='*60}\n"
            f"📊 ESTADO DE PETICIONES A API-FOOTBALL\n"
            f"{'='*60}\n"
        )

        # Fecha
        self.stdout.write(f"📅 Fecha: {stats['today']}\n")

        # Estadísticas principales
        self.stdout.write(
            f"   Peticiones usadas:    {stats['used']}/{stats['limit']}\n"
            f"   Peticiones restantes: {stats['remaining']}\n"
            f"   Porcentaje usado:     {stats['percentage_used']}%\n"
        )

        # Barra de progreso visual
        used_bars = int(stats['percentage_used'] / 5)  # 20 barras máximo
        remaining_bars = 20 - used_bars
        progress_bar = '█' * used_bars + '░' * remaining_bars

        # Color según el porcentaje
        if stats['percentage_used'] >= 90:
            bar_style = self.style.ERROR
            status = "🔴 CRÍTICO"
        elif stats['percentage_used'] >= 70:
            bar_style = self.style.WARNING
            status = "🟠 ALTO"
        elif stats['percentage_used'] >= 50:
            bar_style = lambda x: self.style.WARNING(x)
            status = "🟡 MEDIO"
        else:
            bar_style = self.style.SUCCESS
            status = "🟢 NORMAL"

        self.stdout.write(
            f"\n   [{bar_style(progress_bar)}] {stats['percentage_used']}%\n"
        )

        # Estado
        self.stdout.write(f"   Estado: {status}\n")

        # Recomendaciones
        self.stdout.write(f"\n{'='*60}\n")

        if stats['remaining'] == 0:
            self.stdout.write(self.style.ERROR(
                "🚫 LÍMITE ALCANZADO\n"
                "   No puedes hacer más peticiones hasta mañana.\n"
                "   El contador se resetea automáticamente a las 00:00.\n"
            ))
        elif stats['remaining'] <= 5:
            self.stdout.write(self.style.ERROR(
                "🔴 ALERTA CRÍTICA\n"
                f"   Solo quedan {stats['remaining']} peticiones.\n"
                "   Evita ejecutar comandos que consuman la API.\n"
            ))
        elif stats['remaining'] <= 10:
            self.stdout.write(self.style.WARNING(
                "🟠 ADVERTENCIA\n"
                f"   Solo quedan {stats['remaining']} peticiones.\n"
                "   Usa comandos específicos con parámetros --leagues.\n"
            ))
        elif stats['remaining'] <= 20:
            self.stdout.write(self.style.WARNING(
                "🟡 ATENCIÓN\n"
                f"   Quedan {stats['remaining']} peticiones.\n"
                "   Considera ejecutar solo lo necesario.\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "✅ ESTADO ÓPTIMO\n"
                f"   Tienes {stats['remaining']} peticiones disponibles.\n"
                "   Puedes ejecutar comandos normalmente.\n"
            ))

        # Estimaciones
        self.stdout.write(f"\n{'='*60}\n")
        self.stdout.write("📋 ESTIMACIONES DE PETICIONES POR COMANDO:\n")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(
            "   fetch_api_football (completo):     ~26 peticiones\n"
            "   fetch_api_football (solo ligas):   ~10 peticiones\n"
            "   fetch_api_football (1 liga):       ~2 peticiones\n"
            "   fetch_api_football (+ fixtures):   +5 peticiones\n"
        )

        # Proyección
        if stats['remaining'] >= 26:
            executions = stats['remaining'] // 26
            self.stdout.write(
                f"\n   Puedes ejecutar el comando completo ~{executions} veces más hoy.\n"
            )
        elif stats['remaining'] >= 10:
            self.stdout.write(
                f"\n   Puedes cargar {stats['remaining'] // 2} ligas más hoy.\n"
            )

        self.stdout.write(f"{'='*60}\n")

        # Información adicional
        self.stdout.write(
            "\n💡 CONSEJOS:\n"
            "   - El contador se resetea automáticamente cada día a las 00:00\n"
            "   - Para ver este estado en cualquier momento: python manage.py check_api_status\n"
            "   - Para aumentar el límite: https://www.api-football.com/pricing\n"
            "\n"
        )
