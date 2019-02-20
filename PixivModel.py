from sqlalchemy import Column, Text, create_engine, Integer, REAL, DateTime, Table, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlite3 import IntegrityError
Base = declarative_base()

# DB_CONNECT = 'mysql://root:toor@localhost/test'


#TYPE: 0: illust 1:manga 2: ugoira -1: unknown
class Works(Base):
    __tablename__ = 'works'

    row_id = Column(Integer, primary_key=True, index=True)
    works_id = Column(Integer, unique=True, index=True, nullable=False)
    author_id = Column(Integer, index=True)
    works_type = Column(Integer)
    title = Column(Text)
    caption = Column(Text)
    create_date = Column(DateTime)
    page_count = Column(Integer)
    total_bookmarks = Column(Integer)
    total_view = Column(Text)
    is_bookmarked = Column(Integer)
    bookmark_rate = Column(REAL)


class User(Base):
    __tablename__ = 'users'

    row_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(Text)
    account = Column(Text)
    is_followed = Column(Integer)
    total_illusts = Column(Integer)
    total_manga = Column(Integer)
    total_novels = Column(Integer)
    country_code = Column(Text)


class Ugoira(Base):
    __tablename__ = 'ugoira'

    works_id = Column(Integer, primary_key=True, index=True)
    delay = Column(Text)
    zip_url = Column(Text)


class WorksURLs(Base):
    __tablename__ = 'works_urls'

    row_id = Column(Integer, primary_key=True)
    works_id = Column(Integer)
    page = Column(Integer)
    url = Column(Text)

    UniqueConstraint(works_id, page)


class Tags(Base):
    __tablename__ = 'tags'

    row_id = Column(Integer, primary_key=True, index=True)
    tag_text = Column(Text, index=True)


DB_CONNECT = 'sqlite:///storage/sqlalchemytest.db'

engine = create_engine(DB_CONNECT, echo=True)
Base.metadata.create_all(engine)
S = sessionmaker(bind=engine)
if __name__ == "__main__":
    # engine = create_engine(DB_CONNECT, echo=True)
    # Base.metadata.create_all(engine)
    # S = sessionmaker(bind=engine)
    s = S()
    try:
        s.add(User(user_id=123, name='XXX2'))
    except IntegrityError:
        pass
    s.commit()