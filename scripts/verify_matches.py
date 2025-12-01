#!/usr/bin/env python
"""
Verificar partidos de La Liga en BD
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')
django.setup()

from bets.models import ApiPartido, ApiLiga

# Get La Liga
liga = ApiLiga.objects.get(nombre='La Liga')

# Get all matches
partidos = ApiPartido.objects.filter(id_liga=liga).order_by('-fecha')

print(f"\n{'='*80}")
print(f"📊 PARTIDOS DE LA LIGA EN BASE DE DATOS")
print(f"{'='*80}\n")

for p in partidos:
    print(f"ID: {p.id_partido} | {p.equipo_local.nombre} {p.goles_local or '-'} - {p.goles_visitante or '-'} {p.equipo_visitante.nombre}")
    print(f"   Fecha: {p.fecha} | Estado: {p.estado} | API ID: {p.api_fixture_id}")
    print()

print(f"{'='*80}")
print(f"✅ Total: {partidos.count()} partidos")
print(f"{'='*80}\n")
