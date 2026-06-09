#!/usr/bin/env python
"""
Verificar y corregir marcadores incompletos
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')
django.setup()

from bets.models import ApiPartido, PartidoStatus

print("\n" + "="*80)
print("🔍 BUSCANDO PARTIDOS FINALIZADOS CON MARCADORES INCOMPLETOS")
print("="*80 + "\n")

# Buscar partidos finalizados con marcadores None
partidos_incompletos = ApiPartido.objects.filter(
    estado=PartidoStatus.FINALIZADO
).filter(
    goles_local__isnull=True
) | ApiPartido.objects.filter(
    estado=PartidoStatus.FINALIZADO
).filter(
    goles_visitante__isnull=True
)

print(f"Total partidos con marcadores incompletos: {partidos_incompletos.count()}\n")

for partido in partidos_incompletos:
    print(f"ID: {partido.id_partido} | API ID: {partido.api_fixture_id}")
    print(f"   {partido.equipo_local.nombre} {partido.goles_local} - {partido.goles_visitante} {partido.equipo_visitante.nombre}")
    print(f"   Fecha: {partido.fecha}")
    print(f"   Estado: {partido.estado}")
    print()

# Intentar obtener marcadores de SofaScore para estos partidos
if partidos_incompletos.exists():
    print("\n" + "="*80)
    print("🔧 INTENTANDO OBTENER MARCADORES DESDE SOFASCORE")
    print("="*80 + "\n")

    import requests
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    for partido in partidos_incompletos:
        if partido.api_fixture_id:
            url = f"https://api.sofascore.com/api/v1/event/{partido.api_fixture_id}"

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    evento = data.get('event', {})

                    home_score = evento.get('homeScore', {})
                    away_score = evento.get('awayScore', {})

                    goles_local = home_score.get('current')
                    goles_visitante = away_score.get('current')

                    print(f"✅ Partido ID {partido.id_partido} (API ID: {partido.api_fixture_id})")
                    print(f"   Score obtenido: {goles_local} - {goles_visitante}")

                    if goles_local is not None and goles_visitante is not None:
                        partido.goles_local = goles_local
                        partido.goles_visitante = goles_visitante
                        partido.save()
                        print(f"   ✅ Marcador actualizado: {partido.equipo_local.nombre} {goles_local} - {goles_visitante} {partido.equipo_visitante.nombre}")
                    else:
                        print(f"   ⚠️ Marcador aún incompleto en API")
                else:
                    print(f"❌ Error {response.status_code} para partido {partido.id_partido}")

            except Exception as e:
                print(f"❌ Error obteniendo datos: {e}")

            print()

print("\n" + "="*80)
print("✅ PROCESO COMPLETADO")
print("="*80 + "\n")
