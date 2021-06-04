import re
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


def round_decimal(number: Decimal, nearest: int = 2) -> Decimal:
    """
    Round Decimal to the nearest decimal places
    :param number: Decimal to round
    :param nearest: accuracy after the decimal point (default=2)
    :return: rounded number
    """
    return Decimal(round(number, nearest))


def camel_to_snake_case(string: str) -> str:
    """
    Convert CamelCase to snake_case
    :param string: string to convert
    :return: string in snake case
    """
    return ''.join(word.capitalize() for word in string.split('_'))


def validate_maltese_postcode(postcode: str) -> bool:
    """
    Validate format of Maltese postcode
    :param postcode: postcode
    :return: bool
    """
    postcode_re = re.compile("^[A-Za-z]{3}\s{0,1}\d{4}")
    return bool(postcode_re.match(postcode))


def validate_date_iso_8601(d: date) -> bool:
    """
    Validate ISO-8601 date format
    :param d: date
    :return: bool
    """
    iso_8601_re = re.compile("^(?P<year>[0-9]{4})(?P<hyphen>-?)(?P<month>1[0-2]|0[1-9])")
    return bool(iso_8601_re.match(str(d)))


def validate_date_period(start: date,
                         end: date,
                         ) -> bool:
    """
    Validate that the start date occurs before the end date
    :param start: start date
    :param end: end date
    :return: bool
    """
    return start <= end


def validate_monetary_value(n: Decimal) -> bool:
    """
    Validate values referring to a currency value
    :param n: number
    :return: bool
    """
    return n >= 0


def validate_currency_iso_4217(code: str) -> bool:
    """
    Validate format of currency codes in accordance with ISO 4217
    :param data_dir: root data directory
    :param code: currency code
    :return: bool
    """
    with open(f'ISO-4217.csv', 'r') as f:
        for line in f:
            if code in line:
                return True
    return False


class TaxComputation(str, Enum):
    single = "single"
    married = "married"
    parent = "parent"
    parttime = "parttime"


class SocialSecurityCategory(str, Enum):
    A = "A"
    B = "B"
    C_D_1 = "C/D #1"
    C_D_2 = "C/D #2"
    E = "E"
    F = "F"


class CustomBaseModel(BaseModel):
    """Subclass of pydantic BaseModel having common configuration settings"""

    class Config:
        alias_generator = camel_to_snake_case
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
