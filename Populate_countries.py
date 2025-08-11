import mysql.connector

# Your database connection config
config = {
    'user': 'nico',
    'password': 'C0r4z0n#25',
    'host': 'localhost',        # or your DB host
    'database': 'bet_db_new' # your DB name
}

# The target table name
table_name = 'pais'

# Country data: (Nombre, Continente, Bandera)
# I’m adding continent names roughly based on common regions for your list
countries = [
    ("France", "Europe", "FR"),
    ("England", "Europe", "GB"),
    ("Belgium", "Europe", "BE"),
    ("Netherlands", "Europe", "NL"),
    ("Portugal", "Europe", "PT"),
    ("Italy", "Europe", "IT"),
    ("Uruguay", "South America", "UY"),
    ("Croatia", "Europe", "HR"),
    ("Germany", "Europe", "DE"),
    ("Morocco", "Africa", "MA"),
    ("Switzerland", "Europe", "CH"),
    ("Japan", "Asia", "JP"),
    ("Mexico", "North America", "MX"),
    ("Poland", "Europe", "PL"),
    ("Senegal", "Africa", "SN"),
    ("Denmark", "Europe", "DK"),
    ("Sweden", "Europe", "SE"),
    ("South Korea", "Asia", "KR"),
    ("Tunisia", "Africa", "TN"),
    ("Serbia", "Europe", "RS"),
    ("Cameroon", "Africa", "CM"),
    ("Austria", "Europe", "AT"),
    ("Turkey", "Europe", "TR"),
    ("Nigeria", "Africa", "NG"),
    ("Wales", "Europe", "GB-WLS"),
    ("Czech Republic", "Europe", "CZ"),
    ("Ghana", "Africa", "GH"),
    ("Romania", "Europe", "RO"),
    ("Russia", "Europe/Asia", "RU"),
    ("Canada", "North America", "CA"),
    ("Northern Ireland", "Europe", "GB-NIR"),
    ("Ukraine", "Europe", "UA"),
    ("Iceland", "Europe", "IS"),
    ("Algeria", "Africa", "DZ"),
    ("Costa Rica", "Central America", "CR"),
    ("Hungary", "Europe", "HU"),
    ("Scotland", "Europe", "GB-SCT"),
    ("Slovakia", "Europe", "SK"),
    ("Bosnia and Herzegovina", "Europe", "BA"),
    ("Ecuador", "South America", "EC"),
    ("Finland", "Europe", "FI"),
    ("Bulgaria", "Europe", "BG"),
    ("Greece", "Europe", "GR"),
    ("Norway", "Europe", "NO"),
    ("Slovenia", "Europe", "SI"),
    ("Republic of Ireland", "Europe", "IE"),
    ("Israel", "Asia", "IL"),
    ("United Arab Emirates", "Asia", "AE"),
    ("Lebanon", "Asia", "LB"),
    ("New Zealand", "Oceania", "NZ"),
    ("Luxembourg", "Europe", "LU"),
    ("Lithuania", "Europe", "LT"),
    ("Latvia", "Europe", "LV"),
    ("Estonia", "Europe", "EE"),
    ("Belarus", "Europe", "BY"),
    ("Azerbaijan", "Europe/Asia", "AZ"),
    ("Armenia", "Asia", "AM"),
    ("Georgia", "Asia", "GE"),
    ("North Macedonia", "Europe", "MK"),
    ("Malta", "Europe", "MT"),
    ("Cyprus", "Europe/Asia", "CY"),
    ("Moldova", "Europe", "MD"),
    ("Andorra", "Europe", "AD"),
    ("Liechtenstein", "Europe", "LI"),
    ("San Marino", "Europe", "SM"),
    ("Faroe Islands", "Europe", "FO"),
    ("Monaco", "Europe", "MC"),
    ("Gibraltar", "Europe", "GI"),
    ("Bhutan", "Asia", "BT"),
    ("Maldives", "Asia", "MV"),
    ("Cambodia", "Asia", "KH"),
    ("Timor-Leste", "Asia", "TL"),
    ("Nepal", "Asia", "NP"),
    ("Bangladesh", "Asia", "BD"),
    ("Philippines", "Asia", "PH"),
    ("Indonesia", "Asia", "ID"),
    ("Vietnam", "Asia", "VN"),
    ("Thailand", "Asia", "TH"),
    ("Myanmar", "Asia", "MM"),
    ("Pakistan", "Asia", "PK"),
    ("Sri Lanka", "Asia", "LK"),
    ("Brunei", "Asia", "BN"),
    ("Laos", "Asia", "LA"),
]

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Optional: Clear existing data (comment out if you want to keep data)
    # cursor.execute(f"TRUNCATE TABLE {table_name}")
    # conn.commit()

    sql_insert = f"INSERT INTO {table_name} (Nombre, Continente, Bandera) VALUES (%s, %s, %s)"

    for country in countries:
        cursor.execute(sql_insert, country)
    
    conn.commit()
    print(f"Inserted {cursor.rowcount} rows successfully!")

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
