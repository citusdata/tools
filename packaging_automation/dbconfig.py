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


def db_connection_string(db_params: DbParams, is_test=False):
    database_name = db_params.db_name if not is_test else f"{db_params.db_name}-test"
    return f'postgresql+psycopg2://{db_params.user_name}:{db_params.password}@{db_params.host_and_port}/{database_name}'


def db_session(db_params: DbParams, is_test: bool, create_db_objects: bool = True):
    db_engine = create_engine(
        db_connection_string(db_params=db_params, is_test=is_test))
    if create_db_objects:
        Base.metadata.create_all(db_engine)
    Session = sessionmaker(db_engine)
    return Session()


Base = declarative_base()
