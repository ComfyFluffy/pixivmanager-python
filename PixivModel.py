from contextlib import contextmanager
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
    element.collation = None
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
        return value
        # return datetime.fromtimestamp(value) if value else None


works_tags_table = Table(
    'works_tags', Base.metadata,\
    Column('row_id', Integer, primary_key=True),
    Column(
        'works_id',
        Integer,
        ForeignKey('works.works_id'),
        index=True,
        nullable=False),
    Column(
        'tag_id',
        Integer,
        ForeignKey('tags.tag_id'),
        index=True,
        nullable=False))
works_custom_tags_table = Table(
    'works_custom_tags', Base.metadata,
    Column('row_id', Integer, primary_key=True),
    Column(
        'works_id',
        Integer,
        ForeignKey('works.works_id'),
        index=True,
        nullable=False),
    Column(
        'tag_id',
        Integer,
        ForeignKey('custom_tags.tag_id'),
        index=True,
        nullable=False))


class Works(Base):
    __tablename__ = 'works'

    works_id = Column(Integer, index=True, primary_key=True)
    author_id = Column(
        Integer, ForeignKey('users.user_id'), index=True, nullable=False)
    works_type = Column(String(15))
    title = Column(String(256))
    page_count = Column(Integer)
    total_views = Column(Integer)
    total_bookmarks = Column(Integer)
    is_bookmarked = Column(Boolean)
    bookmark_rate = Column(FLOAT)
    create_date = Column(IntegerTimestamp)
    insert_date = Column(IntegerTimestamp, default=datetime.now)

    author = relationship('User', back_populates='works')
    local = relationship('WorksLocal', uselist=False)
    ugoira = relationship('Ugoira', uselist=False)
    caption = relationship('WorksCaption', uselist=False)
    image_urls = relationship('WorksImageURLs')

    tags = relationship('Tag', secondary=works_tags_table, backref='works')
    custom_tags = relationship(
        'CustomTag', secondary=works_custom_tags_table, backref='works')

    def __repr__(self):
        return 'PixivWorks(works_id=%s, author_id=%s, title=%r)' % (
            self.works_id, self.author_id, self.title)

    @classmethod
    def from_json(cls, session: Session, json_info, language,
                  ugoira_json=None):
        j: dict = json_info
        _caption = _bookmark_rate = _create_date = None
        _tags = []
        if j.get('caption'):
            _caption = WorksCaption.get_by_id(session, j['id'])
            _caption.caption_text = j['caption']
        if j.get('total_bookmarks') and j.get('total_view'):
            _bookmark_rate = round(j['total_bookmarks'] / j['total_view'], 5)
        if j.get('tags'):
            _tags = Tag.from_tags_json(session, j['tags'], language)
        if j.get('create_date'):
            _create_date = iso_to_datetime(j.get('create_date'))
        _image_urls = WorksImageURLs.from_works_json(session, j)

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
            kv['ugoira'] = Ugoira.from_json(session, j['id'], ugoira_json)
        w = session.query(cls).filter(
            cls.works_id == kv['works_id']).one_or_none()
        if not w:
            w = cls(**kv)
            # if save_to_session:
            session.add(w)
        else:
            dict_setattr(w, kv)
        return w


class WorksLocal(Base):
    __tablename__ = 'works_local'

    local_id = Column(Integer, primary_key=True, index=True)
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
    def create_if_not_exist(cls, session: Session, works_id):
        w = session.query(WorksLocal).filter(
            WorksLocal.works_id == works_id).one_or_none()
        if not w:
            w = cls(works_id=works_id)
            # if save_to_session:
            session.add(w)
        return w


class User(Base):
    __tablename__ = 'users'

    local_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False, unique=True)
    name = Column(String(256))
    account = Column(String(256))
    is_followed = Column(Boolean)
    insert_date = Column(IntegerTimestamp, default=datetime.now)

    works = relationship('Works', back_populates='author')
    detial = relationship('UserDetail', uselist=False)

    def __repr__(self):
        return 'PixivUser(user_id=%r, name=%r, account=%r, local_id=%r)' % (
            self.user_id, self.name, self.account, self.local_id)

    @classmethod
    def from_json(cls, session: Session, json_info):
        kv = {
            'user_id': json_info['user']['id'],
            'name': json_info['user']['name'],
            'account': json_info['user']['account'],
            'is_followed': json_info['user']['is_followed'],
            'detial': UserDetail.from_user_json(session, json_info)
        }

        u = session.query(cls).filter(
            cls.user_id == kv['user_id']).one_or_none()
        if not u:
            u = cls(**kv)
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


