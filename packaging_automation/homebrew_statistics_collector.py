import argparse
import json
import time
from datetime import datetime, date
from enum import Enum
from http import HTTPStatus
from typing import List, Any

import requests
from sqlalchemy import Column, INTEGER, DATE, TIMESTAMP, String
import sqlalchemy

from .common_tool_methods import (remove_suffix, stat_get_request)
from .dbconfig import (Base, db_session, DbParams, RequestType)

HOMEBREW_STATS_ADDRESS = "https://formulae.brew.sh/api/formula/citus.json"


class HomebrewStats(Base):
    __tablename__ = "homebrew_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_time = Column(TIMESTAMP, nullable=False)
    stat_date = Column(DATE, nullable=False,unique=True)
    stat_30d = Column(INTEGER, nullable=False, default=0,)
    stat_90d = Column(INTEGER, nullable=False, default=0)
    stat_365d = Column(INTEGER, nullable=False, default=0)


def fetch_and_save_homebrew_stats(db_params: DbParams, is_test: bool) -> None:
    session = db_session(db_params=db_params, is_test=is_test)

    result = stat_get_request(HOMEBREW_STATS_ADDRESS, RequestType.homebrew_download, session)
    stat_details = json.loads(result.content)
    record = session.query(HomebrewStats).filter_by(stat_date=date.today()).first()
    if record is None:
        hb_stat = HomebrewStats(fetch_time=datetime.now(), stat_date=date.today(),
                                stat_30d=stat_details["analytics"]["install"]["30d"]["citus"],
                                stat_90d=stat_details["analytics"]["install"]["90d"]["citus"],
                                stat_365d=stat_details["analytics"]["install"]["365d"]["citus"])
        session.add(hb_stat)
        session.commit()
    else:
        print(f"Homebrew stat for the day {date.today()} already exists")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_user_name', required=True)
    parser.add_argument('--db_password', required=True)
    parser.add_argument('--db_host_and_port', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--is_test', action="store_true")

    arguments = parser.parse_args()

    db_parameters = DbParams(user_name=arguments.db_user_name, password=arguments.db_password,
                             host_and_port=arguments.db_host_and_port, db_name=arguments.db_name)

    fetch_and_save_homebrew_stats(db_parameters, arguments.is_test)
