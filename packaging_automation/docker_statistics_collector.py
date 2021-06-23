import argparse
import sys
from datetime import datetime, timedelta

import requests
from sqlalchemy import Column, DATE, INTEGER, TIMESTAMP, desc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .common_tool_methods import (str_array_to_str)
from .dbconfig import (Base, db_connection_string)

IS_TEST = False


class DockerStats(Base):
    __tablename__ = "docker_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_date = Column(TIMESTAMP)
    stat_date = Column(DATE, unique=True)
    total_pull_count = Column(INTEGER)
    daily_pull_count = Column(INTEGER)


docker_repositories = ["citus", "membership-manager"]


def fetch_and_store_docker_statistics(repository_name: str, db_user_name: str, db_password: str, db_host_and_port: str,
                                      db_name: str, is_test: bool = False, test_day_shift_index: int = 0,
                                      test_pull_count_shift: int = 0):
    if repository_name not in docker_repositories:
        raise ValueError(f"Repository name should be in {str_array_to_str(docker_repositories)}")
    if not is_test and (test_day_shift_index > 0 or test_pull_count_shift > 0):
        raise ValueError(f"test_day_shift_index and test_pull_count_shift parameters are test parameters. Please "
                         f"don't use these parameters other than testing.")

    result = requests.get(f"https://hub.docker.com/v2/repositories/citusdata/{repository_name}/")
    total_pull_count = int(result.json()["pull_count"]) + test_pull_count_shift

    db_engine = create_engine(
        db_connection_string(user_name=db_user_name, password=db_password, host_and_port=db_host_and_port,
                             db_name=db_name, is_test=is_test))
    Session = sessionmaker(db_engine)
    session = Session()

    Base.metadata.create_all(db_engine)

    fetch_date = datetime.now() + timedelta(days=test_day_shift_index)
    same_day_record = session.query(DockerStats).filter_by(stat_date=fetch_date.date()).first()
    if same_day_record:
        print(f"Docker download record for date {fetch_date.date()} already exists. No need to add record.")
        sys.exit(0)
    last_stat_record = session.query(DockerStats).order_by(desc(DockerStats.stat_date)).first()

    day_diff = (fetch_date.date() - last_stat_record.stat_date).days if last_stat_record else 1
    pull_diff = total_pull_count - last_stat_record.total_pull_count if last_stat_record else total_pull_count
    mod_pull_diff = pull_diff % day_diff
    for i in range(0, day_diff):
        daily_pull_count = (pull_diff - mod_pull_diff) / day_diff if i > 0 else (
                                                                                    pull_diff - mod_pull_diff) / day_diff + mod_pull_diff
        stat_param = DockerStats(fetch_date=fetch_date, total_pull_count=total_pull_count,
                                 daily_pull_count=daily_pull_count,
                                 stat_date=fetch_date.date() - timedelta(days=i))
        session.add(stat_param)
    session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo_name', choices=docker_repositories)
    parser.add_argument('--db_user_name', required=True)
    parser.add_argument('--db_password', required=True)
    parser.add_argument('--db_host_and_port', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--is_test', action="store_true")
    parser.add_argument('--test_day_shift_index', nargs='?', default=0)
    parser.add_argument('--test_pull_count_shift', nargs='?', default=0)

    arguments = parser.parse_args()

    fetch_and_store_docker_statistics(repository_name=arguments.repo_name, is_test=arguments.is_test,
                                      db_user_name=arguments.db_user_name, db_password=arguments.db_password,
                                      db_host_and_port=arguments.db_host_and_port, db_name=arguments.db_name,
                                      test_day_shift_index=int(arguments.test_day_shift_index),
                                      test_pull_count_shift=int(arguments.test_pull_count_shift))
