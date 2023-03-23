import enum

import sqlalchemy
from attr import dataclass
from sqlalchemy import Column, INTEGER, TIMESTAMP, TEXT
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


@dataclass
class DbParams:
    user_name: str
    password: str
    host_and_port: str
    db_name: str


def db_connection_string(db_params: DbParams, is_test=False):
    database_name = db_params.db_name if not is_test else f"{db_params.db_name}-test"
    return f"postgresql+psycopg2://{db_params.user_name}:{db_params.password}@{db_params.host_and_port}/{database_name}"


def db_session(db_params: DbParams, is_test: bool, create_db_objects: bool = True):
    db_engine = create_engine(
        db_connection_string(db_params=db_params, is_test=is_test)
    )
    if create_db_objects:
        Base.metadata.create_all(db_engine)
    Session = sessionmaker(db_engine)
    return Session()


Base = declarative_base()


class RequestType(enum.Enum):
    docker_pull = 1
    github_clone = 2
    package_cloud_list_package = 3
    package_cloud_download_series_query = 4
    package_cloud_detail_query = 5
    homebrew_download = 6


class RequestLog(Base):
    __tablename__ = "request_log"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    request_time = Column(TIMESTAMP, nullable=False)
    request_type = Column(sqlalchemy.Enum(RequestType))
    status_code = Column(INTEGER)
    response = Column(TEXT)
