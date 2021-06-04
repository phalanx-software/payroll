import traceback
from abc import abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable

import yaml
from pydantic import validator, ValidationError

from payroll.custom_base_model import CustomBaseModel, validate_monetary_value, TaxComputation
from payroll.date_utils import date_within_period, Period
from payroll.employee import Employee
from payroll.line_item import LineItems, Items
from payroll.organisation import Organisation


class Payment(CustomBaseModel):
    organisation: Organisation = None
    employee: Employee = None
    period: Period = None
    time_worked: Decimal = Decimal(0)
    number_of_mondays: int = 0
    monthly_wage: Decimal = Decimal(0)
    weekly_wage: Decimal = Decimal(0)
    line_items: LineItems = LineItems()
    items = Items()
    part_time: bool = False

    @validator("monthly_wage", "weekly_wage")
    def _validate_wage(cls, v):
        if not validate_monetary_value(v):
            raise ValueError(f"wage '{v}'  must be >= 0")
        return v

    @property
    def first_for_employee(self) -> bool:
        """
        Specifies whether this is the employee's very first payment ever.

        :return: True if this is the employee's very first payment ever; False, otherwise
        """
        return date_within_period(self.employee.start_date, self.period)


class PaymentStore:
    @abstractmethod
    def load(self, employee_key: str, year: int, filter: Callable[[Payment], bool] = lambda x: True) -> Iterable[Payment]:
        pass

    @abstractmethod
    def load_for_month(self, year: int, month: int, filter: Callable[[Payment], bool] = lambda x: True) -> Iterable[Payment]:
        pass

    @abstractmethod
    def aggregate_for_employee(self, employee_key: str, year: int, filter: Callable[[Payment], bool] = lambda x: True) -> Items:
        pass


class FilesystemPaymentStore(PaymentStore):
    def __init__(self, path: Path):
        self.__path = path

    def load(self, employee_key: str, year: int, filter: Callable[[Payment], bool] = lambda x: True) -> Iterable[Payment]:
        for subpath in self.__path.joinpath(F"{employee_key}/{year}").glob("*.yml"):
            with open(subpath, "r") as content:
                try:
                    if filter(payment := Payment(**yaml.load(content, Loader=yaml.FullLoader))):
                        if payment.line_items.net_employee_pay.current_period > 0.0:
                            payment.items = payment.line_items.as_items(payment.employee.tax_computation == TaxComputation.parttime)
                        yield payment
                except ValidationError:
                    print(traceback.format_exc())
                    print(F"Could not parse payment: {subpath}")

    def load_for_month(self, year: int, month: int, filter: Callable[[Payment], bool] = lambda x: True) -> Iterable[Payment]:
        for subpath in self.__path.glob(F"*/{year}/{year}-{month:0>2}-*.yml"):
            with open(subpath, "r") as content:
                try:
                    if filter(payment := Payment(**yaml.load(content, Loader=yaml.FullLoader))):
                        if payment.line_items.net_employee_pay.current_period > 0.0:
                            payment.items = payment.line_items.as_items(payment.employee.tax_computation == TaxComputation.parttime)
                        yield payment
                except ValidationError:
                    print(traceback.format_exc())
                    print(F"Could not parse payment: {subpath}")

    def aggregate_for_employee(self, employee_key: str, year: int, filter: Callable[[Payment], bool] = lambda x: True) -> Items:
        accumulator = Items.zero()
        for payment in self.load(employee_key, year, filter):
            accumulator = accumulator + payment.items
        return accumulator
