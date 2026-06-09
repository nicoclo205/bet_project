# 🐳 GUÍA DE COMANDOS DOCKER - SOFASCORE SCRAPING

Guía completa de comandos Docker para scraping de La Liga usando SofaScore.

---

## 🚀 INICIO RÁPIDO

### 1. Levantar contenedores
```bash
docker-compose up -d
```

### 2. Verificar que estén corriendo
```bash
docker-compose ps
```

Deberías ver:
- `bet_mysql` (corriendo)
- `bet_django` (corriendo)

---

## 📥 CARGA INICIAL (UNA SOLA VEZ)

### Paso 1: Cargar países
```bash
docker-compose exec web python Populate_countries.py
```

**Resultado:** 139 países cargados en BD

---

### Paso 2: Crear deporte "Fútbol"
```bash
# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Ir a http://localhost:8000/admin
# Login y crear un registro en "Deportes":
# - nombre: Fútbol
# - descripcion: Fútbol/Soccer
# - api_sport_id: 1
```

---

### Paso 3: Cargar La Liga completa
```bash
# Opción A: Carga completa (equipos + todos los partidos)
docker-compose exec web python manage.py load_sofascore_laliga

# Opción B: Solo equipos (20 equipos)
docker-compose exec web python manage.py load_sofascore_laliga --skip-fixtures

# Opción C: Solo una jornada para probar (10 partidos)
docker-compose exec web python manage.py load_sofascore_laliga --round 15
```

**⏱️ Tiempo estimado:**
- Equipos: 2-3 minutos
- Fixtures completos (38 jornadas): 10-15 minutos
- Una jornada: 1 minuto

**📊 Resultado:**
- ✅ 20 equipos de La Liga en BD
- ✅ 380 partidos de la temporada 2024/25 (si carga completa)

---

## 🔄 ACTUALIZACIÓN DIARIA DE RESULTADOS

### Actualizar partidos de HOY
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 0
```

### Actualizar partidos de AYER (recomendado)
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 1
```

### Actualizar últimos 3 días
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 3
```

### Actualizar ayer + hoy + mañana
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 1 --days-forward 1
```

### Actualizar solo partidos pendientes o en curso
```bash
docker-compose exec web python manage.py update_sofascore_football --only-pending
```

---

## 📋 COMANDOS SEGÚN NECESIDAD

### 🎯 Para obtener resultados de HOY MISMO
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 0 --days-forward 0
```

### 🎯 Para actualización automática diaria (RECOMENDADO)
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 1 --days-forward 0
```

### 🎯 Para recuperar resultados de toda la semana
```bash
docker-compose exec web python manage.py update_sofascore_football --days-back 7
```

### 🎯 Para actualizar solo partidos de La Liga
```bash
docker-compose exec web python manage.py update_sofascore_football --league-id 1
```

### 🎯 Para actualizar TODOS los partidos en BD
```bash
docker-compose exec web python manage.py update_sofascore_football --update-all
```

---

## 🔍 VERIFICACIÓN Y DEBUGGING

### Ver partidos en BD
```bash
docker-compose exec web python scripts/verify_matches.py
```

### Ver análisis detallado de marcadores
```bash
docker-compose exec web python scripts/verify_scores_detailed.py
```

### Completar marcadores faltantes
```bash
docker-compose exec web python scripts/check_incomplete_scores.py
```

### Cargar equipos específicos que faltan
```bash
docker-compose exec web python scripts/load_missing_teams.py
```

---

## 🗄️ COMANDOS DE BASE DE DATOS

### Acceder a MySQL
```bash
docker-compose exec db mysql -u nico -p bet_db
# Password: C0r4z0n#25
```

### Hacer backup de BD
```bash
docker-compose exec db mysqldump -u nico -p bet_db > backup_$(date +%Y%m%d).sql
# Password: C0r4z0n#25
```

### Restaurar backup
```bash
docker-compose exec -T db mysql -u nico -p bet_db < backup_20241201.sql
```

