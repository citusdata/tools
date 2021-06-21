from ..docker_statistics_collector import fetch_and_store_docker_statistics, DockerStats

from datetime import datetime, timedelta
from ..dbconfig import Base, db_connection_string
from sqlalchemy import create_engine, text, engine
from sqlalchemy.orm import sessionmaker


def test_docker_statistics_collector():
    test_day_shift_index = 2
    test_pull_count_shift = 200
    db = create_engine(db_connection_string(is_test=True))
    sql = text(f'DROP TABLE {DockerStats.__tablename__}')
    db.execute(sql)
    fetch_and_store_docker_statistics("citus", is_test=True)
    first_day = datetime.today()
    fetch_and_store_docker_statistics("citus", is_test=True, test_day_shift_index=test_day_shift_index,
                                      test_pull_count_shift=test_pull_count_shift)

    Session = sessionmaker(db)
    session = Session()
    Base.metadata.create_all(db)
    third_day = datetime.today() + timedelta(days=test_day_shift_index)
    second_day = datetime.today() + timedelta(days=test_day_shift_index - 1)

    first_day_record = session.query(DockerStats).filter_by(stat_date=first_day.date()).first()
    third_day_record = session.query(DockerStats).filter_by(stat_date=third_day.date()).first()
    second_day_record = session.query(DockerStats).filter_by(stat_date=second_day.date()).first()

    pull_count_diff = third_day_record.total_pull_count - first_day_record.total_pull_count

    assert third_day_record and second_day_record and (
            third_day_record.total_pull_count == second_day_record.total_pull_count) and (
                   third_day_record.daily_pull_count + second_day_record.daily_pull_count == pull_count_diff)
