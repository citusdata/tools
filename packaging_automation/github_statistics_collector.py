import argparse
from datetime import datetime
from enum import Enum
from typing import Dict, Any

from github import Github
from sqlalchemy import Column, DATE, INTEGER, TIMESTAMP, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .dbconfig import (Base, DbParams, db_session)

ORGANIZATION_NAME = "citusdata"


class GithubRepos(Enum):
    citus = "citus"
    pg_auto_failover = "pg-auto-failover"


class GithubCloneStatsTransactionsMain(Base):
    __tablename__ = "github_stats_clone_transactions_main"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_time = Column(TIMESTAMP, nullable=False)
    repo_name = Column(String, nullable=False)
    count = Column(INTEGER, nullable=False)
    uniques = Column(INTEGER, nullable=False)
    details = relationship("GithubCloneStatsTransactionsDetail", backref="github_stats_clone_transactions_main",
                           lazy=True)


class GithubCloneStatsTransactionsDetail(Base):
    __tablename__ = "github_stats_clone_transactions_detail"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    clone_date = Column(DATE, nullable=False)
    count = Column(INTEGER, nullable=False)
    uniques = Column(INTEGER, nullable=False)
    parent_id = Column(INTEGER, ForeignKey('github_stats_clone_transactions_main.id'), nullable=False)


class GithubCloneStats(Base):
    __tablename__ = "github_clone_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    repo_name = Column(String, nullable=False)
    fetch_time = Column(TIMESTAMP, nullable=False)
    clone_date = Column(DATE, nullable=False)
    count = Column(INTEGER, nullable=False)
    uniques = Column(INTEGER, nullable=False)
    __table_args__ = (UniqueConstraint('repo_name', 'clone_date', name='repo_name_clone_date_uq'),)


def stat_records_exists(record_time: datetime.date, session) -> bool:
    db_record = session.query(GithubCloneStats).filter_by(clone_date=record_time).first()
    return db_record is not None


def github_clone_stats(github_token: str, organization_name: str, repo_name: str) -> Dict[str, Any]:
    g = Github(github_token)
    repo = g.get_repo(f"{organization_name}/{repo_name}")
    return repo.get_clones_traffic(per="day")


def fetch_and_store_github_clones(organization_name: str, repo_name: str, db_parameters: DbParams, github_token: str,
                                  is_test: bool):
    contents = github_clone_stats(github_token, organization_name, repo_name)

    session = db_session(db_parameters, is_test)

    fetch_time = datetime.now()

    main_transaction = GithubCloneStatsTransactionsMain(fetch_time=fetch_time, count=contents['count'],
                                                        repo_name=repo_name, uniques=contents['uniques'])
    for daily_record in contents['clones']:
        detail_transaction = GithubCloneStatsTransactionsDetail(clone_date=daily_record.timestamp,
                                                                count=daily_record.count, uniques=daily_record.uniques)
        main_transaction.details.append(detail_transaction)
        # current date's record is skipped since statistics continue to change until end of the day
        # stat record will not be added if it exists in 'github_clone_stats' table
        if daily_record.timestamp.date() == fetch_time.date() or stat_records_exists(daily_record.timestamp.date(),
                                                                                     session=session):
            continue
        stats_record = GithubCloneStats(fetch_time=fetch_time, clone_date=daily_record.timestamp,
                                        count=daily_record.count, uniques=daily_record.uniques,
                                        repo_name=repo_name)

        session.add(stats_record)

    session.add(main_transaction)

    session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo_name', choices=[r.value for r in GithubRepos])
    parser.add_argument('--db_user_name', required=True)
    parser.add_argument('--db_password', required=True)
    parser.add_argument('--db_host_and_port', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--github_token', required=True)
    parser.add_argument('--is_test', action="store_true")

    arguments = parser.parse_args()

    db_params = DbParams(user_name=arguments.db_user_name, password=arguments.db_password,
                         host_and_port=arguments.db_host_and_port, db_name=arguments.db_name)

    fetch_and_store_github_clones(organization_name=ORGANIZATION_NAME, repo_name=arguments.repo_name,
                                  github_token=arguments.github_token, db_parameters=db_params,
                                  is_test=arguments.is_test)
