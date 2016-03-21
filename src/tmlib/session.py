from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

url = 'postgresql://{user}:{password}@{host}:{port}/tissuemaps'.format(
                    user='markus', password='123', host='localhost', port=5432)
engine = create_engine(url)
Session = sessionmaker(bind=engine)

with Session() as session:
    session.query()
