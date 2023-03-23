import os

from sqlalchemy import text, create_engine

from ..dbconfig import db_session, DbParams, db_connection_string
from ..homebrew_statistics_collector import fetch_and_save_homebrew_stats, HomebrewStats

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")

db_parameters = DbParams(
    user_name=DB_USER_NAME,
    password=DB_PASSWORD,
    host_and_port=DB_HOST_AND_PORT,
    db_name=DB_NAME,
)


def test_fetch_and_save_homebrew_stats():
    db = create_engine(db_connection_string(db_params=db_parameters, is_test=True))
    db.execute(text(f"DROP TABLE IF EXISTS {HomebrewStats.__tablename__}"))

    session = db_session(db_params=db_parameters, is_test=True)

    fetch_and_save_homebrew_stats(db_params=db_parameters, is_test=True)

    records = session.query(HomebrewStats).all()
    assert len(records) == 1

    fetch_and_save_homebrew_stats(db_params=db_parameters, is_test=True)

    records = session.query(HomebrewStats).all()
    assert len(records) == 1
