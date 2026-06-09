#!/bin/bash

# Script de ayuda para gestionar Docker en el proyecto Bet Project

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}================================${NC}"
}

function print_error() {
    echo -e "${RED}Error: $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}Advertencia: $1${NC}"
}

function check_env_file() {
    if [ ! -f .env ]; then
        print_warning "No se encontró archivo .env"
        read -p "¿Deseas crear uno desde .env.example? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            cp .env.example .env
            echo -e "${GREEN}Archivo .env creado. Por favor, edítalo con tus configuraciones.${NC}"
        else
            print_error "Se requiere archivo .env para continuar"
            exit 1
        fi
    fi
}

function start_services() {
    print_header "Iniciando servicios Docker"
    check_env_file
    docker-compose up -d
    echo -e "${GREEN}Servicios iniciados exitosamente${NC}"
    echo -e "Django: http://localhost:8000"
    echo -e "Admin: http://localhost:8000/admin/"
}

function stop_services() {
    print_header "Deteniendo servicios"
    docker-compose stop
    echo -e "${GREEN}Servicios detenidos${NC}"
}

function restart_services() {
    print_header "Reiniciando servicios"
    docker-compose restart
    echo -e "${GREEN}Servicios reiniciados${NC}"
}

function view_logs() {
    print_header "Mostrando logs (Ctrl+C para salir)"
    docker-compose logs -f
}

function rebuild_services() {
    print_header "Reconstruyendo servicios"
    docker-compose up -d --build
    echo -e "${GREEN}Servicios reconstruidos${NC}"
}

function run_migrations() {
    print_header "Ejecutando migraciones"
    docker-compose exec web python manage.py migrate
    echo -e "${GREEN}Migraciones completadas${NC}"
}

function create_superuser() {
    print_header "Creando superusuario"
    docker-compose exec web python manage.py createsuperuser
}

function django_shell() {
    print_header "Abriendo Django shell"
    docker-compose exec web python manage.py shell
}

function mysql_shell() {
    print_header "Abriendo MySQL shell"
    docker-compose exec db mysql -u nico -p bet_db
}

function backup_db() {
    print_header "Creando backup de la base de datos"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backup_${TIMESTAMP}.sql"
    docker-compose exec db mysqldump -u nico -p bet_db > "$BACKUP_FILE"
    echo -e "${GREEN}Backup creado: $BACKUP_FILE${NC}"
}

function clean_all() {
    print_warning "Esto eliminará TODOS los contenedores, volúmenes y datos"
    read -p "¿Estás seguro? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        print_header "Limpiando todo"
        docker-compose down -v
        echo -e "${GREEN}Limpieza completa${NC}"
    else
        echo "Operación cancelada"
    fi
}

function show_status() {
    print_header "Estado de los servicios"
    docker-compose ps
}

function show_help() {
    echo "Bet Project - Docker Helper Script"
    echo ""
    echo "Uso: ./docker-helper.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start       - Iniciar todos los servicios"
    echo "  stop        - Detener todos los servicios"
    echo "  restart     - Reiniciar todos los servicios"
    echo "  logs        - Ver logs en tiempo real"
    echo "  rebuild     - Reconstruir las imágenes"
    echo "  migrate     - Ejecutar migraciones de Django"
    echo "  superuser   - Crear superusuario de Django"
    echo "  shell       - Abrir shell de Django"
    echo "  mysql       - Abrir shell de MySQL"
    echo "  backup      - Crear backup de la base de datos"
    echo "  status      - Ver estado de los contenedores"
    echo "  clean       - Eliminar contenedores y volúmenes (PELIGROSO)"
    echo "  help        - Mostrar esta ayuda"
}

# Procesar comando
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        view_logs
        ;;
    rebuild)
        rebuild_services
        ;;
    migrate)
        run_migrations
        ;;
    superuser)
        create_superuser
        ;;
    shell)
        django_shell
        ;;
    mysql)
        mysql_shell
        ;;
    backup)
        backup_db
        ;;
    status)
        show_status
        ;;
    clean)
        clean_all
        ;;
    help|*)
        show_help
        ;;
esac
