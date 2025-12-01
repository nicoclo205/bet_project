#!/usr/bin/env python
"""
Verificar marcadores en detalle
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

print("\n" + "="*80)
print("📊 ANÁLISIS DETALLADO DE MARCADORES")
print("="*80 + "\n")

for p in partidos:
    local_str = str(p.goles_local) if p.goles_local is not None else "None"
    visit_str = str(p.goles_visitante) if p.goles_visitante is not None else "None"

    print(f"ID: {p.id_partido} | {p.equipo_local.nombre} {local_str} - {visit_str} {p.equipo_visitante.nombre}")
    print(f"   goles_local: {p.goles_local} (type: {type(p.goles_local).__name__})")
    print(f"   goles_visitante: {p.goles_visitante} (type: {type(p.goles_visitante).__name__})")
    print(f"   Estado: {p.estado}")
    print()

print("="*80 + "\n")
