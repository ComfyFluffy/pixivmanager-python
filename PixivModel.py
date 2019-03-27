from datetime import datetime

from sqlalchemy import (FLOAT, BigInteger, Boolean, Column, ForeignKey,
                        Integer, String, Table, Text, create_engine)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import CreateColumn
from sqlalchemy.sql import exists
from sqlalchemy.types import TypeDecorator

from PixivConfig import iso_to_datetime

Base = declarative_base()


def dict_setattr(obj, d: dict):
    for k, v in d.items():
        setattr(obj, k, v)


@compiles(String, 'sqlite')
def skip_sqlite_collation(element, compiler, **kwargs):
    element.collation = ''
    return compiler.visit_VARCHAR(element, **kwargs)


class IntegerTimestamp(TypeDecorator):
    impl = BigInteger

    def __init__(self):
        TypeDecorator.__init__(self)

    def process_bind_param(self, value, dialect):
        if isinstance(value, int):
            return value
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
        'tag_id',
        Integer,
        ForeignKey('custom_tags.tag_id'),
        index=True,
        primary_key=True))


class Works(Base):
    __tablename__ = 'works'

    works_id = Column(Integer, index=True, primary_key=True)
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

    local = relationship('WorksLocal', uselist=False)
    author = relationship('User', back_populates='works')
    ugoira = relationship('Ugoira', uselist=False)
    caption = relationship('WorksCaption', uselist=False)
    image_urls = relationship('WorksImageURLs')

    tags = relationship('Tag', secondary=works_tags_table, backref='works')
    custom_tags = relationship(
        'CustomTag', secondary=works_custom_tags_table, backref='works')

    # def __str__(self):
    #     return f'PixivWorks: {self.works_id} | {self.title}'

    def __repr__(self):
        return f'PixivWorks(works_id={self.works_id}, author_id={self.author_id}, title={self.title})'

    @classmethod
    def from_json(cls,
                  session: Session,
                  json_info,
                  save_to_session=True,
                  ugoira_json=None):
        j: dict = json_info
        _caption = _bookmark_rate = _create_date = None
        _tags = []
        _save = not save_to_session
        if j.get('caption'):
            _caption = WorksCaption.get_by_id(session, j['id'], _save)
            _caption.caption_text = j['caption']
        if j.get('total_bookmarks') and j.get('total_view'):
            _bookmark_rate = round(j['total_bookmarks'] / j['total_view'], 5)
        if j.get('tags'):
            _tags = Tag.from_tags_text_list(session,
                                            [t['name'] for t in j['tags']])
        if j.get('create_date'):
            _create_date = iso_to_datetime(j.get('create_date'))
        _image_urls = WorksImageURLs.from_works_json(session, j, _save)

        kv = {
            'works_id': j['id'],
            'author_id': j['user']['id'],
            'works_type': j.get('type'),
            'title': j.get('title'),
            'page_count': j.get('page_count'),
            'total_views': j.get('total_view'),
            'total_bookmarks': j.get('total_bookmarks'),
            'is_bookmarked': j.get('is_bookmarked'),
            'bookmark_rate': _bookmark_rate,
            'create_date': _create_date
        }
        if _caption:
            kv['caption'] = _caption
        if _tags:
            kv['tags'] = _tags
        if _image_urls:
            kv['image_urls'] = _image_urls
        if ugoira_json:
            kv['ugoira'] = Ugoira.from_json(session, j['id'], ugoira_json,
                                            _save)
        w = session.query(cls).filter(
            cls.works_id == kv['works_id']).one_or_none()
        if not w:
            w = cls(**kv)
            if save_to_session:
                session.add(w)
        else:
            dict_setattr(w, kv)
        return w


class WorksLocal(Base):
    __tablename__ = 'works_local'

    local_id = Column(Integer, primary_key=True)
    works_id = Column(
        Integer,
        ForeignKey('works.works_id'),
        index=True,
        nullable=False,
        unique=True)

    def __repr__(self):
        return 'WorksLocal(local_id=%s, works_id=%s)' % (self.local_id,
                                                         self.works_id)

    @classmethod
    def create_if_not_exist(cls,
                            session: Session,
                            works_id,
                            save_to_session=True):
        w = session.query(WorksLocal).filter(
            WorksLocal.works_id == works_id).one_or_none()
        if not w:
            w = cls(works_id=works_id)
            if save_to_session:
                session.add(w)
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

    # def __str__(self):
    #     return f'PixivUser: {self.user_id} | {self.name}'

    def __repr__(self):
        return f'PixivUser(user_id={self.user_id}, name={self.name}, account={self.account}, local_id={self.local_id})'

    @classmethod
    def from_json(cls, session: Session, json_info, save_to_session=True):
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
            if save_to_session:
                session.add(u)
        else:
            dict_setattr(u, kv)
        return u

    @classmethod
    def create_if_empty(cls, session: Session, user_id, **kwargs):
        if not session.query(exists().where(cls.user_id == user_id)).scalar():
            new_user = cls(user_id=user_id, **kwargs)
            session.add(new_user)
            return new_user


