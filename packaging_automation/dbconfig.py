### config.py ###
from sqlalchemy.ext.declarative import declarative_base


def db_connection_string(is_test=False):
    database_name = "citus-stats" if not is_test else "citus-stats-test"
    return (f'postgresql+psycopg2://citus_admin@citus-stats:CtsRocks123@citus-stats.postgres.database.azure.com:5432/'
            f'{database_name}')


Base = declarative_base()
