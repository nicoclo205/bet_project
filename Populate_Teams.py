import pandas as pd
from sqlalchemy import create_engine, text

# Replace these with your actual database credentials
db_username = 'nico'
db_password = 'C0r4z0n#25'
db_host = 'localhost'
db_name = 'bet_db_new'
table_name = 'equipos'

# Create a SQLAlchemy engine
engine = create_engine(f'mysql+pymysql://{db_username}:{db_password}@{db_host}/{db_name}')

# Load the CSV file into a pandas DataFrame
csv_file_path = 'Equipos001.csv'
df = pd.read_csv(csv_file_path)

# Remove any unnamed columns
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Replace NaN values with None
df = df.where(pd.notnull(df), None)

# Fetch valid id_pais values from the database
valid_pais_ids_query = text("SELECT id_pais FROM pais")
with engine.connect() as connection:
    valid_pais_ids = {row[0] for row in connection.execute(valid_pais_ids_query)}

# Filter DataFrame to include only rows with valid id_pais
df = df[df['id_pais'].isin(valid_pais_ids)]

# Iterate over the DataFrame and insert or update records
with engine.connect() as connection:
    for _, row in df.iterrows():
        # Convert the row to a dictionary
        row_dict = row.to_dict()

        # Ensure all keys are present, even if they are None
        row_dict = {key: row_dict.get(key) for key in ['id_equipo', 'nombre', 'logo', 'tipo', 'id_deporte', 'id_pais']}

        # Assuming 'id_equipo' is the primary key
        id_equipo = row_dict['id_equipo']

        # Check if the record already exists
        check_query = text(f"SELECT COUNT(*) FROM {table_name} WHERE id_equipo = :id_equipo")
        result = connection.execute(check_query, {'id_equipo': id_equipo})

        if result.scalar() > 0:
            # Update the existing record
            update_query = text(f"""
                UPDATE {table_name}
                SET nombre = :nombre, logo = :logo, tipo = :tipo, id_deporte = :id_deporte, id_pais = :id_pais
                WHERE id_equipo = :id_equipo
            """)
            connection.execute(update_query, row_dict)
        else:
            # Insert the new record
            insert_query = text(f"""
                INSERT INTO {table_name} (id_equipo, nombre, logo, tipo, id_deporte, id_pais)
                VALUES (:id_equipo, :nombre, :logo, :tipo, :id_deporte, :id_pais)
            """)
            connection.execute(insert_query, row_dict)

    connection.commit()

print("Data processed successfully.")
