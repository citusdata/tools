import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..dbconfig import Base, db_connection_string
from ..docker_statistics_collector import fetch_and_store_docker_statistics, DockerStats

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")


def test_docker_statistics_collector():
    test_day_shift_index = -2
    test_pull_count_shift = 205
    db = create_engine(
        db_connection_string(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT,
                             db_name=DB_NAME, is_test=True))
    sql = text(f'DROP TABLE IF EXISTS {DockerStats.__tablename__}')
    db.execute(sql)
    fetch_and_store_docker_statistics("citus", db_user_name=DB_USER_NAME, db_password=DB_PASSWORD,
                                      db_host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME, is_test=True,
                                      test_day_shift_index=test_day_shift_index)
    fetch_and_store_docker_statistics("citus", db_user_name=DB_USER_NAME, db_password=DB_PASSWORD,
                                      db_host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME,
                                      test_pull_count_shift=test_pull_count_shift, is_test=True)

    Session = sessionmaker(db)
    session = Session()
    Base.metadata.create_all(db)
    first_day = datetime.today() + timedelta(days=test_day_shift_index)
    second_day = datetime.today() + timedelta(days=test_day_shift_index + 1)
    third_day = datetime.today()

    first_day_record = session.query(DockerStats).filter_by(stat_date=first_day.date()).first()
    second_day_record = session.query(DockerStats).filter_by(stat_date=second_day.date()).first()
    third_day_record = session.query(DockerStats).filter_by(stat_date=third_day.date()).first()

    pull_count_diff = third_day_record.total_pull_count - first_day_record.total_pull_count

    assert third_day_record and second_day_record and (
        third_day_record.total_pull_count == second_day_record.total_pull_count) and (
               third_day_record.daily_pull_count + second_day_record.daily_pull_count == pull_count_diff)
