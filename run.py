import os
import sys
import subprocess
import platform

def print_help():
    print("\nScript de ayuda para ejecutar comandos con diferentes configuraciones de entorno")
    print("Uso: python run.py [entorno] [comando]")
    print("\nEntornos disponibles:")
    print("  local             - Usar base de datos local (predeterminado)")
    print("  railway_external  - Conectar a Railway desde tu PC local")
    print("  railway           - Para ejecución en Railway")
    print("\nEjemplos:")
    print("  python run.py local migrate")
    print("  python run.py railway_external migrate")
    print("  python run.py local runserver\n")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)
    
    # Determinar el entorno
    env = 'local'
    args_start = 1
    
    if sys.argv[1] in ['local', 'railway_external', 'railway']:
        env = sys.argv[1]
        args_start = 2
    
    # Verificar que hay un comando para ejecutar
    if len(sys.argv) <= args_start:
        print("Error: No se especificó un comando para ejecutar")
        print_help()
        sys.exit(1)
    
    # Determinar el ejecutable de Python correcto
    # Usar el mismo ejecutable de Python que está ejecutando este script
    python_exe = sys.executable
    
    # Construir el comando a ejecutar
    cmd = [python_exe, 'manage.py'] + sys.argv[args_start:]
    
    # Configurar el entorno
    env_vars = os.environ.copy()
    env_vars['DJANGO_ENV'] = env
    
    # Ejecutar el comando
    try:
        print(f"\n🚀 Ejecutando: {' '.join(cmd)} (entorno: {env})\n")
        subprocess.run(cmd, env=env_vars)
    except Exception as e:
        print(f"Error al ejecutar el comando: {e}")
        sys.exit(1)
