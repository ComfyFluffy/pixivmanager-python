from .models import Works, User, WorksCaption, Tag, TagTranslation
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session, selectinload, joinedload


def query_works(author_include: tuple = None,
                author_exclude: tuple = None,
                works_type: str = None,
                title_like: str = None,
                caption_like: str = None,
                is_bookmarked: bool = None,
                tags_include: tuple = None,
                tags_exclude: tuple = None,
                custom_tags_include: tuple = None,
                custom_tags_exclude: tuple = None,
                page_count_range: tuple = None,
                total_views_range: tuple = None,
                total_bookmarks_range: tuple = None,
                bookmark_rate_range: tuple = None,
                create_date_range: tuple = None,
                insert_date_range: tuple = None,
                order_by: str = 'local_id',
                desc: bool = True) -> Query:
    filters_or = []
    q = Query(Works)
    if title_like:
        filters_or.append(Works.title.like(title_like))
    if caption_like:
        q = q.join(WorksCaption)
        filters_or.append(WorksCaption.caption_text.like(caption_like))
    q = q.filter(or_(*filters_or))
    return q


def query_users(
        name_like: str = None,
        is_followed: bool = None,
        comment_like: str = None,
        insert_date_range: tuple = None,
        total_illusts_range: tuple = None,
        total_manga_range: tuple = None,
        total_novels_range: tuple = None,
        total_illust_bookmarks_public_range: tuple = None,
        total_follow_users_range: tuple = None,
) -> Query:
    pass


def search_works():
    '''Search works in title, caption, tags & tag translations.'''
    pass


def tags_like(term: str, language: str = None, exclude=[], limit=10) -> Query:
    q: Query = Query(Tag).outerjoin(Tag.translation).options(
        selectinload(Tag.translation))
    f_or = [Tag.tag_text.collate('utf8mb4_0900_ai_ci').like(term)]
    if language:
        f_or.append(
            and_(
                TagTranslation.translation_text.like(term),
                TagTranslation.language == language))
    else:
        f_or.append(TagTranslation.translation_text.like(term))
    if exclude:
        q = q.filter(or_(*f_or), Tag.tag_text.notin_(exclude))
    else:
        q = q.filter(or_(*f_or))
    q = q.limit(limit)

    return q
