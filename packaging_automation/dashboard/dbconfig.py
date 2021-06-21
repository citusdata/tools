### config.py ###
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Scheme: "postgres+psycopg2://<USERNAME>:<PASSWORD>@<IP_ADDRESS>:<PORT>/<DATABASE_NAME>"

DATABASE_URI = (
    'postgresql+psycopg2://citus_admin@citus-stats:CtsRocks123@citus-stats.postgres.database.azure.com:5432/citus-stats')
db = create_engine(DATABASE_URI)
Base = declarative_base()

Session = sessionmaker(db)