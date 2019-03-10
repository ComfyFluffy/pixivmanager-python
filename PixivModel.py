from datetime import datetime

from sqlalchemy import (FLOAT, BigInteger, Boolean, Column, ForeignKey,
                        Integer, String, Table, Text, UniqueConstraint,
                        create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.sql import exists
from sqlalchemy.types import TypeDecorator
from PixivConfig import iso_to_datetime

Base = declarative_base()


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
    Column(
        'works_id',
        Integer,
        ForeignKey('works.works_id'),
        index=True,
        primary_key=True),
    Column(
        'tag_id',
        Integer,
        ForeignKey('tags.tag_id'),
        index=True,
        primary_key=True))
works_custom_tags_table = Table(
    'works_custom_tags', Base.metadata,
    Column(
        'works_id',
        Integer,
        ForeignKey('works.works_id'),
        index=True,
        primary_key=True),
    Column(
        'custom_tag_id',
        Integer,
        ForeignKey('custom_tags.custom_tag_id'),
        index=True,
        primary_key=True))


class Works(Base):
    __tablename__ = 'works'

    local_id = Column(Integer, primary_key=True)
    works_id = Column(Integer, index=True, nullable=False, unique=True)
    author_id = Column(
        Integer, ForeignKey('users.user_id'), index=True, nullable=False)
    works_type = Column(String(15))
    title = Column(String(255))
    page_count = Column(Integer)
    total_views = Column(Integer)
    total_bookmarks = Column(Integer)
    is_bookmarked = Column(Boolean)
    bookmark_rate = Column(FLOAT)
    create_date = Column(IntegerTimestamp)
    insert_date = Column(IntegerTimestamp, default=datetime.now)

    author = relationship('User', back_populates='works')
    ugoira = relationship('Ugoira', uselist=False)
    caption = relationship('WorksCaption', uselist=False)

    tags = relationship('Tag', secondary=works_tags_table, backref='works')
    custom_tags = relationship(
        'CustomTag', secondary=works_custom_tags_table, backref='works')

    def __str__(self):
        return f'PixivWorks: {self.works_id} | {self.title}'

    def __repr__(self):
        return f'PixivWorks(works_id={self.works_id}, author_id={self.author_id}, title={self.title}, local_id={self.local_id})'

    @classmethod
    def from_json(cls, json_info, session: Session):
        j = json_info
        if j['caption']:
            _caption = WorksCaption.get_works_caption(session, j['id'])
            _caption.caption_text = j['caption']

        if j['total_bookmarks'] and j['total_view']:
            _bookmark_rate = round(j['total_bookmarks'] / j['total_view'], 5)

        if j['tags']:
            _tags = Tag.get_tags_list([t['name'] for t in j['tags']], session)

        kv = {
            'works_id': j['id'],
            'author_id': j['user']['id'],
            'works_type': j['type'],
            'title': j['title'],
            'page_count': j['page_count'],
            'total_views': j['total_view'],
            'total_bookmarks': j['total_bookmarks'],
            'is_bookmarked': j['is_bookmarked'],
            'bookmark_rate': _bookmark_rate,
            'caption': _caption,
            'create_date': iso_to_datetime(j['create_date']),
            'tags': _tags
        }

        w = session.query(cls).filter(
            cls.works_id == kv['works_id']).one_or_none()
        if not w:
            w = cls(**kv)
            session.add(w)
        else:
            w(**kv)
        return w


class User(Base):
    '''
    user_id, name, account, is_followed, total_illusts, total_manga, total_novels,(insert_date)
    '''
    __tablename__ = 'users'

    local_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False, unique=True)
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
        return f'PixivUser(user_id={self.user_id}, name={self.name}, account={self.account}, local_id={self.local_id})'

    @classmethod
    def from_json(cls, session: Session, json_info):
        kv = {
            'user_id': json_info['user']['id'],
            'name': json_info['user']['name'],
            'account': json_info['user']['account'],
            'is_followed': json_info['user']['is_followed'],
            'total_illusts': json_info['profile']['total_illusts'],
            'total_manga': json_info['profile']['total_manga'],
            'total_novels': json_info['profile']['total_novels']
        }

        u = session.query(cls).filter(
            cls.user_id == kv['user_id']).one_or_none()
        if not u:
            u = cls(**kv)
            session.add(u)
        else:
            u(**kv)
        return u


class Ugoira(Base):
    __tablename__ = 'ugoiras'

    works_id = Column(Integer, ForeignKey('works.works_id'), primary_key=True)
    delay_text = Column(Text)
    zip_url = Column(String(255))

    _delay = []

    @classmethod
    def fron_json(cls, session, ugoira_json):
        _delay = [f['delay'] for f in ugoira_json['ugoira_metadata']['frames']]

        kv = {
            'zip_url': ugoira_json['ugoira_metadata']['zip_urls']['medium'],
            'delay_text': ' '.join([str(d) for d in _delay]),
            '_delay': _delay
        }

        return cls(**kv)

    @property
    def delay(self):
        return self._delay or [int(d) for d in self.delay_text.split()]


# class WorksImageURLs(Base):
#     __tablename__ = 'works_image_urls'

#     works_id = Column(
#         Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
#     page = Column(Integer, primary_key=True)
#     large = Column(String(255))
#     medium = Column(String(255))
#     square_medium = Column(String(255))
#     original = Column(String(255))


class WorksCaption(Base):
    __tablename__ = 'works_captions'

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    caption_text = Column(Text)

    def __str__(self):
        return str(self.caption_text)

    def __repr__(self):
        return 'WorksCaption(works_id=%r, caption_text=%r)' % self.works_id, self.caption_text

    @classmethod
    def get_works_caption(cls, session: Session, _works_id):
        c = session.query(cls).filter(cls.works_id == _works_id).one_or_none()
        if not c:
            c = cls(works_id=_works_id)
        return c


class Tag(Base):
    __tablename__ = 'tags'

    tag_id = Column(Integer, primary_key=True)
    tag_text = Column(
        String(255, collation='utf8mb4_0900_as_cs'),
        index=True,
        nullable=False,
        unique=True)

    def __str__(self):
        return str(self.tag_text)

    def __repr__(self):
        return f'Tag(tag_id={self.tag_id}, tag_text={self.tag_text})'

    @classmethod
    def get_tags_list(cls, tags: list, session: Session):
        l = []
        for ts in tags:
            t = session.query(cls).filter(cls.tag_text == ts).one_or_none()
            if not t:
                t = cls(tag_text=ts)
            l.append(t)
        return l


class CustomTag(Base):
    __tablename__ = 'custom_tags'

    custom_tag_id = Column(Integer, primary_key=True)
    custom_tag_text = Column(
        String(255, collation='utf8mb4_0900_as_cs'),
        index=True,
        nullable=False,
        unique=True)

    def __str__(self):
        return str(self.custom_tag_text)

    def __repr__(self):
        return f'CustomTag(custom_tag_id={self.custom_tag_id}, custom_tag_text={self.custom_tag_text})'

    @classmethod
    def get_custom_tags_list(cls, custom_tags: list, session: Session):
        l = []
        for ts in custom_tags:
            t = session.query(cls).filter(
                cls.custom_tag_text == ts).one_or_none()
            if not t:
                t = cls(tag_text=ts)
            l.append(t)
        return l


if __name__ == "__main__":
    DB_CONNECT = 'sqlite:///storage/sqlalchemytest.db'

    engine = create_engine(DB_CONNECT, echo=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    s = S()
