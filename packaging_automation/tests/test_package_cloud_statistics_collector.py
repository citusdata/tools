import os

from ..dbconfig import (Base, db_session, DbParams)

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")
db_parameters = DbParams(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME)

