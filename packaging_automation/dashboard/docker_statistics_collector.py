import sys

from sqlalchemy import create_engine
from sqlalchemy import Column, String, DATE, NUMERIC, INTEGER, TIMESTAMP, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime, timedelta
# from .config import DATABASE_URI
import dbconfig
import requests
import argparse
from ..common_tool_methods import (str_array_to_str)

IS_TEST = False


def get_table_name(table_name: str, is_test: bool = False):
    return table_name if not is_test else f"{table_name}_test"


class DockerStats(dbconfig.Base):
    __tablename__ = get_table_name("docker_stats")
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_date = Column(TIMESTAMP)
    stat_date = Column(DATE, unique=True)
    total_pull_count = Column(INTEGER)
    daily_pull_count = Column(INTEGER)


docker_repositories = ["citus", "membership-manager"]


def fetch_and_store_docker_statistics(repository_name: str, is_test: bool = False, test_day_shift_index: int = 0,
                                      test_pull_count_shift: int = 0):
    if not repository_name and repository_name not in docker_repositories:
        raise ValueError(f"Repository name should be in {str_array_to_str(docker_repositories)}")
    if not is_test and (test_day_shift_index > 0 or test_pull_count_shift > 0):
        raise ValueError(f"test_day_shift_index and  test_pull_count_shift parameters are test parameters. Please "
                         f"don't use these parameters other than testing.")

    result = requests.get(f"https://hub.docker.com/v2/repositories/citusdata/{repository_name}/")
    total_pull_count = result.json()["pull_count"] + test_pull_count_shift

    session = dbconfig.Session()

    dbconfig.Base.metadata.create_all(dbconfig.db)

    fetch_date = datetime.now() + timedelta(days=test_day_shift_index)
    same_day_record = session.query(DockerStats).filter_by(stat_date=fetch_date.date()).first()
    if same_day_record:
        print(f"Docker download record for date {fetch_date.date()} already exists. No Need to add record.")
        sys.exit(0)
    last_stat_record = session.query(DockerStats).order_by(desc(DockerStats.stat_date)).first()

    day_diff = (fetch_date.date() - last_stat_record.stat_date).days if last_stat_record else 1
    pull_diff = total_pull_count - last_stat_record.total_pull_count if last_stat_record else total_pull_count
    for i in range(0, day_diff):
        stat_param = DockerStats(fetch_date=fetch_date, total_pull_count=total_pull_count,
                                 daily_pull_count=pull_diff / day_diff,
                                 stat_date=fetch_date.date() - timedelta(days=i))
        session.add(stat_param)
    session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo_name', choices=docker_repositories)
    parser.add_argument('--prj_name', required=True)
    parser.add_argument('--is_test', action="store_true")
    parser.add_argument('--test_day_shift_index', nargs='?', default=0)
    parser.add_argument('--test_pull_count_shift', nargs='?', default=0)

    arguments = parser.parse_args()

    IS_TEST = arguments.is_test

    fetch_and_store_docker_statistics(arguments.repo_name, arguments.is_test, arguments.test_day_shift_index,
                                      arguments.test_pull_count_shift)
