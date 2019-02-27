from datetime import datetime

from sqlalchemy import (REAL, Column, DateTime, ForeignKey, Integer, Table,
                        Text, UniqueConstraint, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.types import TypeDecorator

Base = declarative_base()


class IntegerTimestamp(TypeDecorator):
    impl = Integer

    def __init__(self):
        TypeDecorator.__init__(self)

    def process_bind_param(self, value, dialect):
        return int(value.timestamp())

    def process_result_value(self, value, dialect):
        return datetime.fromtimestamp(value)


works_tags_table = Table(
    'works_tags', Base.metadata,
    Column('works_id', Integer, ForeignKey('works.works_id'), index=True),
    Column('tag_id', Integer, ForeignKey('tags.tag_id'), index=True))


class Works(Base):
    __tablename__ = 'works'

    works_id = Column(Integer, primary_key=True, index=True)
    author_id = Column(
        Integer, ForeignKey('users.user_id'), index=True, nullable=False)
    works_type = Column(Integer)
    title = Column(Text)
    page_count = Column(Integer)
    total_view = Column(Text)
    total_bookmarks = Column(Integer)
    is_bookmarked = Column(Integer)
    create_date = Column(DateTime)
    caption = Column(Text)
    bookmark_rate = Column(REAL)
    insert_date = Column(IntegerTimestamp, default=datetime.now())

    author = relationship('User', back_populates='works')
    image_urls = relationship('WorksImageURLs', uselist=False)
    ugoira = relationship('Ugoira', uselist=False)

    tags = relationship('Tag', secondary=works_tags_table, backref='works')

    def __str__(self):
        return f'PixivWorks: {self.works_id} | {self.title}'

    def __repr__(self):
        return f'PixivWorks(works_id={self.works_id}, author_id={self.author_id}, works_type={self.works_type}, title={self.title}, page_count={self.page_count})'


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(Text)
    account = Column(Text)
    is_followed = Column(Integer)
    total_illusts = Column(Integer)
    total_manga = Column(Integer)
    total_novels = Column(Integer)
    insert_date = Column(IntegerTimestamp, default=datetime.now())

    works = relationship('Works', back_populates='author')

    def __str__(self):
        return f'PixivUser: {self.user_id} | {self.name}'

    def __repr__(self):
        return f'PixivUser(user_id={self.user_id}, name={self.name}, account={self.account}), is_followed={self.is_followed}, total_illusts={self.total_illusts}'


class Ugoira(Base):
    __tablename__ = 'ugoiras'

    works_id = Column(Integer, ForeignKey('works.works_id'), primary_key=True)
    delay = Column(Text)
    zip_url = Column(Text)


class WorksImageURLs(Base):
    __tablename__ = 'works_image_urls'

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    page = Column(Integer, primary_key=True)
    large = Column(Text)
    medium = Column(Text)
    square_medium = Column(Text)
    original = Column(Text)


class Tag(Base):
    __tablename__ = 'tags'

    tag_id = Column(Integer, primary_key=True)
    tag_text = Column(Text, index=True, nullable=False,unique=True)

    def __str__(self):
        return self.tag_text

    def __repr__(self):
        return f'Tag(tag_id={self.tag_id}, tag_text={self.tag_text})'


if __name__ == "__main__":
    DB_CONNECT = 'sqlite:///storage/sqlalchemytest.db'

    engine = create_engine(DB_CONNECT, echo=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    s = S()
    tu1 = User(user_id=1, name='xxx')
    tw1 = Works(works_id=1, author_id=1, title='xxxx')
