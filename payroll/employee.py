import datetime
import re
import traceback
from abc import abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Optional, Callable, Iterable

import yaml
from moneyed import Money, EUR
from pydantic import validator, ValidationError

from payroll.custom_base_model import (CustomBaseModel, validate_monetary_value, TaxComputation, SocialSecurityCategory,
                                       validate_maltese_postcode, validate_date_period)
from payroll.date_utils import count_days_between_dates, Period


class PriorTaxInformation(CustomBaseModel):
    gross_annual_emoluments: Decimal = Decimal(0)
    income_tax: Decimal = Decimal(0)

    @validator("gross_annual_emoluments", "income_tax")
    def _validate(cls, v):
        if not validate_monetary_value(v):
            raise ValueError(f"value '{v}' must be >= 0")
        return v


class Employee(CustomBaseModel):
    key: Optional[str]
    identifier: str
    first_name: str
    surname: str
    email: str
    role: str
    address: str
    postcode: Optional[str]
    telephone_number: str
    registration_number: str
    social_security_number: Optional[str] = None
    spouse_registration_number: Optional[str] = None
    start_date: datetime.date
    end_date: Optional[datetime.date] = None
    hours_per_week: int
    tax_computation: TaxComputation
    social_security_category: SocialSecurityCategory
    gross_annual_salary: Decimal
    prior_tax_information: Optional[PriorTaxInformation] = PriorTaxInformation()

    def get_identifier_number(self) -> str:
        """
        Get Employee Identifier numbers without the E-
        :return:
        """
        if self.identifier is not None:
            return self.identifier.split('-')[-1]
        return ""

    @property
    def pays_social_security_contributions(self) -> bool:
        return self.tax_computation != TaxComputation.parttime

    @property
    def monthly_wage(self) -> Money:
        return Money(self.gross_annual_salary / 12, EUR).round(2)

    @property
    def weekly_wage(self) -> Money:
        return Money(self.gross_annual_salary / 52, EUR).round(2)

    def time_worked_in_period(self, payroll_period: Period) -> Decimal:
        """
        Calculate the amount of time an employee worked, as a fraction of the payroll period
        :param payroll_period: the current payroll period
        :return: time worked as a fraction of the period
        """
        if self.start_date > payroll_period.end:
            return Decimal(0)
        elif self.end_date is not None and self.end_date < payroll_period.start:
            return Decimal(0)
        else:
            if self.end_date is not None:
                numerator = count_days_between_dates(min(self.end_date, payroll_period.end),
                                                     max(self.start_date, payroll_period.start)) + 1

            else:
                numerator = count_days_between_dates(payroll_period.end,
                                                     max(self.start_date, payroll_period.start)) + 1
        denominator = count_days_between_dates(payroll_period.end, payroll_period.start) + 1
        return round(Decimal(numerator / denominator), 2)

    @validator("postcode")
    def _validate_maltese_postcode(cls, v):
        if v != "" and not validate_maltese_postcode(v):
            raise ValueError("postcode must match Maltese format (XYZ 1234)")
        return v

    @validator("registration_number", "spouse_registration_number")
    def _validate_registration_number(cls, v):
        maltese_id_re = re.compile("\d{3,7}[MGAPLHBZ]{1}")
        foreign_tax_identifier_number = re.compile("^\d{9}")

        if not maltese_id_re.match(v) and not foreign_tax_identifier_number.match(v):
            raise ValueError("registration number must match Maltese format 3-7 digits and 1 letter")
        return v

    @validator("social_security_number")
    def _validate_social_security_number(cls, v):
        # TODO: implement
        return v

    @validator("end_date")
    def _validate_dates(cls, v, values, **kwargs):
        if not validate_date_period(values['start_date'], v):
            raise ValueError("End date must come after start date")
        return v

    @validator("gross_annual_salary")
    def _validate_gross_annual_salary(cls, v):
        if not validate_monetary_value(v):
            raise ValueError("gross annual emoluments cannot be < 0")
        return v

    @validator("hours_per_week")
    def _validate_hours_per_week(cls, v):
        if v < 0:
            raise ValueError("Hours per week must be >= 0")
        return v

    def employment_period(self):
        return Period(Start=self.start_date, End=self.end_date)


class EmployeeStore:
    @abstractmethod
    def load(self, filter: Callable[[Employee], bool] = lambda: True) -> Iterable[Employee]:
        pass

    @abstractmethod
    def load_by_key(self, key: str) -> Optional[Employee]:
        pass


class FilesystemEmployeeStore(EmployeeStore):
    def __init__(self, path: Path):
        self.__path = path

    def load(self, filter: Callable[[Employee], bool] = lambda x: True) -> Iterable[Employee]:
        for subpath in self.__path.glob("*.yml"):
            with open(subpath, "r") as content:
                try:
                    if filter(employee := Employee(Key=subpath.name.split(".", 2)[0], **yaml.load(content, Loader=yaml.FullLoader))):
                        yield employee
                except ValidationError:
                    print(traceback.format_exc())
                    print(F"Could not parse employee: {subpath}")

    def load_by_key(self, key: str) -> Optional[Employee]:
        subpath = self.__path.joinpath(F"{key}.yml")
        if not subpath.exists():
            return None
        with open(subpath, "r") as content:
            return Employee(Key=subpath.name.split(".", 2)[0], **yaml.load(content, Loader=yaml.FullLoader))