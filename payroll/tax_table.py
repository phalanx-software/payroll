from csv import DictReader
from decimal import Decimal
from enum import Enum
from typing import List

from moneyed import Money
from pydantic import validator, BaseModel

from payroll.custom_base_model import validate_monetary_value, SocialSecurityCategory


class IncomeTaxEntry(BaseModel):
    upto: Decimal
    rate: Decimal
    subtract: Decimal

    @validator("upto")
    def _validate_upto(cls, v):
        if v == -1:
            return Decimal('Infinity')
        elif v < 0:
            return ValueError("upto cannot be < 0")
        return v

    @validator("subtract")
    def _validate_subtract(cls, v):
        if not validate_monetary_value(v):
            raise ValueError("subtract cannot be < 0")
        return v

    @validator("rate")
    def _validate_rate(cls, v):
        if not 0 <= v <= 1.0:
            raise ValueError("rate must be between 0 and 1.0")
        return v


class IncomeTaxTable:
    _entries = []

    def __init__(self, filepath):
        self.load(filepath)

    def load(self, filepath):
        with open(filepath, 'r') as f:
            csv_reader = DictReader(f)
            entries = []
            for row in csv_reader:
                entries.append(IncomeTaxEntry(**row))
            self._entries = entries

    def apply(self, taxable: Money) -> Money:
        for entry in self.entries:
            if entry.upto >= taxable.amount:
                return Money((taxable.amount * entry.rate) - entry.subtract, taxable.currency)
        return Money(Decimal("0.0"), taxable.currency).round(2)

    @property
    def entries(self) -> List[IncomeTaxEntry]:
        return self._entries


class RateType(str, Enum):
    fixed = "Fixed"
    rate = "Rate"


class CategoryRateEntry(BaseModel):
    category: SocialSecurityCategory
    rate_type: RateType
    rate: Decimal
    maximum: Decimal

    @validator("category")
    def _validate_category(cls, v):
        options = ["A", "B", "C/D #1", "C/D #2", "E", "F"]
        if v not in options:
            raise ValueError(f"category must be one of: {options}")
        return v

    @validator("rate_type", pre=True)
    def _validate_rate_type(cls, v):
        options = ['Fixed', 'Rate']
        if v not in options:
            raise ValueError(f"rate_type must be one of: {options}")
        return v

    @validator("rate")
    def _validate_rate(cls, v, values, **kwargs):
        if values['rate_type'] == "Fixed":
            if not v >= 0:
                return ValueError("rate must be >= 0")
        elif values["rate_type"] == "Rate":
            if not 0 <= v <= 1.0:
                raise ValueError("rate must be between 0 and 1.0")
        return v

    @validator("maximum")
    def _validate_subtract(cls, v):
        if not validate_monetary_value(v):
            raise ValueError("subtract cannot be < 0")
        return v


class CategoryRateTable:
    _entries = []

    def __init__(self, filepath):
        self.load(filepath)

    def load(self, filepath):
        with open(filepath, 'r') as f:
            csv_reader = DictReader(f)
            entries = []
            for row in csv_reader:
                entries.append(CategoryRateEntry(**row))
            self._entries = entries

    def apply(self, category: SocialSecurityCategory, weekly_wage: Money):
        for entry in self._entries:
            if category == entry.category:
                if entry.rate_type == "Fixed":
                    total = Money(entry.rate, "EUR")
                else:
                    total = weekly_wage * entry.rate
                return min(total, Money(entry.maximum, "EUR"))

    @property
    def entries(self) -> List[CategoryRateEntry]:
        return self._entries


class MonetaryBonusEntry(BaseModel):
    month: int
    bonus: Decimal

    @validator("month", pre=True)
    def _validate_month(cls, v):
        options = ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]
        if v not in options:
            return ValueError("month is invalid")
        return options.index(v) + 1

    @validator("bonus")
    def _validate_subtract(cls, v):
        if not validate_monetary_value(v):
            raise ValueError("bonus cannot be < 0")
        return v


class MonetaryBonusTable:
    _entries = []

    def __init__(self, filepath):
        self.load(filepath)

    def load(self, filepath):
        with open(filepath, 'r') as f:
            csv_reader = DictReader(f)
            entries = []
            for row in csv_reader:
                entries.append(MonetaryBonusEntry(**row))
            self._entries = entries

    @property
    def entries(self) -> List[MonetaryBonusEntry]:
        return self._entries
