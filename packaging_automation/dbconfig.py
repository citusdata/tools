### config.py ###
from sqlalchemy.ext.declarative import declarative_base


def db_connection_string(user_name: str, password: str, host_and_port: str, db_name: str, is_test=False):
    database_name = db_name if not is_test else f"{db_name}-test"
    return f'postgresql+psycopg2://{user_name}:{password}@{host_and_port}/{database_name}'


Base = declarative_base()
