from datetime import datetime

from sqlalchemy import (FLOAT, Column, ForeignKey, Integer, Table, String,
                        UniqueConstraint, create_engine, Boolean, BigInteger,
                        Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.types import TypeDecorator

Base = declarative_base()

# WORKS_TYPE_MAP = {'illust': 0, 'manga': 1, 'ugoira': 2}
# WORKS_TYPE_MAP_REVERSE = {0: 'illust', 1: 'manga', 2: 'ugoira'}


class IntegerTimestamp(TypeDecorator):
    impl = BigInteger

    def __init__(self):
        TypeDecorator.__init__(self)

    def process_bind_param(self, value, dialect):
        return int(value.timestamp()) if value else None

    def process_result_value(self, value, dialect):
        return datetime.fromtimestamp(value) if value else None


works_tags_table = Table(
    'works_tags', Base.metadata,
    Column('works_id', Integer, ForeignKey('works.works_id'), index=True),
    Column('tag_id', Integer, ForeignKey('tags.tag_id'), index=True))
custom_works_tags_table = Table(
    'custom_works_tags', Base.metadata,
    Column('works_id', Integer, ForeignKey('works.works_id'), index=True),
    Column(
        'custom_tag_id',
        Integer,
        ForeignKey('custom_tags.custom_tag_id'),
        index=True))


class Works(Base):
    __tablename__ = 'works'

    works_id = Column(
        Integer, primary_key=True, index=True, autoincrement=False)
    author_id = Column(
        Integer, ForeignKey('users.user_id'), index=True, nullable=False)
    works_type = Column(Integer)  #{'illust': 0, 'manga': 1, 'ugoira': 2}
    title = Column(String(255))
    page_count = Column(Integer)
    total_view = Column(Integer)
    total_bookmarks = Column(Integer)
    is_bookmarked = Column(Boolean)
    create_date = Column(IntegerTimestamp)
    caption = Column(Text)
    bookmark_rate = Column(FLOAT)
    local_id = Column(Integer, autoincrement=True)
    insert_date = Column(IntegerTimestamp, default=datetime.now)

    author = relationship('User', back_populates='works')
    image_urls = relationship('WorksImageURLs', uselist=False)
    ugoira = relationship('Ugoira', uselist=False)

    tags = relationship('Tag', secondary=works_tags_table, backref='works')
    custom_tags = relationship(
        'CustomTag', secondary=custom_works_tags_table, backref='works')

    def __str__(self):
        return f'PixivWorks: {self.works_id} | {self.title}'

    def __repr__(self):
        return f'PixivWorks(works_id={self.works_id}, author_id={self.author_id}, works_type={self.works_type}, title={self.title}, page_count={self.page_count})'


class User(Base):
    '''
    user_id, name, account, is_followed, total_illusts, total_manga, total_novels,(insert_date)
    '''
    __tablename__ = 'users'

    user_id = Column(
        Integer, primary_key=True, index=True, autoincrement=False)
    name = Column(String(255))
    account = Column(String(255))
    is_followed = Column(Boolean)
    total_illusts = Column(Integer)
    total_manga = Column(Integer)
    total_novels = Column(Integer)
    insert_date = Column(IntegerTimestamp, default=datetime.now)

    works = relationship('Works', back_populates='author')

    def __str__(self):
        return f'PixivUser: {self.user_id} | {self.name}'

    def __repr__(self):
        return f'PixivUser(user_id={self.user_id}, name={self.name}, account={self.account}, is_followed={self.is_followed}, total_illusts={self.total_illusts})'


class Ugoira(Base):
    __tablename__ = 'ugoiras'

    works_id = Column(Integer, ForeignKey('works.works_id'), primary_key=True)
    delay = Column(Text)
    zip_url = Column(String(255))


class WorksImageURLs(Base):
    __tablename__ = 'works_image_urls'

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    page = Column(Integer, primary_key=True)
    large = Column(String(255))
    medium = Column(String(255))
    square_medium = Column(String(255))
    original = Column(String(255))


class Tag(Base):
    __tablename__ = 'tags'

    tag_id = Column(Integer, primary_key=True)
    tag_text = Column(String(255), index=True, nullable=False, unique=True)

    def __str__(self):
        return self.tag_text

    def __repr__(self):
        return f'Tag(tag_id={self.tag_id}, tag_text={self.tag_text})'


class CustomTag(Base):
    __tablename__ = 'custom_tags'

    custom_tag_id = Column(Integer, primary_key=True)
    custom_tag_text = Column(
        String(255), index=True, nullable=False, unique=True)

    def __str__(self):
        return self.custom_tag_text

    def __repr__(self):
        return f'CustomTag(custom_tag_id={self.custom_tag_id}, custom_tag_text={self.custom_tag_text})'


if __name__ == "__main__":
    DB_CONNECT = 'sqlite:///storage/sqlalchemytest.db'

    engine = create_engine(DB_CONNECT, echo=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    s = S()
