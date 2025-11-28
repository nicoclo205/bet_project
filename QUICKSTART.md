# 🚀 Guía de Inicio Rápido - Bet Project

## Prerrequisitos

- Docker instalado ([Descargar Docker](https://www.docker.com/get-started))
- Docker Compose instalado (incluido con Docker Desktop)

## Inicio en 3 pasos

### 1️⃣ Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar el archivo .env (opcional, los valores por defecto funcionan)
nano .env  # o usa tu editor favorito
```

**Importante**: En producción, cambia las contraseñas por unas seguras.

### 2️⃣ Iniciar los servicios

Tienes 2 opciones:

**Opción A: Usando el script helper (recomendado)**
```bash
./docker-helper.sh start
```

**Opción B: Usando Docker Compose directamente**
```bash
docker-compose up -d
```

### 3️⃣ Crear un superusuario (primera vez)

```bash
# Usando el script helper
./docker-helper.sh superuser

# O usando Docker Compose directamente
docker-compose exec web python manage.py createsuperuser
```

## 🎉 ¡Listo!

Tu aplicación está corriendo en:

- **API**: http://localhost:8000/api/
- **Panel Admin**: http://localhost:8000/admin/
- **Documentación API**: http://localhost:8000/api/

## Comandos útiles

### Ver logs en tiempo real
```bash
./docker-helper.sh logs
# o
docker-compose logs -f
```

### Detener los servicios
```bash
./docker-helper.sh stop
# o
docker-compose stop
```

### Reiniciar los servicios
```bash
./docker-helper.sh restart
# o
docker-compose restart
```

### Ver estado de los contenedores
```bash
./docker-helper.sh status
# o
docker-compose ps
```

### Acceder a la shell de Django
```bash
./docker-helper.sh shell
# o
docker-compose exec web python manage.py shell
```

### Acceder a MySQL
```bash
./docker-helper.sh mysql
# o
docker-compose exec db mysql -u nico -p bet_db
```

### Ejecutar migraciones
```bash
./docker-helper.sh migrate
# o
docker-compose exec web python manage.py migrate
```

### Crear backup de la base de datos
```bash
./docker-helper.sh backup
# o
docker-compose exec db mysqldump -u nico -p bet_db > backup.sql
```

## Solución de Problemas

### Error: "Port 8000 is already allocated"
Otro servicio está usando el puerto 8000. Cámbialo en el archivo `.env`:
```env
DJANGO_PORT=8001
```

### Error: "Can't connect to MySQL server"
MySQL tarda unos segundos en inicializarse. Espera 10-15 segundos y vuelve a intentar.

Para verificar que MySQL está listo:
```bash
docker-compose logs db | grep "ready for connections"
```

### Resetear todo (eliminar base de datos)
```bash
./docker-helper.sh clean
# Confirma con 'y'
./docker-helper.sh start
```

## Siguiente paso

Consulta el archivo `README.md` para documentación completa y ejemplos de uso de la API.

## Ayuda

Ver todos los comandos disponibles:
```bash
./docker-helper.sh help
```
