from typing import Any, ClassVar, Generic, Literal, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import ColumnElement, delete, func, insert, literal, not_, select, update
from sqlalchemy import exists as _exists
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm.strategy_options import _AbstractLoad

from app.core.database.base import Base
from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResult
from app.domain.base import BaseDomain

T = TypeVar(name="T", bound=BaseDomain)
M = TypeVar(name="M", bound=Base)


class BaseRepository(Generic[T, M]):
    __model__: ClassVar[type[M]]

    def __init__(self, session: AsyncSession):
        self.session = session

    def domain_model(self, data: dict[Any, Any], as_domain: Optional[BaseDomain] = None) -> T:
        """
        Takes data as a dictionary and transform it to domain model T. Alternatively, transform it to another
        model by passing `as_domain`

        Arguments:
            `data`: transformation payload
            `as_domain`: alternative model to `T`

        Returns:
            domain model as `T` or the alternative model `as_domain` if passed
        """
        raise NotImplementedError()

    def model(self) -> M:
        """
        Return the SQLAlchemy model utilized
        """
        return self.__model__

    def to_domain_models(self, data: list[dict[Any, Any]], as_domain: Optional[BaseDomain] = None) -> list[T]:
        """
        Take a list of dictionaries and attempt to transform it to a list of `T`. Alternatively, transform it to
        another model by passing `as_domain`

        Arguments:
            `data`: transformation payload
            `as_domain`: alternative model to `T`

        Returns:
            list of domain model as `list[T]`


        """
        result: list[T] = []
        for item in data:
            result.append(self.domain_model(item, as_domain))
        return result

    def _to_data_dict(
        self, data: Union[dict[str, Any], BaseModel], /, *, exclude_none: bool = True, exclude_unset: bool = True
    ) -> dict[str, Any]:
        """
        Ensure that passed payload is a `dict`

        Arguments:
            `data`: payload which is a `dict` or `BaseModel`
            `exclude_none`: if `True`, `None` values will be dropped from a `BaseModel`
            `exclude_unset`: if `True`, values that are ommited will be dropped from a `BaseModel`

        Returns:
            `data` as dictionary
        """
        if isinstance(data, BaseModel):
            return data.model_dump(exclude_none=exclude_none, exclude_unset=exclude_unset, by_alias=False)
        elif isinstance(data, dict):
            return data
        else:
            raise ValueError("Positional argument 'data' is not of type 'BaseModel' or 'dict'")

    def _to_list_data_dict(
        self, data: list[Union[dict[str, Any], BaseModel]], /, *, exclude_none: bool = True, exclude_unset: bool = True
    ) -> list[dict[str, Any]]:
        """
        Ensure payload is a list of `dict`

        Arguments:
            `data`: payload which is a list `dict` or `BaseModel`
            `exclude_none`: if `True`, `None` values will be dropped from a `BaseModel`
            `exclude_unset`: if `True`, values that are ommited will be dropped from a `BaseModel`

        Returns:
            `data` as a list of dictionary
        """
        result: list[dict[str, Any]] = []
        for item in data:
            result.append(self._to_data_dict(item, exclude_none=exclude_none, exclude_unset=exclude_unset))
        return result

    async def get_one_or_none(
        self,
        where_clause: Optional[list[ColumnElement]] = None,
        /,
        *,
        options: Optional[list[_AbstractLoad]] = None,
        domain_model: Optional[BaseDomain] = None,
    ) -> Optional[T]:
        """
        Retrieve a single record or `None` if non-existant

        Arguments:
            `where_clause`: list of conditions.
            `options`: if passed, list of relations to retreive
            `domain_model`: if passed, an alternative transformation domain model is used
        """
        if not where_clause:
            raise ValueError("Must pass some condition to get a value")

        stmt = select(self.__model__).where(*where_clause)

        if isinstance(options, list):
            stmt = stmt.options(*options)

        result = (await self.session.execute(stmt)).scalar_one_or_none()

        if not result:
            return None

        return self.domain_model(result, domain_model)

    async def get_one(
        self,
        where_clause: list[ColumnElement] = None,
        /,
        *,
        options: Optional[list[_AbstractLoad]] = None,
        domain_model: Optional[BaseDomain] = None,
    ) -> Union[T, Type[BaseDomain]]:
        """
        Retrieve a single record, or `throw` a `NotFoundException` if not existing

        Arguments:
            `where_clause`: list of conditions.
            `options`: if passed, list of relations to retreive
            `domain_model`: if passed, an alternative transformation domain model is used
        """
        if not where_clause:
            raise ValueError("Must pass some condition to get a value")

        stmt = select(self.__model__).where(*where_clause)

        if isinstance(options, list):
            stmt = stmt.options(*options)

        result = (await self.session.execute(stmt)).scalar_one_or_none()

        if not result:
            raise NotFoundException

        return self.domain_model(result, domain_model)

    async def get_many(
        self,
        /,
        *,
        where_clause: Optional[list[ColumnElement[bool]]] = None,
        order_clause: Optional[list[InstrumentedAttribute]] = None,
        page: Optional[int] = 1,
        size: Optional[int] = 5,
        options: Optional[list[_AbstractLoad]] = None,
        domain_model: Optional[BaseDomain] = None,
    ) -> PaginatedResult[T]:
        """
        Get a list of records

        Arguments:
            `where_clause`: list of conditions
            `order_clause`: list of fields to order by
            `page`: page number (default is `1`)
            `size`: page size (default is `5`)
            `options`: if passed, list of relations to retreive
            `domain_model`: if passed, an alternative transformation domain model is used

        Returns:
            `PaginatedResult` object
        """
        if not where_clause:
            where_clause = []
        if not order_clause:
            order_clause = []

        offset = (page - 1) * size

        stmt = select(self.__model__).where(*where_clause).order_by(*order_clause).offset(offset).limit(size)

        if options:
            stmt = stmt.options(*options)

        total_count = await self.session.scalar(select(func.count(self.__model__.id)).where(*where_clause))

        result = await self.session.scalars(stmt)

        domain_results = self.to_domain_models(result, domain_model)

        return PaginatedResult(result=domain_results, total_records=total_count, size=size, page=page)

    async def count(self) -> int:
        """
        Count records of a table

        Returns:
            number of records for current table
        """
        return await self.session.scalar(func.count(self.model().id))

    async def exists_or_not(self, where_clause: list[ColumnElement[bool]] = None, as_not_exists: bool = False) -> bool:
        """
        Check for existance of record(s) based on condition

        Arguments:
            `where_clause`: a list of conditions
            `as_not_exists`: flip condition of exists to check for non-existance

        Returns:
            `True` if exists else `False`
        """
        if not where_clause:
            raise ValueError("Must pass some 'WHERE' clause to get a value")

        subq = _exists().where(*where_clause)

        if as_not_exists:
            subq = not_(subq)

        stmt = select(literal(True)).where(subq)

        result = await self.session.scalar(stmt)

        return bool(result)

    async def create_one(
        self, data: Union[dict, BaseModel], /, *, commit: bool = False, domain_model: Optional[BaseDomain] = None
    ) -> T:
        """
        Create a record from a Dictionary or BaseModel

        Arguments:
            `data`: to be inserted
            `commit`: defaults to `False`
            `domain_model`: if passed, an alternative transformation domain model is used

        Returns:
            Created result of type `T`
        """
        data_json = self._to_data_dict(data)

        obj = self.__model__(**data_json)

        self.session.add(obj)

        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

        return self.domain_model(obj, domain_model)

    async def create_many(
        self, data: list[Union[dict[str, Any], BaseModel]], batch_size: Optional[int] = 1000, /, *, commit: bool = False
    ) -> list[T]:
        """
        Batch create a list of records

        Arguments:
            `data`: payload
            `batch_size`: defaults to `1000`
            `commit`: default to `False`
            `domain_model`: if passed, an alternative transformation domain model is used

        Returns
            Created sequence of results of domain type `list[T]`
        """
        if not isinstance(data, list):
            raise ValueError("positional argument 'data' must be a list")

        if len(data) == 0:
            return []

        data_json: list[dict[str, Any]] = []

        try:
            data_json = self._to_list_data_dict(data)
        except Exception:
            raise ValueError("An item in list is not of compatiable type. Must be either 'BaseModel' or 'dict'")

        result: list[T] = []
        try:
            for batch in range(0, len(data), batch_size):
                data_batch = data_json[batch : batch + batch_size]

                stmt = insert(self.__model__).returning(self.__model__)

                result_batch = (await self.session.scalars(stmt, data_batch)).all()

                result.extend(result_batch)
        except Exception as e:
            print(f"Batch {batch} failed with {str(e)}")
            raise e

        if commit:
            await self.session.commit()

        return self.to_domain_models(result)

    async def update(
        self,
        data: Union[dict[str, Any], BaseModel],
        where_clause: list[ColumnElement[bool]],
        /,
        *,
        commit: bool = False,
        domain_model: Optional[BaseDomain] = None,
    ) -> list[T]:
        """
        Update one or many records based on a condition.

        Arguments:
            `data`: update payload
            `where_clause`: a list of conditions
            `domain_model`: if passed, an alternative transformation domain model is used

        Returns:
            a list of updated records
        """

        try:
            if not where_clause:
                raise ValueError("Must pass some 'WHERE' clause to get a value")

            data_json = self._to_data_dict(data)

            stmt = update(self.model()).where(*where_clause).values(**data_json).returning(self.model())

            result = await self.session.scalars(stmt)

            if commit:
                await self.session.commit()

            return self.to_domain_models(result, domain_model)
        except Exception as e:
            raise e

    async def update_many_by_pk(
        self,
        data: list[Union[dict[str, Any], BaseModel]],
        /,
        *,
        pk: str = "id",
        commit: bool = False,
        domain_model: Optional[BaseDomain] = None,
    ) -> list[T]:
        """
        Similar to method `update` but specifically by `Primary Key` field, this allows to pass
        multiple records at once to be updated. Each record MUST include the `Primary Key` property.

        Arguments:
            `data`: list of records
            `pk`: `primary key` to be used
            `commit`: whether to commit or not
            `domain_model`: if passed, an alternative transformation domain model is used

        Returns:
            a list of updated records

        """
        data_dict = self._to_list_data_dict(data)

        for item in data_dict:
            if not item.get(pk):
                raise ValueError(f"Ensure that all items include PK field: {pk}")

        stmt = update(self.model())
        result = await self.session.execute(stmt, data_dict)

        if commit:
            await self.session.commit()

        ids = [item.get(pk) for item in data_dict]
        refetch_stmt = select(self.__model__).where(self.model().id.in_(ids)).execution_options(populate_existing=True)
        result = await self.session.scalars(refetch_stmt)

        return self.to_domain_models(result.all(), domain_model)

    async def delete(
        self,
        where_clause: list[ColumnElement[bool]],
        /,
        *,
        commit: bool = False,
        domain_model: Optional[BaseDomain] = None,
    ) -> list[T]:
        """
        Delete one or more records based on conditions

        Arguments:
           `where_clause`: list of conditions.
           `commit`: default `False`.
           `domain_model`: if passed, an alternative transformation domain model is used

        Returns:
            deleted records
        """

        if not where_clause:
            raise ValueError("Must pass some 'WHERE' clause to get a value")

        stmt = delete(self.model()).where(*where_clause).returning(self.model())

        results = await self.session.scalars(stmt)

        if commit:
            await self.session.commit()

        return self.to_domain_models(results.all(), domain_model)

    async def upsert(
        self,
        data: list[Union[dict, BaseModel]],
        index_elements: Optional[list[InstrumentedAttribute | str]] = ["id"],
        /,
        *,
        commit: bool = False,
        on_conflict: Literal["do_nothing", "do_update"] = "do_update",
    ) -> list[T]:
        """
        Upsert one or more records

        Arguments:
            `data`: records to be upserted
            `index_elements`: anchor columns to check if already existing.
            `commit`: whether to commit or not. Default is `False`
            `on_conflit`: conflict behaviour. Default is `do_update`

        Returns:
            list of records updated or inserted
        """

        if isinstance(data, list) and len(data) == 0:
            return []

        if not index_elements:
            raise ValueError("Positional argument 'index_elements' cannot be None")

        if not data or not isinstance(data, list):
            raise ValueError("Positional argument 'data' is none or is not a list")

        data_dicts = self._to_list_data_dict(data)

        stmt = pg_insert(self.model())

        if on_conflict == "do_nothing":
            stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
        else:
            columns = self.model().columns()
            update_columns = {
                col.key: getattr(stmt.excluded, col.key)
                for col in columns
                if col.key not in index_elements and not col.primary_key
            }
            stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=update_columns)

        stmt = stmt.returning(self.model())

        result = await self.session.scalars(stmt, data_dicts, execution_options={"populate_existing": True})

        if commit:
            await self.session.commit()

        return self.to_domain_models(result.all())
