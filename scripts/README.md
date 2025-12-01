# 📂 Scripts de Utilidad

Esta carpeta contiene scripts standalone para tareas específicas de mantenimiento y debugging.

## 📋 Scripts Disponibles

### `check_incomplete_scores.py`
**Propósito:** Encuentra partidos finalizados con marcadores incompletos y los actualiza desde SofaScore.

**Uso:**
```bash
# Con Docker
docker-compose exec web python scripts/check_incomplete_scores.py

# Sin Docker (local)
cd bet_project
python scripts/check_incomplete_scores.py
```

**Qué hace:**
- Busca partidos con `estado='finalizado'` pero `goles_local=None` o `goles_visitante=None`
- Por cada partido, obtiene el marcador desde SofaScore API
- Actualiza los marcadores en la BD

---

### `load_missing_teams.py`
**Propósito:** Carga equipos específicos que faltan en la BD usando IDs de SofaScore.

**Uso:**
```bash
# Con Docker
docker-compose exec web python scripts/load_missing_teams.py

# Sin Docker (local)
cd bet_project
python scripts/load_missing_teams.py
```

**Qué hace:**
- Carga equipos hardcodeados (Girona FC, Espanyol, Leganés, Real Valladolid)
- Útil cuando API-Football no tiene equipos recién ascendidos
- Usa IDs y datos directos de SofaScore

**Nota:** Este script tiene equipos hardcodeados. Modifícalo para agregar más equipos.

---

### `verify_matches.py`
**Propósito:** Lista todos los partidos de La Liga en la BD para verificación rápida.

**Uso:**
```bash
# Con Docker
docker-compose exec web python scripts/verify_matches.py

# Sin Docker (local)
cd bet_project
python scripts/verify_matches.py
```

**Salida:**
```
========================================================================
📊 PARTIDOS DE LA LIGA EN BASE DE DATOS
========================================================================

ID: 1 | Real Madrid 2 - 1 Barcelona
   Fecha: 2024-10-26 15:00:00 | Estado: finalizado | API ID: 12345678

ID: 2 | Atletico Madrid - - Sevilla
   Fecha: 2024-11-02 20:00:00 | Estado: programado | API ID: 12345679

========================================================================
✅ Total: 152 partidos
========================================================================
```

---

### `verify_scores_detailed.py`
**Propósito:** Análisis detallado de tipos de datos en marcadores (debugging).

**Uso:**
```bash
# Con Docker
docker-compose exec web python scripts/verify_scores_detailed.py

# Sin Docker (local)
cd bet_project
python scripts/verify_scores_detailed.py
```

**Salida:**
```
================================================================================
📊 ANÁLISIS DETALLADO DE MARCADORES
================================================================================

ID: 1 | Real Madrid 2 - 1 Barcelona
   goles_local: 2 (type: int)
   goles_visitante: 1 (type: int)
   Estado: finalizado

ID: 2 | Atletico Madrid None - None Sevilla
   goles_local: None (type: NoneType)
   goles_visitante: None (type: NoneType)
   Estado: programado

================================================================================
```

**Útil para:** Identificar problemas con `None` vs `0` vs `NULL` en marcadores.

---

## 🆚 Scripts vs Comandos Django

### Cuándo usar Scripts (esta carpeta):
- ✅ Tareas puntuales de mantenimiento
- ✅ Debugging rápido
- ✅ Correcciones one-time
- ✅ No requieren integración con Django admin

### Cuándo usar Comandos Django:
- ✅ Tareas recurrentes (diarias, semanales)
- ✅ Operaciones que requieren acceso completo a ORM
- ✅ Integración con cron jobs
- ✅ Comandos que se ejecutarán en producción

**Comandos Django disponibles:**
```bash
# Con Docker
docker-compose exec web python manage.py help

# Comandos de SofaScore
docker-compose exec web python manage.py load_sofascore_laliga        # Carga inicial
docker-compose exec web python manage.py update_sofascore_football    # Actualización diaria

# Comandos de API-Football (backup)
docker-compose exec web python manage.py fetch_api_football           # Carga desde API-Football
docker-compose exec web python manage.py check_api_status             # Estado de peticiones
```

---

## 🔧 Convertir Script a Comando Django

Si un script se usa frecuentemente, conviértelo en comando Django:

1. Crear archivo en `bets/management/commands/nombre_comando.py`
2. Estructura básica:
```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Descripción del comando'

    def add_arguments(self, parser):
        # Agregar argumentos opcionales
        pass

    def handle(self, *args, **options):
        # Lógica del comando
        pass
```

3. Ejecutar:
```bash
python manage.py nombre_comando
```

---

## 📝 Notas

- Todos los scripts usan `django.setup()` para acceso a modelos
- Requieren estar en el directorio `bet_project` para ejecutarse
- Algunos scripts hacen peticiones a SofaScore API (respeta los delays)
- Los scripts NO están en Git ignore, son parte del proyecto

---

## 🚀 Ejemplos de Uso Común

### Completar marcadores faltantes:
```bash
docker-compose exec web python scripts/check_incomplete_scores.py
```

### Verificar datos antes de deploy:
```bash
docker-compose exec web python scripts/verify_matches.py
docker-compose exec web python scripts/verify_scores_detailed.py
```

### Cargar equipo específico:
```bash
# Editar scripts/load_missing_teams.py con los datos del equipo
docker-compose exec web python scripts/load_missing_teams.py
```
