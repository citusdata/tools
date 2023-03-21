import requests
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta

# Define the database connection
db_name = "citus-stats"
db_user = "citus_admin@citus-stats"
db_password = "CtsGreat1923"
db_host = "citus-stats.postgres.database.azure.com"
db_port = "5432"
engine = create_engine(
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# Define the model for the download numbers
class DownloadNumbers(Base):
    __table_name__ = "pypi_downloads"

    id = Column(Integer, primary_key=True)
    fetch_date = Column(Date)
    library_name = Column(String)
    download_count = Column(Integer)
    download_date = Column(Date)


# Retrieve the download numbers from PyPI for the last 7 days
package_name = "django-multitenant"
days_to_retrieve = 7
dates = [date.today() - timedelta(days=i) for i in range(days_to_retrieve)]
download_numbers = []
for date in dates:
    url = f"https://pypistats.org/api/packages/{package_name}/{date.isoformat()}/last"
    response = requests.get(url)
    download_numbers.extend(response.json()["data"])

# Save the download numbers to the database
session = Session()
for downloads in download_numbers:
    existing_record = (
        session.query(DownloadNumbers)
        .filter_by(
            library_name=package_name,
            downloads=downloads["downloads"],
            date=downloads["date"],
        )
        .first()
    )
    if not existing_record:
        record = DownloadNumbers(
            fetch_date=date.today(),
            library_name=package_name,
            downloads=downloads["downloads"],
            date=downloads["date"],
        )
        session.add(record)

session.commit()
