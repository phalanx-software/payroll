import traceback
from abc import abstractmethod
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable, Type, Any

import yaml
from moneyed import Money
from pydantic import ValidationError

from payroll.custom_base_model import CustomBaseModel


class WorkLog(CustomBaseModel):
    """
    A log of hourly work that is paid for and taxed as a part-time emolument.
    """
    employee: str
    dated: date
    hours: Decimal
    hourly_wage: Money


class Reimbursement(CustomBaseModel):
    """
    An expense reimbursement for an employee that is credited alongside their salary. Expense reimbursements are not
    taxed.
    """
    employee: str
    dated: date
    value: Money
    description: str


class ManualAdjustment(CustomBaseModel):
    """
    A one-time payment credited alongside an employee's salary that is likewise taxed.
    """
    employee: str
    dated: date
    value: Money
    description: str


class TransactionStore:
    @abstractmethod
    def stream(self, employee_key: str, year: int, filter: Callable[[Any], bool] = lambda x: True) -> Iterable:
        pass


class FilesystemTransactionStore(TransactionStore):
    def __init__(self, model: Type, path: Path):
        self.__model = model
        self.__path = path

    def stream(self, employee_key: str, year: int, filter: Callable[[Any], bool] = lambda x: True) -> Iterable:
        for subpath in self.__path.joinpath(F"{employee_key}/{year}").glob("*.yml"):
            with open(subpath, "r") as content:
                try:
                    if filter(transaction := self.__model(**yaml.load(content, Loader=yaml.FullLoader))):
                        yield transaction
                except ValidationError:
                    print(traceback.format_exc())
                    print(F"Could not parse transaction: {subpath}")

