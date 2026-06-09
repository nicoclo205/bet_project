"""
Script para poblar la tabla api_paises con países principales.
Versión corregida para usar con Django y la estructura actual de la BD.
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bet_project.settings')
django.setup()

from bets.models import ApiPais

# Lista de países con su código ISO2
# Formato: (nombre, code, api_id_opcional)
countries = [
    # Europa principales
    ("France", "FR", 2),
    ("England", "GB", 462),
    ("Belgium", "BE", 1),
    ("Netherlands", "NL", 34),
    ("Portugal", "PT", 27),
    ("Italy", "IT", 768),
    ("Germany", "DE", 25),
    ("Spain", "ES", 724),
    ("Croatia", "HR", 3),
    ("Switzerland", "CH", 15),
    ("Poland", "PL", 28),
    ("Denmark", "DK", 21),
    ("Sweden", "SE", 113),
    ("Serbia", "RS", 14),
    ("Austria", "AT", 17),
    ("Turkey", "TR", 777),
    ("Wales", "GB-WLS", 767),
    ("Czech Republic", "CZ", 333),
    ("Romania", "RO", 774),
    ("Russia", "RU", 35),
    ("Ukraine", "UA", 775),
    ("Iceland", "IS", 373),
    ("Hungary", "HU", 18),
    ("Scotland", "GB-SCT", 1104),
    ("Slovakia", "SK", 24),
    ("Bosnia and Herzegovina", "BA", 20),
    ("Finland", "FI", 101),
    ("Bulgaria", "BG", 114),
    ("Greece", "GR", 19),
    ("Norway", "NO", 23),
    ("Slovenia", "SI", 13),
    ("Republic of Ireland", "IE", 10),
    ("Northern Ireland", "GB-NIR", 1367),

    # América del Sur
    ("Uruguay", "UY", 7),
    ("Colombia", "CO", 8),
    ("Brazil", "BR", 31),
    ("Argentina", "AR", 26),
    ("Chile", "CL", 33),
    ("Peru", "PE", 49),
    ("Ecuador", "EC", 22),
    ("Paraguay", "PY", 60),
    ("Venezuela", "VE", 2383),
    ("Bolivia", "BO", 2384),

    # América del Norte y Central
    ("Mexico", "MX", 16),
    ("USA", "US", 2094),
    ("Canada", "CA", 1530),
    ("Costa Rica", "CR", 85),
    ("Panama", "PA", 660),
    ("Jamaica", "JM", 2385),
    ("Honduras", "HN", 86),
    ("Guatemala", "GT", 2386),

    # África
    ("Morocco", "MA", 12),
    ("Senegal", "SN", 5),
    ("Tunisia", "TN", 30),
    ("Cameroon", "CM", 1529),
    ("Nigeria", "NG", 11),
    ("Ghana", "GH", 2382),
    ("Algeria", "DZ", 2381),
    ("Egypt", "EG", 1530),
    ("South Africa", "ZA", 32),
    ("Ivory Coast", "CI", 1501),

    # Asia
    ("Japan", "JP", 50),
    ("South Korea", "KR", 48),
    ("Saudi Arabia", "SA", 58),
    ("Iran", "IR", 22),
    ("Australia", "AU", 1530),
    ("Qatar", "QA", 1569),
    ("Iraq", "IQ", 1567),
    ("United Arab Emirates", "AE", 1568),
    ("China", "CN", 51),
    ("India", "IN", 1530),
    ("Israel", "IL", 780),
    ("Lebanon", "LB", 1570),
    ("Thailand", "TH", 1530),
    ("Vietnam", "VN", 1530),
    ("Indonesia", "ID", 1530),
    ("Philippines", "PH", 1530),
    ("Pakistan", "PK", 1530),
    ("Bangladesh", "BD", 1530),
    ("Sri Lanka", "LK", 1530),
    ("Myanmar", "MM", 1530),
    ("Cambodia", "KH", 1530),
    ("Laos", "LA", 1530),
    ("Nepal", "NP", 1530),
    ("Bhutan", "BT", 1530),
    ("Maldives", "MV", 1530),
    ("Brunei", "BN", 1530),
    ("Timor-Leste", "TL", 1530),

    # Oceanía
    ("New Zealand", "NZ", 1530),

    # Otros pequeños países europeos
    ("Luxembourg", "LU", 1530),
    ("Lithuania", "LT", 1530),
    ("Latvia", "LV", 1530),
    ("Estonia", "EE", 1530),
    ("Belarus", "BY", 1530),
    ("Azerbaijan", "AZ", 1530),
    ("Armenia", "AM", 1530),
    ("Georgia", "GE", 1530),
    ("North Macedonia", "MK", 1530),
    ("Malta", "MT", 1530),
    ("Cyprus", "CY", 1530),
    ("Moldova", "MD", 1530),
    ("Andorra", "AD", 1530),
    ("Liechtenstein", "LI", 1530),
    ("San Marino", "SM", 1530),
    ("Faroe Islands", "FO", 1530),
    ("Monaco", "MC", 1530),
    ("Gibraltar", "GI", 1530),
]

def populate_countries():
    """
    Puebla la tabla api_paises con los países definidos.
    Usa get_or_create para evitar duplicados.
    """
    created_count = 0
    updated_count = 0

    print("🌍 Iniciando carga de países...\n")

    for nombre, code, api_id in countries:
        pais, created = ApiPais.objects.get_or_create(
            code=code,
            defaults={
                'nombre': nombre,
                'api_id': api_id if api_id else None,
            }
        )

        if created:
            created_count += 1
            print(f"✅ Creado: {nombre} ({code})")
        else:
            # Actualizar si cambió el nombre o api_id
            updated = False
            if pais.nombre != nombre:
                pais.nombre = nombre
                updated = True
            if api_id and pais.api_id != api_id:
                pais.api_id = api_id
                updated = True

            if updated:
                pais.save()
                updated_count += 1
                print(f"🔄 Actualizado: {nombre} ({code})")
            else:
                print(f"⏭️  Ya existe: {nombre} ({code})")

    print(f"\n{'='*60}")
    print(f"📊 RESUMEN")
    print(f"{'='*60}")
    print(f"   Países creados: {created_count}")
    print(f"   Países actualizados: {updated_count}")
    print(f"   Total en BD: {ApiPais.objects.count()}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    try:
        populate_countries()
        print("✅ Proceso completado exitosamente!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