### Ver tablas
```bash
docker-compose exec db mysql -u nico -p bet_db -e "SHOW TABLES;"
```

### Contar partidos
```bash
docker-compose exec db mysql -u nico -p bet_db -e "SELECT COUNT(*) as total_partidos FROM api_partidos;"
```

### Ver partidos de hoy
```bash
docker-compose exec db mysql -u nico -p bet_db -e "
SELECT
    CONCAT(el.nombre, ' ', IFNULL(p.goles_local, '-'), ' - ', IFNULL(p.goles_visitante, '-'), ' ', ev.nombre) as partido,
    p.estado,
    p.fecha
FROM api_partidos p
JOIN api_equipos el ON p.equipo_local = el.id_equipo
JOIN api_equipos ev ON p.equipo_visitante = ev.id_equipo
WHERE DATE(p.fecha) = CURDATE()
ORDER BY p.fecha;
"
```

---

## 🐍 COMANDOS DJANGO GENERALES

### Acceder a Django shell
```bash
docker-compose exec web python manage.py shell
```

Ejemplos de uso en shell:
```python
from bets.models import ApiPartido, ApiEquipo, ApiLiga
from datetime import datetime

# Ver todos los equipos
equipos = ApiEquipo.objects.filter(tipo='Club')
for e in equipos:
    print(f"{e.nombre} ({e.id_pais.nombre})")

# Ver partidos de hoy
hoy = datetime.now().date()
partidos = ApiPartido.objects.filter(fecha__date=hoy)
for p in partidos:
    print(f"{p.equipo_local.nombre} {p.goles_local} - {p.goles_visitante} {p.equipo_visitante.nombre}")

# Ver estadísticas
from bets.models import PartidoStatus
print(f"Programados: {ApiPartido.objects.filter(estado=PartidoStatus.PROGRAMADO).count()}")
print(f"Finalizados: {ApiPartido.objects.filter(estado=PartidoStatus.FINALIZADO).count()}")
```

### Migraciones
```bash
# Crear migraciones
docker-compose exec web python manage.py makemigrations

# Aplicar migraciones
docker-compose exec web python manage.py migrate

# Ver estado de migraciones
docker-compose exec web python manage.py showmigrations
```

### Ver logs de Django
```bash
docker-compose logs -f web
```

### Ver logs de MySQL
```bash
docker-compose logs -f db
```

---

## ⏰ AUTOMATIZACIÓN CON CRON

### Opción 1: Cron en el host (Linux/Mac)

Editar crontab del host:
```bash
crontab -e
```

Agregar línea:
```bash
# Actualizar partidos todos los días a las 2 AM
0 2 * * * cd /ruta/web-nico-project-be/bet_project && docker-compose exec -T web python manage.py update_sofascore_football --days-back 1 >> /var/log/sofascore-update.log 2>&1
```

**Nota:** El flag `-T` es necesario para cron (no allocate TTY).

---

### Opción 2: Cron dentro del contenedor

Crear archivo `docker/cron/update-matches`:
```bash
0 2 * * * cd /app && python manage.py update_sofascore_football --days-back 1 >> /var/log/cron.log 2>&1
```

Modificar `Dockerfile` para incluir cron:
```dockerfile
# Instalar cron
RUN apt-get update && apt-get install -y cron

# Copiar archivo cron
COPY docker/cron/update-matches /etc/cron.d/update-matches
RUN chmod 0644 /etc/cron.d/update-matches
RUN crontab /etc/cron.d/update-matches

# Crear log file
RUN touch /var/log/cron.log
```

---

### Opción 3: Script manual diario (más simple)

Crear script `update_daily.sh`:
```bash
#!/bin/bash
cd /ruta/web-nico-project-be/bet_project
docker-compose exec -T web python manage.py update_sofascore_football --days-back 1
```

Ejecutar manualmente cada día:
```bash
./update_daily.sh
```

---

## 🔄 REINICIAR Y MANTENER CONTENEDORES

