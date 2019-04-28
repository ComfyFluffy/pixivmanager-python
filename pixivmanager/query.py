from .models import Works, User,WorksCaption
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session


def query_works(title='',caption='') -> Query:
    filters_or = []
    if title:
        filters_or.append(Works.title.like(title))
    if caption:
        filters_or.append(Works.query())
    return Works.query.filter(or_(*filters_or))