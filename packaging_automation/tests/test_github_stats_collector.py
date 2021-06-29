import os
from datetime import datetime

from sqlalchemy import text, create_engine

from ..dbconfig import (db_connection_string, DbParams, db_session)
from ..github_stats_collector import (fetch_and_store_github_clones, GithubCloneStatsTransactionsDetail,
                                      GithubCloneStatsTransactionsMain, GithubCloneStats)

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")
GH_TOKEN = os.getenv("GH_TOKEN")

ORGANIZATION_NAME = "citusdata"
REPO_NAME = "citus"


def test_github_stats_collector():
    db_params = DbParams(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME)
    db = create_engine(db_connection_string(db_params=db_params, is_test=True))
    db.execute(text(f'DROP TABLE IF EXISTS {GithubCloneStatsTransactionsDetail.__tablename__}'))
    db.execute(text(f'DROP TABLE IF EXISTS {GithubCloneStatsTransactionsMain.__tablename__}'))
    db.execute(text(f'DROP TABLE IF EXISTS {GithubCloneStats.__tablename__}'))

    fetch_and_store_github_clones(organization_name=ORGANIZATION_NAME, repo_name=REPO_NAME, github_token=GH_TOKEN,
                                  db_parameters=db_params, is_test=True)

    session = db_session(db_params=db_params, is_test=True)
    records = session.query(GithubCloneStats).all()
    assert len(records) == 13
    first_record = session.query(GithubCloneStats).first()
    session.delete(first_record)
    session.commit()
    records = session.query(GithubCloneStats).all()
    assert len(records) == 12
    fetch_and_store_github_clones(organization_name=ORGANIZATION_NAME, repo_name=REPO_NAME, github_token=GH_TOKEN,
                                  db_parameters=db_params, is_test=True)
    records = session.query(GithubCloneStats).all()
    assert len(records) == 13
    today_record = session.query(GithubCloneStats).filter_by(clone_date=datetime.today())
    assert not today_record.first()
