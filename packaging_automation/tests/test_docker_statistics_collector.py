import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..dbconfig import Base, db_connection_string, DbParams
from ..docker_statistics_collector import fetch_and_store_docker_statistics, DockerStats

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")


def test_docker_statistics_collector():
    test_day_shift_index = -2
    test_pull_count_shift = 205
    db_params = DbParams(
        user_name=DB_USER_NAME,
        password=DB_PASSWORD,
        host_and_port=DB_HOST_AND_PORT,
        db_name=DB_NAME,
    )
    db = create_engine(db_connection_string(db_params=db_params, is_test=True))
    sql = text(f"DROP TABLE IF EXISTS {DockerStats.__tablename__}")
    db.execute(sql)
    Session = sessionmaker(db)
    session = Session()
    fetch_and_store_docker_statistics(
        "citus",
        db_parameters=db_params,
        is_test=True,
        test_day_shift_index=test_day_shift_index,
    )
    first_day = datetime.today() + timedelta(days=test_day_shift_index)
    first_day_record = (
        session.query(DockerStats).filter_by(stat_date=first_day.date()).first()
    )
    fetch_and_store_docker_statistics(
        "citus",
        db_parameters=db_params,
        is_test=True,
        test_total_pull_count=first_day_record.total_pull_count + test_pull_count_shift,
    )
    Base.metadata.create_all(db)

    second_day = datetime.today() + timedelta(days=test_day_shift_index + 1)
    third_day = datetime.today()

    second_day_record = (
        session.query(DockerStats).filter_by(stat_date=second_day.date()).first()
    )
    third_day_record = (
        session.query(DockerStats).filter_by(stat_date=third_day.date()).first()
    )

    pull_count_diff = (
        third_day_record.total_pull_count - first_day_record.total_pull_count
    )

    assert (
        third_day_record
        and second_day_record
        and (third_day_record.total_pull_count == second_day_record.total_pull_count)
        and (
            third_day_record.daily_pull_count + second_day_record.daily_pull_count
            == pull_count_diff
        )
        and (pull_count_diff == test_pull_count_shift)
    )
