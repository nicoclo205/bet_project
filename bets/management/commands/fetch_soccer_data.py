import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from bets.models import ApiPais, ApiEquipo, ApiLiga, ApiPartido  # adjust app name if needed
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY", "YOUR_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

class Command(BaseCommand):
    help = "Fetch teams, competitions, and matches from API-Football"

    def add_arguments(self, parser):
        parser.add_argument("--league", type=int, help="League ID from API-Football", required=True)
        parser.add_argument("--season", type=int, help="Season year (e.g. 2024)", required=True)

    def handle(self, *args, **options):
        league_id = options["league"]
        season = options["season"]

        self.stdout.write(self.style.SUCCESS(f"Fetching data for league {league_id}, season {season}"))

        # Fetch Teams
        teams = self.fetch_api("teams", {"league": league_id, "season": season})
        self.save_teams(teams)

        # Fetch Competitions (we map league -> Competencia)
        leagues = self.fetch_api("leagues", {"id": league_id, "season": season})
        self.save_competitions(leagues)

        # Fetch Matches
        matches = self.fetch_api("fixtures", {"league": league_id, "season": season})
        self.save_matches(matches)

    def fetch_api(self, endpoint, params):
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            self.stderr.write(self.style.ERROR(f"Error fetching {endpoint}: {response.text}"))
            return []
        data = response.json()
        return data.get("response", [])

    def find_country(self, country_name, country_code):
        """Find country in ApiPais table by ISO2 code first, then by English name."""
        if country_code:
            p = ApiPais.objects.filter(codigo__iexact=country_code).first()
            if p:
                return p
        if country_name:
            p = ApiPais.objects.filter(nombre__iexact=country_name).first()
            if p:
                return p
        return None

    def save_teams(self, teams_data):
        for item in teams_data:
            team_info = item.get("team", {})
            country_name = team_info.get("country")
            # API-Football does not provide ISO2 for clubs directly
            country_code = None  

            pais = self.find_country(country_name, country_code)

            if not pais:
                self.stdout.write(self.style.WARNING(
                    f"No country found for team {team_info.get('name')} ({country_name})"
                ))

            ApiEquipo.objects.update_or_create(
                api_team_id=team_info.get("id"),
                defaults={
                    "nombre": team_info.get("name"),
                    "logo": team_info.get("logo"),
                    "id_pais": pais
                }
            )
        self.stdout.write(self.style.SUCCESS("Teams updated."))

    def save_competitions(self, leagues_data):
        for item in leagues_data:
            league_info = item.get("league", {})
            country_info = item.get("country", {})

            pais = self.find_country(country_info.get("name"), country_info.get("code"))

            ApiLiga.objects.update_or_create(
                api_league_id=item.get("league", {}).get("id"),
                defaults={
                    "nombre": league_info.get("name"),
                    "id_pais": pais,
                    "logo": league_info.get("logo"),
                    "tipo": league_info.get("type", "League")
                }
            )
        self.stdout.write(self.style.SUCCESS("Competitions updated."))

    def save_matches(self, matches_data):
        for item in matches_data:
            fixture = item.get("fixture", {})
            league_info = item.get("league", {})
            teams_info = item.get("teams", {})

            # Get competition FK
            liga = ApiLiga.objects.filter(api_league_id=league_info.get("id")).first()

            # Get teams FK
            home_team = ApiEquipo.objects.filter(api_team_id=teams_info.get("home", {}).get("id")).first()
            away_team = ApiEquipo.objects.filter(api_team_id=teams_info.get("away", {}).get("id")).first()

            # Parse date
            fecha = fixture.get("date")
            fecha_dt = datetime.fromisoformat(fecha.replace("Z", "+00:00")) if fecha else None

            ApiPartido.objects.update_or_create(
                api_fixture_id=fixture.get("id"),
                defaults={
                    "id_liga": liga,
                    "equipo_local": home_team,
                    "equipo_visitante": away_team,
                    "fecha": fecha_dt,
                    "resultado_local": item.get("goals", {}).get("home"),
                    "resultado_visitante": item.get("goals", {}).get("away"),
                    "estado": fixture.get("status", {}).get("long")
                }
            )
        self.stdout.write(self.style.SUCCESS("Matches updated."))

        # curl -H "x-apisports-key: 2e2aaefb65f0bbd2fcdb3f2d58a7296e" "https://v3.football.api-sports.io/teams?league=39&season=2024"

