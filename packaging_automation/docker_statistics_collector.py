import argparse
import sys
from datetime import datetime, timedelta

import requests
from sqlalchemy import Column, DATE, INTEGER, TIMESTAMP, desc

from .common_tool_methods import str_array_to_str
from .dbconfig import Base, DbParams, db_session


class DockerStats(Base):
    __tablename__ = "docker_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_date = Column(TIMESTAMP)
    stat_date = Column(DATE, unique=True)
    total_pull_count = Column(INTEGER)
    daily_pull_count = Column(INTEGER)


docker_repositories = ["citus", "membership-manager"]


def fetch_and_store_docker_statistics(
    repository_name: str,
    db_parameters: DbParams,
    is_test: bool = False,
    test_day_shift_index: int = 0,
    test_total_pull_count: int = 0,
):
    if repository_name not in docker_repositories:
        raise ValueError(
            f"Repository name should be in {str_array_to_str(docker_repositories)}"
        )
    if not is_test and (test_day_shift_index != 0 or test_total_pull_count != 0):
        raise ValueError(
            "test_day_shift_index and test_total_pull_count parameters are test "
            "parameters. Please don't use these parameters other than testing."
        )

    result = requests.get(
        f"https://hub.docker.com/v2/repositories/citusdata/{repository_name}/",
        timeout=60,
    )
    total_pull_count = (
        int(result.json()["pull_count"])
        if test_total_pull_count == 0
        else test_total_pull_count
    )

    session = db_session(
        db_params=db_parameters, is_test=is_test, create_db_objects=True
    )

    fetch_date = datetime.now() + timedelta(days=test_day_shift_index)
    if same_day_record_exists(fetch_date, session):
        return
    day_diff, mod_pull_diff, pull_diff = calculate_diff_params(
        fetch_date, session, total_pull_count
    )
    for i in range(0, day_diff):
        daily_pull_count = (
            (pull_diff - mod_pull_diff) / day_diff
            if i > 0
            else (pull_diff - mod_pull_diff) / day_diff + mod_pull_diff
        )
        stat_param = DockerStats(
            fetch_date=fetch_date,
            total_pull_count=total_pull_count,
            daily_pull_count=daily_pull_count,
            stat_date=fetch_date.date() - timedelta(days=i),
        )
        session.add(stat_param)
    session.commit()


def calculate_diff_params(fetch_date, session, total_pull_count):
    last_stat_record = (
        session.query(DockerStats).order_by(desc(DockerStats.stat_date)).first()
    )
    day_diff = (
        (fetch_date.date() - last_stat_record.stat_date).days if last_stat_record else 1
    )
    pull_diff = (
        total_pull_count - last_stat_record.total_pull_count
        if last_stat_record
        else total_pull_count
    )
    mod_pull_diff = pull_diff % day_diff
    return day_diff, mod_pull_diff, pull_diff


def same_day_record_exists(fetch_date, session):
    same_day_record = (
        session.query(DockerStats).filter_by(stat_date=fetch_date.date()).first()
    )
    return same_day_record is not None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_name", choices=docker_repositories)
    parser.add_argument("--db_user_name", required=True)
    parser.add_argument("--db_password", required=True)
    parser.add_argument("--db_host_and_port", required=True)
    parser.add_argument("--db_name", required=True)
    parser.add_argument("--is_test", action="store_true")
    parser.add_argument("--test_day_shift_index", nargs="?", default=0)
    parser.add_argument("--test_total_pull_count", nargs="?", default=0)

    arguments = parser.parse_args()
    db_params = DbParams(
        user_name=arguments.db_user_name,
        password=arguments.db_password,
        host_and_port=arguments.db_host_and_port,
        db_name=arguments.db_name,
    )

    fetch_and_store_docker_statistics(
        repository_name=arguments.repo_name,
        is_test=arguments.is_test,
        db_parameters=db_params,
        test_day_shift_index=int(arguments.test_day_shift_index),
        test_total_pull_count=int(arguments.test_total_pull_count),
    )
