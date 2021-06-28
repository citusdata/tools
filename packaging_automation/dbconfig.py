from attr import dataclass
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@dataclass
class DbParams:
    user_name: str
    password: str
    host_and_port: str
    db_name: str


def db_connection_string(user_name: str, password: str, host_and_port: str, db_name: str, is_test=False):
    database_name = db_name if not is_test else f"{db_name}-test"
    return f'postgresql+psycopg2://{user_name}:{password}@{host_and_port}/{database_name}'


def db_session(db_parameters: DbParams, is_test: bool, create_db_objects: bool = True):
    db_engine = create_engine(
        db_connection_string(user_name=db_parameters.user_name, password=db_parameters.password,
                             host_and_port=db_parameters.host_and_port, db_name=db_parameters.db_name,
                             is_test=is_test))
    if create_db_objects:
        Base.metadata.create_all(db_engine)

    Session = sessionmaker(db_engine)
    return Session()


Base = declarative_base()
