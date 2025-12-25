# Guía de Celery - Sistema de Scraping Automatizado

## 📋 Tabla de Contenidos
- [Diferencia entre Celery y Celery Beat](#diferencia-entre-celery-y-celery-beat)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Tareas Programadas](#tareas-programadas)
- [Comandos Docker](#comandos-docker)
- [Verificación y Monitoreo](#verificación-y-monitoreo)
- [Solución de Problemas](#solución-de-problemas)

---

## 🔄 Diferencia entre Celery y Celery Beat

### **Celery Worker** (`celery`)
- **Rol**: Trabajador que ejecuta tareas asíncronas
- **Función**: Escucha la cola de Redis y procesa tareas cuando llegan
- **Analogía**: Es como un "empleado" esperando trabajo
- **Comando**: `celery -A bet_project worker`
- **Container**: `bet_celery`

### **Celery Beat** (`celery-beat`)
- **Rol**: Programador/Scheduler de tareas
- **Función**: Envía tareas a la cola según horarios definidos en `celery.py`
- **Analogía**: Es como un "jefe" que asigna trabajo según el calendario
- **Comando**: `celery -A bet_project beat`
- **Container**: `bet_celery_beat`

### **Flujo de Trabajo**
```
Celery Beat (Scheduler)
    ↓ (envía tareas según horario)
Redis (Cola de mensajes)
    ↓ (almacena tareas pendientes)
Celery Worker (Ejecutor)
    ↓ (procesa las tareas)
Base de Datos / Scraping
```

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Containers                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │   MySQL  │   │  Redis   │   │  Django  │   │  Celery  │ │
│  │    DB    │   │  Queue   │   │   Web    │   │  Worker  │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                                                               │
│                      ┌──────────────┐                        │
│                      │ Celery Beat  │                        │
│                      │  Scheduler   │                        │
│                      └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## ⏰ Tareas Programadas

### 1. **Actualización Completa de SofaScore**
- **Tarea**: `update_sofascore_full`
- **Horarios**: 00:00, 06:00, 12:00, 18:00 (cada 6 horas)
- **Alcance**: 2 días atrás + 7 días adelante
- **Propósito**: Mantener base de datos completa con partidos pasados, actuales y futuros

### 2. **Actualización Rápida**
- **Tarea**: `update_sofascore_quick`
- **Horarios**: 15:00, 21:00
- **Alcance**: Ayer + Hoy + Mañana
- **Propósito**: Actualización rápida en horarios pico de partidos

### 3. **Partidos en Vivo**
- **Tarea**: `update_live_matches`
- **Horario**: Cada 5 minutos de 12:00 a 23:59
- **Alcance**: Solo partidos del día (con flag `--only-pending`)
- **Propósito**: Actualización en tiempo real de marcadores

### 4. **Procesamiento de Resultados**
- **Tarea**: `process_finished_matches`
- **Horario**: Cada hora (minuto 30)
- **Propósito**: Calcular puntos de apuestas cuando partidos finalizan

### 5. **Limpieza de Notificaciones**
- **Tarea**: `cleanup_old_notifications`
- **Horario**: Diariamente a las 3:00 AM
- **Propósito**: Eliminar notificaciones mayores a 30 días

---

## 🐳 Comandos Docker

### Iniciar el Sistema Completo
```bash
# Detener contenedores existentes
docker-compose down

# Construir imágenes
docker-compose build

# Iniciar todos los servicios
docker-compose up -d

# Ver estado de contenedores
docker ps
```

### Iniciar Servicios Específicos
```bash
# Solo base de datos y Redis
docker-compose up -d db redis

# Solo aplicación web
docker-compose up -d web

# Solo Celery worker
docker-compose up -d celery

# Solo Celery beat
docker-compose up -d celery-beat
```

### Detener Servicios
```bash
# Detener todos
docker-compose down

# Detener sin eliminar volúmenes (mantiene datos)
docker-compose stop

# Detener servicio específico
docker-compose stop celery
docker-compose stop celery-beat
```

---

## 📊 Verificación y Monitoreo

### Ver Logs en Tiempo Real
```bash
# Logs de Celery Worker
docker logs bet_celery -f

# Logs de Celery Beat
docker logs bet_celery_beat -f

# Logs de Django
docker logs bet_django -f

# Logs de Redis
docker logs bet_redis -f

# Logs de MySQL
docker logs bet_mysql -f
```

### Ver Logs de un Periodo Específico
```bash
# Últimas 100 líneas
docker logs bet_celery --tail 100

# Últimas 24 horas
docker logs bet_celery --since 24h
```

### Verificar Estado de Servicios
```bash
# Ver todos los contenedores
docker ps -a

# Ver solo contenedores activos
docker ps

# Inspeccionar contenedor específico
docker inspect bet_celery
```

### Verificar Conectividad Redis
```bash
# Conectar a Redis CLI
docker exec -it bet_redis redis-cli

# Dentro de Redis, verificar conexión
> PING
PONG

# Ver tareas en cola
> KEYS *

# Salir
> exit
```

### Ejecutar Comandos Dentro del Container
```bash
# Acceder al shell de Django
docker exec -it bet_django bash

# Ejecutar comando Django
docker exec -it bet_django python manage.py update_sofascore_football --days-back=1 --days-forward=1

# Ver trabajos de Celery
docker exec -it bet_celery celery -A bet_project inspect active

# Ver tareas registradas
docker exec -it bet_celery celery -A bet_project inspect registered
```

---

## 🔧 Solución de Problemas

### Problema: Celery Worker no inicia
**Síntomas**: Container `bet_celery` se reinicia constantemente

**Soluciones**:
```bash
# 1. Ver logs detallados
docker logs bet_celery --tail 50

# 2. Verificar que Redis esté corriendo
docker ps | grep redis

# 3. Verificar conectividad con Redis
docker exec -it bet_celery ping redis

# 4. Reconstruir container
docker-compose stop celery
docker-compose build celery
docker-compose up -d celery
```

### Problema: Celery Beat no programa tareas
**Síntomas**: Tareas programadas no se ejecutan

**Soluciones**:
```bash
# 1. Ver logs de Beat
docker logs bet_celery_beat -f

# 2. Verificar que Worker esté corriendo
docker ps | grep celery

# 3. Reiniciar Beat
docker-compose restart celery-beat

# 4. Verificar configuración en celery.py
# Asegurarse que beat_schedule está definido correctamente
```

### Problema: Tareas no se ejecutan
**Síntomas**: Beat programa pero Worker no procesa

**Soluciones**:
```bash
# 1. Verificar que Worker vea las tareas
docker exec -it bet_celery celery -A bet_project inspect registered

# 2. Ver tareas activas
docker exec -it bet_celery celery -A bet_project inspect active

# 3. Ver tareas reservadas
docker exec -it bet_celery celery -A bet_project inspect reserved

# 4. Purgar cola de Redis (cuidado!)
docker exec -it bet_celery celery -A bet_project purge
```

### Problema: Error de conexión a MySQL
**Síntomas**: `Can't connect to MySQL server`

**Soluciones**:
```bash
# 1. Verificar que MySQL esté corriendo
docker ps | grep mysql

# 2. Ver logs de MySQL
docker logs bet_mysql --tail 50

# 3. Verificar healthcheck
docker inspect bet_mysql | grep Health

# 4. Esperar a que MySQL inicie completamente
# MySQL tarda ~30s en estar listo en primer inicio
```

### Problema: Redis no disponible
**Síntomas**: `Error connecting to Redis`

**Soluciones**:
```bash
# 1. Verificar que Redis esté corriendo
docker ps | grep redis

# 2. Probar conexión desde Django
docker exec -it bet_django python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# 3. Reiniciar Redis
docker-compose restart redis
```

---

## 🧪 Pruebas Manuales

### Ejecutar Tarea Manual
```bash
# Desde dentro del container Django
docker exec -it bet_django python manage.py shell

# En el shell de Python
>>> from bets.tasks import update_sofascore_full
>>> result = update_sofascore_full.delay()
>>> result.status
'SUCCESS'
```

### Probar Scraping Manual
```bash
# Actualización completa
docker exec -it bet_django python manage.py update_sofascore_football --days-back=2 --days-forward=7

# Solo partidos de hoy
docker exec -it bet_django python manage.py update_sofascore_football --days-back=0 --days-forward=0

# Solo partidos pendientes
docker exec -it bet_django python manage.py update_sofascore_football --days-back=1 --days-forward=1 --only-pending
```

---

## 📝 Variables de Entorno Importantes

En tu archivo `.env`:
```bash
# Django
DEBUG=True
SECRET_KEY=tu-secret-key-aqui

# Base de datos
DB_NAME=bet_db
DB_USER=nico
DB_PASSWORD=C0r4z0n#25
DB_HOST=db
DB_PORT=3306

# Redis (para Celery y Channels)
REDIS_HOST=redis

# Otros
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## 🎯 Mejores Prácticas

1. **Monitorear Logs Regularmente**: Revisa los logs de Celery al menos una vez al día
2. **No Modificar Tareas en Ejecución**: Detén Beat antes de modificar horarios
3. **Backups de Redis**: Redis almacena el estado de las tareas, haz backups periódicos
4. **Rate Limiting**: SofaScore puede bloquear si haces muchas peticiones, los delays están configurados
5. **Escalabilidad**: Puedes aumentar `--concurrency` en el Worker si necesitas más capacidad

---

## 📚 Referencias

- [Documentación Celery](https://docs.celeryproject.org/)
- [Django Celery Integration](https://docs.celeryproject.org/en/stable/django/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- SofaScore API: API no oficial, usa con delays apropiados
