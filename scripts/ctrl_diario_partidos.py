import os
import sys
from datetime import datetime

# 1. Configurar el entorno de Django de manera externa
# Reemplaza 'bet_project' por el nombre exacto de tu directorio de configuraciones si es diferente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')

import django
django.setup()

from django.utils import timezone
from bets.models import Partido

def main():
    ahora = timezone.now()
    
    # Buscar partidos cuya fecha programada ya pasó y cuyo estado no sea 'Finalizado'
    partidos_pendientes = Partido.objects.filter(
        fecha_partido__lte=ahora
    ).exclude(estado='Finalizado').order_by('fecha_partido')

    cantidad = partidos_pendientes.count()

    print("=" * 55)
    print("     ⚽ FRIENDLYBET - PANEL DE ACTUALIZACIÓN MANUAL ⚽     ")
    print("=" * 55)
    print(f"Hora actual del servidor: {ahora.strftime('%Y-%m-%d %H:%M')}")

    if cantidad == 0:
        print("\n🎉 ¡Al día! No tienes partidos pendientes por finalizar.")
        print("=" * 55)
        return

    print(f"\n⚠️ Se encontraron {cantidad} partido(s) finalizados cronológicamente sin marcador.")
    print("Presiona [Enter] en los goles si deseas saltar un partido para después.\n")
    print("-" * 55)

    actualizados = 0

    for idx, partido in enumerate(partidos_pendientes, 1):
        print(f"\n[{idx}/{cantidad}] 👉 {partido.local.nombre} vs {partido.visitante.nombre}")
        print(f"      🗓️  Fecha: {partido.fecha_partido.strftime('%Y-%m-%d %H:%M')} | ID: {partido.id}")
        
        goles_local = input(f"      ⚽ Goles para {partido.local.nombre}: ").strip()
        if goles_local == "":
            print("      ⏭️  Partido saltado.")
            continue

        goles_visitante = input(f"      ⚽ Goles para {partido.visitante.nombre}: ").strip()
        if goles_visitante == "":
            print("      ⏭️  Partido saltado.")
            continue

        try:
            # Asignar datos reales
            partido.goles_local = int(goles_local)
            partido.goles_visitante = int(goles_visitante)
            partido.estado = 'Finalizado'
            
            # Al guardar, Django ejecuta automáticamente las señales e inyecta los puntos a los usuarios
            partido.save()
            
            actualizados += 1
            print(f"      ✅ ¡Guardado con éxito! Marcador registrado: {goles_local} - {goles_visitante}")
        except ValueError:
            print("      ❌ Error: Ingresa solo números enteros. Partido omitido.")

    print("\n" + "=" * 55)
    print(f" Fin de la revisión. Se actualizaron {actualizados} partidos.")
    print("=" * 55)

if __name__ == '__main__':
    main()