### Detener contenedores
```bash
docker-compose down
```

### Detener y eliminar volúmenes (CUIDADO: borra BD)
```bash
docker-compose down -v
```

### Reiniciar contenedores
```bash
docker-compose restart
```

### Reiniciar solo Django (después de cambios en código)
```bash
docker-compose restart web
```

### Reconstruir contenedores (después de cambios en Dockerfile/requirements)
```bash
docker-compose up -d --build
```

### Ver uso de recursos
```bash
docker stats
```

---

## 🧹 LIMPIEZA Y MANTENIMIENTO

### Ver espacio usado por Docker
```bash
docker system df
```

### Limpiar contenedores detenidos
```bash
docker container prune
```

### Limpiar imágenes sin usar
```bash
docker image prune
```

### Limpiar todo (CUIDADO)
```bash
docker system prune -a
```

---

## 📝 CHEATSHEET RÁPIDO

```bash
# === SETUP INICIAL ===
docker-compose up -d                                          # Levantar contenedores
docker-compose exec web python Populate_countries.py         # Cargar países
docker-compose exec web python manage.py createsuperuser     # Crear admin
docker-compose exec web python manage.py load_sofascore_laliga  # Cargar La Liga

# === SCRAPING DIARIO ===
docker-compose exec web python manage.py update_sofascore_football --days-back 1

# === VERIFICACIÓN ===
docker-compose exec web python scripts/verify_matches.py     # Ver partidos
docker-compose logs -f web                                    # Ver logs

# === BASE DE DATOS ===
docker-compose exec db mysql -u nico -p bet_db               # Acceder a MySQL
docker-compose exec web python manage.py shell               # Django shell

# === MANTENIMIENTO ===
docker-compose restart web                                    # Reiniciar Django
docker-compose down                                           # Detener todo
docker-compose up -d --build                                  # Reconstruir
```

---

## 🎯 FLUJO DE TRABAJO RECOMENDADO

### Día 1 (Setup):
```bash
docker-compose up -d
docker-compose exec web python Populate_countries.py
docker-compose exec web python manage.py createsuperuser
# Crear deporte "Fútbol" en admin
docker-compose exec web python manage.py load_sofascore_laliga
docker-compose exec web python scripts/verify_matches.py
```

### Día 2+ (Automático):
```bash
# Configurar cron job para ejecutar todos los días a las 2 AM:
# docker-compose exec -T web python manage.py update_sofascore_football --days-back 1
```

### Cuando necesites verificar:
```bash
docker-compose exec web python scripts/verify_matches.py
docker-compose logs -f web
```

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Contenedores no inician
```bash
docker-compose logs
```

### Error de conexión a BD
```bash
# Verificar que MySQL esté healthy
docker-compose ps

# Esperar 10 segundos y reintentar
docker-compose restart web
```

### Error 403 de SofaScore
```bash
# Esperar 5-10 minutos antes de reintentar
# SofaScore bloquea peticiones muy frecuentes
```

### Cambios en código no se reflejan
```bash
# Reiniciar contenedor Django
docker-compose restart web

# O reconstruir si cambiaste requirements.txt
docker-compose up -d --build
```

### BD corrupta o quieres empezar de cero
```bash
# CUIDADO: Esto borra TODO
docker-compose down -v
docker-compose up -d
# Repetir setup inicial
```

---

## 🚀 SIGUIENTE NIVEL

### Agregar más ligas
Modificar `load_sofascore_laliga.py` para aceptar otros torneos:
```bash
docker-compose exec web python manage.py load_sofascore_laliga --tournament-id 17 --season-id 61627
# 17 = Premier League
```

### Crear comando genérico
Crear `load_sofascore_tournament.py` que acepte cualquier liga.

### Extender a otros deportes
Usar las funciones de `sofascore_api.py` para tenis, basket, F1.

---

**🎉 ¡Listo para usar!**

Todos los comandos están listos para Docker. Solo ejecuta `docker-compose up -d` y sigue el flujo de trabajo.
