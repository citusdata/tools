from sqlalchemy import Column, Integer, String, Date
from datetime import date, datetime
import pypistats
import json
from .dbconfig import Base, DbParams, db_session
import os


# Define the database connection
db_name = os.getenv(
    "DB_NAME",
)
db_user = os.getenv("DB_USER_NAME")
db_password = os.getenv("DB_PASSWORD")
db_host_and_port = os.getenv("DB_HOST_AND_PORT")

db_params = DbParams(
    user_name=db_user,
    password=db_password,
    host_and_port=db_host_and_port,
    db_name=db_name,
)


# Define the model for the download numbers
class DownloadNumbers(Base):
    __tablename__ = "pypi_downloads"

    id = Column(Integer, primary_key=True)
    fetch_date = Column(Date)
    library_name = Column(String)
    download_count = Column(String)
    download_date = Column(Date)


def fetch_download_numbers(package_name):

    print(
        f"Fetching download numbers for {package_name} from pypi.org. Started at {datetime.now()}"
    )
    download_numbers = json.loads(
        pypistats.overall(package_name, format="json", mirrors=True, total=True)
    )
    session = db_session(db_params=db_params, is_test=False, create_db_objects=True)
    print(
        f"{len(download_numbers['data'])} records fetched from pypi.org. Starting to add to database. Started at {datetime.now()}"
    )

    new_record_count = 0
    existing_record_count = 0
    for downloads in download_numbers["data"]:

        existing_record = (
            session.query(DownloadNumbers)
            .filter_by(
                library_name=package_name,
                download_count=downloads["downloads"],
                download_date=downloads["date"],
            )
            .first()
        )
        if not existing_record:
            new_record_count += 1
            print(f"Adding {package_name} {downloads['downloads']} {downloads['date']}")
            record = DownloadNumbers(
                fetch_date=date.today(),
                library_name=package_name,
                download_count=downloads["downloads"],
                download_date=downloads["date"],
            )
            session.add(record)
        else:
            existing_record_count += 1

    session.commit()
    print(
        f"Process finished. New records: {new_record_count} Existing records: {existing_record_count}. Finished at {datetime.now()}"
    )


packages = ["django-multitenant"]
for package_name in packages:
    fetch_download_numbers(package_name)
