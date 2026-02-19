from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func

from session import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    #Create
    def create(self, db: Session, obj_in: Dict[str, Any]) -> ModelType:
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            raise e
    
    #get by id
    def get_by_id(self, db: Session, id: int) -> Optional[ModelType]:
        return db.get(self.model, id)
    
    #get all
    def get_all(self, db: Session, offset: int = 0, limit: int = 10) -> List[ModelType]:
        stmt = select(self.model).offset(offset).limit(limit)
        return db.execute(stmt).scalars().all()

    
    #update
    def update(self, db: Session, id: int, update_data: Dict[str, Any]) -> ModelType:
        try:
            db_obj = self.get_by_id(db, id)
            for field, value in update_data.items():
                setattr(db_obj, field, value)

            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            raise e
    
    #delete
    def delete(self, db: Session, id: int) -> None:
        try:
            db_obj = self.get_by_id(db, id)
            if db_obj:
                db.delete(db_obj)
                db.commit()
            else:
                raise ValueError("Object not found")
        except SQLAlchemyError as e:
            db.rollback()
            raise e

    # filter    
    def filter(
        self,
        db: Session,
        filters: Dict[str, Any],
        offset: int = 0,
        limit: int = 10
    ) -> List[ModelType]:
        query = select(self.model)

        for field, value in filters.items():
            query = query.where(getattr(self.model, field) == value)

        query = query.offset(offset).limit(limit)
        return db.execute(query).scalars().all()

    # count
    def count(self, db: Session) -> int:
        stmt = select(func.count()).select_from(self.model)
        return db.execute(stmt).scalar_one()

    # bulk create
    def bulk_create(self, db: Session, objs: List[Dict[str, Any]]):
        try:
            db.bulk_insert_mappings(self.model, objs)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise e

from models import Review, ReviewFile, Issue, Metrics, Suggestion

review_crud = CRUDBase(Review)
review_file_crud = CRUDBase(ReviewFile)
issue_crud = CRUDBase(Issue)
metric_crud = CRUDBase(Metrics)
suggestion_crud = CRUDBase(Suggestion)