class Ugoira(Base):
    __tablename__ = 'ugoiras'

    works_id = Column(Integer, ForeignKey('works.works_id'), primary_key=True)
    delay_text = Column(Text)
    zip_url = Column(String(255))

    _delay = []

    def __repr__(self):
        return 'Ugoira(works_id=%r, zip_url=%r, delay_text=%s)' % (
            self.works_id, self.zip_url, str(self.delay_text)[:20])

    @property
    def delay(self):
        if not self._delay:
            self._delay = list(map(int, self.delay_text.split()))
        return self._delay

    @classmethod
    def from_json(cls,
                  session: Session,
                  works_id,
                  ugoira_json,
                  save_to_session=True):
        _delay = [f['delay'] for f in ugoira_json['ugoira_metadata']['frames']]

        kv = {
            'works_id': works_id,
            'zip_url': ugoira_json['ugoira_metadata']['zip_urls']['medium'],
            'delay_text': ' '.join(map(str, _delay)),
            '_delay': _delay
        }

        ug = session.query(cls).filter(
            cls.works_id == kv['works_id']).one_or_none()
        if not ug:
            ug = cls(**kv)
            if save_to_session:
                session.add(ug)
        else:
            dict_setattr(ug, kv)
        return ug

    # @classmethod
    # def get_by_id(cls, session: Session, works_id, save_to_session=True):
    #     o = session.query(cls).filter(cls.works_id == works_id).one_or_none()
    #     if not o:
    #         o = cls(works_id=works_id)
    #         if save_to_session:
    #             session.add(o)
    #     return o


class WorksImageURLs(Base):
    __tablename__ = 'works_image_urls'

    def __repr__(self):
        return 'WorksImageURLs(works_id=%s,original=%r)' \
            % (self.works_id, self.original)

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    page = Column(Integer, primary_key=True)
    square_medium = Column(String(255))
    medium = Column(String(255))
    large = Column(String(255))
    original = Column(String(255))

    @classmethod
    def get_by_id(cls,
                  session: Session,
                  works_id,
                  page,
                  create_if_not_exist=True,
                  save_to_session=True):
        o = session.query(cls).filter(cls.works_id == works_id,
                                      cls.page == page).one_or_none()
        if not o and create_if_not_exist:
            o = cls(works_id=works_id, page=page)
            if save_to_session:
                session.add(o)
        return o

    @classmethod
    def from_works_json(cls,
                        session: Session,
                        works_json_info,
                        save_to_session=True):
        r = []
        if works_json_info['page_count'] > 1 and works_json_info['meta_pages']:
            for page, u in enumerate(works_json_info['meta_pages']):
                o = cls.get_by_id(
                    session,
                    works_json_info['id'],
                    page,
                    save_to_session=save_to_session)
                urls = u['image_urls']

                o.square_medium = urls['square_medium']
                o.medium = urls['medium']
                o.large = urls['large']
                o.original = urls['original']

                r.append(o)

        elif works_json_info['page_count'] == 1 and works_json_info[
                'meta_single_page']:
            o = cls.get_by_id(
                session,
                works_json_info['id'],
                0,
                save_to_session=save_to_session)
            urls = works_json_info['image_urls']

            o.square_medium = urls['square_medium']
            o.medium = urls['medium']
            o.large = urls['large']
            o.original = works_json_info['meta_single_page'][
                'original_image_url']

            r.append(o)

        else:
            print('No urls found.')

        if save_to_session:
            session.add_all(r)

        return r


class WorksCaption(Base):
    __tablename__ = 'works_captions'

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    caption_text = Column(Text)

    def __str__(self):
        return str(self.caption_text)

    def __repr__(self):
        return 'WorksCaption(works_id=%r, caption_text=%s)'\
            % (self.works_id, str(self.caption_text)[:20])

    @classmethod
    def get_by_id(cls, session: Session, works_id, save_to_session=True):
        o = session.query(cls).filter(cls.works_id == works_id).one_or_none()
        if not o:
            o = cls(works_id=works_id)
            if save_to_session:
                session.add(o)
        return o


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
        return 'Tag(tag_id=%r, tag_text=%r)' % (self.tag_id, self.tag_text)

    @classmethod
    def from_tags_text_list(cls,
                            session: Session,
                            tags: list,
                            save_to_session=True):
        l = []
        for ts in tags:
            t = session.query(cls).filter(cls.tag_text == ts).one_or_none()
            if not t:
                t = cls(tag_text=ts)
                if save_to_session:
                    session.add(t)
            l.append(t)
        return l


class CustomTag(Base):
    __tablename__ = 'custom_tags'

    tag_id = Column(Integer, primary_key=True)
    tag_text = Column(
        String(255, collation='utf8mb4_0900_as_cs'),
        index=True,
        nullable=False,
        unique=True)

    def __str__(self):
        return str(self.tag_text)

    def __repr__(self):
        return 'CustomTag(tag_id=%r, tag_text=%r)' % (self.tag_id,
                                                      self.tag_text)

    @classmethod
    def from_tags_text_list(cls,
                            session: Session,
                            tags: list,
                            save_to_session=True):
        l = []
        for ts in tags:
            t = session.query(cls).filter(cls.tag_text == ts).one_or_none()
            if not t:
                t = cls(tag_text=ts)
                if save_to_session:
                    session.add(t)
            l.append(t)
        return l


class PixivDB:
    def __init__(self, database_uri: str, create_tables=True, **kwargs):
        self.engine = create_engine(database_uri, **kwargs)
        if create_tables:
            Base.metadata.create_all(self.engine)
        self.sessionmaker = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.sessionmaker()


if __name__ == "__main__":
    import PixivConfig

    pcfg = PixivConfig.PixivConfig('config.json')
    pdb = PixivDB(pcfg.database_uri, echo=True)
