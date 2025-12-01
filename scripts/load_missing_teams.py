#!/usr/bin/env python
"""
Script para cargar equipos faltantes de La Liga usando SofaScore
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')
django.setup()

import requests
from bets.models import ApiEquipo, ApiPais, ApiLiga, Deporte

# SofaScore configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def main():
    # Get La Liga from DB
    try:
        liga = ApiLiga.objects.get(nombre='La Liga')
        print(f"✅ Liga encontrada: {liga.nombre}")
    except ApiLiga.DoesNotExist:
        print("❌ Liga 'La Liga' no encontrada en BD")
        return

    # Get Spain
    try:
        spain = ApiPais.objects.get(nombre='Spain')
        print(f"✅ País encontrado: {spain.nombre}")
    except ApiPais.DoesNotExist:
        print("❌ País 'Spain' no encontrado en BD")
        return

    # Get football deporte
    try:
        futbol = Deporte.objects.get(nombre='Fútbol')
        print(f"✅ Deporte encontrado: {futbol.nombre}")
    except Deporte.DoesNotExist:
        print("❌ Deporte 'Fútbol' no encontrado en BD")
        return

    # Teams to add manually with their SofaScore data
    teams_data = [
        {
            'nombre': 'Girona FC',
            'nombre_corto': 'Girona',
            'api_id': 2988,  # SofaScore ID
            'fundado': 1930,
            'logo_url': 'https://api.sofascore.app/api/v1/team/2988/image',
        },
        {
            'nombre': 'Espanyol',
            'nombre_corto': 'Espanyol',
            'api_id': 2836,  # SofaScore ID
            'fundado': 1900,
            'logo_url': 'https://api.sofascore.app/api/v1/team/2836/image',
        },
        {
            'nombre': 'Leganés',
            'nombre_corto': 'Leganés',
            'api_id': 48659,  # SofaScore ID
            'fundado': 1928,
            'logo_url': 'https://api.sofascore.app/api/v1/team/48659/image',
        },
        {
            'nombre': 'Real Valladolid',
            'nombre_corto': 'Valladolid',
            'api_id': 2851,  # SofaScore ID
            'fundado': 1928,
            'logo_url': 'https://api.sofascore.app/api/v1/team/2851/image',
        },
    ]

    for team_info in teams_data:
        print(f"\n{'='*60}")
        print(f"🔍 Cargando equipo: {team_info['nombre']}")
        print(f"{'='*60}")

        # Check if team already exists by name
        existing = ApiEquipo.objects.filter(nombre__iexact=team_info['nombre']).first()

        if existing:
            print(f"   ✅ Equipo ya existía en BD: {existing.nombre}")
            continue

        # Create team
        equipo = ApiEquipo.objects.create(
            nombre=team_info['nombre'],
            nombre_corto=team_info['nombre_corto'],
            logo_url=team_info['logo_url'],
            id_pais=spain,
            fundado=team_info['fundado'],
            tipo='Club',
            api_id=team_info['api_id'],
            id_deporte=futbol,
        )

        print(f"   🆕 Equipo CREADO: {equipo.nombre}")
        print(f"      - Nombre corto: {equipo.nombre_corto}")
        print(f"      - Fundado: {equipo.fundado}")

    print(f"\n{'='*60}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*60}")

    # Verify teams in DB
    print(f"\n{'='*60}")
    print("📊 VERIFICACIÓN DE EQUIPOS EN BD")
    print(f"{'='*60}")

    for team_info in teams_data:
        team = ApiEquipo.objects.filter(nombre__iexact=team_info['nombre']).first()
        if team:
            print(f"✅ {team.nombre} (ID: {team.id_equipo})")
        else:
            print(f"❌ {team_info['nombre']} NO ENCONTRADO")

if __name__ == '__main__':
    main()