class UserDetail(Base):
    __tablename__ = 'users_details'

    user_id = Column(
        Integer, ForeignKey('users.user_id'), primary_key=True, index=True)
    total_illusts = Column(Integer)
    total_manga = Column(Integer)
    total_novels = Column(Integer)
    avatar_url = Column(String(256))
    background_url = Column(String(256))
    comment = Column(Text)

    @classmethod
    def from_user_json(cls, session: Session, json_info,
                       save_to_session=False):
        kv = {
            'user_id': json_info['user']['id'],
            'total_illusts': json_info['profile']['total_illusts'],
            'total_manga': json_info['profile']['total_manga'],
            'total_novels': json_info['profile']['total_novels'],
            'avatar_url': json_info['user']['profile_image_urls']['medium'],
            'background_url': json_info['profile']['background_image_url'],
            'comment': json_info['user']['comment']
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


class Ugoira(Base):
    __tablename__ = 'ugoiras'

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    delay_text = Column(Text)
    zip_url = Column(String(256))

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
                  save_to_session=False):
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


class WorksImageURLs(Base):
    __tablename__ = 'works_image_urls'

    def __repr__(self):
        return 'WorksImageURLs(works_id=%s,original=%r)' \
            % (self.works_id, self.original)

    works_id = Column(
        Integer, ForeignKey('works.works_id'), primary_key=True, index=True)
    page = Column(Integer, primary_key=True)
    square_medium = Column(String(256))
    medium = Column(String(256))
    large = Column(String(256))
    original = Column(String(256))

    @classmethod
    def get_by_id(cls,
                  session: Session,
                  works_id,
                  page,
                  create_if_not_exist=True,
                  save_to_session=False):
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
                        save_to_session=False):
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
    def get_by_id(cls, session: Session, works_id, save_to_session=False):
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
        String(256, collation='utf8mb4_0900_as_cs'),
        index=True,
        nullable=False,
        unique=True)

    translation = relationship('TagTranslation', lazy='dynamic')

    # def __str__(self):
    #     return str(self.tag_text)

    def __repr__(self):
        return 'Tag(tag_id=%r, tag_text=%r)' % (self.tag_id, self.tag_text)

    def get_translate(self, language):
        return self.translation.filter(TagTranslation.language == language)

    @classmethod
    def from_tags_json(cls, session: Session, tags: list, language: str):
        r = []
        _tags = set()
        for _t in tags:
            t_name = _t['name']
            t_translate = _t.get('translated_name')
            if t_name in _tags:
                continue
            _tags.add(t_name)

            t = session.query(cls).filter(cls.tag_text == t_name).one_or_none()
            if not t:
                t = cls(tag_text=t_name)
                session.add(t)
                session.flush()
            if t_translate:
                TagTranslation.save(session, t.tag_id, language, t_translate)
            r.append(t)
        return r


class TagTranslation(Base):
    __tablename__ = 'tags_translation'

    tag_id = Column(
        Integer, ForeignKey('tags.tag_id'), primary_key=True, index=True)
    language = Column(String(16), primary_key=True, index=True)
    translation_text = Column(String(256), nullable=False)

    def __repr__(self):
        return 'TagTranslation(tag_id=%s, lang=%r, translation_text=%r)' % (
            self.tag_id, self.language, self.translation_text)

    @classmethod
    def save(cls, session: Session, tag_id, language, translation_text):
        tt = session.query(cls).filter(cls.tag_id == tag_id,
                                       cls.language == language).one_or_none()
        if not tt:
            tt = cls(
                tag_id=tag_id,
                language=language,
                translation_text=translation_text)
            session.add(tt)
        else:
            tt.translation_text = translation_text
        return tt


class CustomTag(Base):
    __tablename__ = 'custom_tags'

    tag_id = Column(Integer, primary_key=True)
    tag_text = Column(
        String(256, collation='utf8mb4_0900_as_cs'),
        index=True,
        nullable=False,
        unique=True)

    def __str__(self):
        return str(self.tag_text)

    def __repr__(self):
        return 'CustomTag(tag_id=%r, tag_text=%r)' % (self.tag_id,
                                                      self.tag_text)


class PixivDB:
    def __init__(self, database_uri: str, create_tables=True, **kwargs):
        self.engine = create_engine(database_uri, pool_pre_ping=True, **kwargs)
        if create_tables:
            Base.metadata.create_all(self.engine)
        self.sessionmaker = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self, readonly=True) -> Session:
        def no_write(*args, **kwargs):
            pass

        s: Session = self.sessionmaker()
        if readonly:
            s.autoflush = False
            s.flush = no_write
            s.commit = no_write
        try:
            yield s
        except:
            s.rollback()
            raise
        finally:
            s.close()


if __name__ == "__main__":
    import PixivConfig

    pcfg = PixivConfig.PixivConfig('config.json')
    pdb = PixivDB(pcfg.database_uri, echo=True)
    s = pdb.sessionmaker()
