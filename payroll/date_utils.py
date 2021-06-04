import datetime
import re

from dateutil.rrule import rrule, WEEKLY, MO
from pydantic import validator

from payroll.custom_base_model import CustomBaseModel, validate_date_iso_8601, validate_date_period

_MALTESE_POSTCODE_VALIDATOR = re.compile("^[A-Za-z]{3}\s{0,1}\d{4}")


class Period(CustomBaseModel):
    start: datetime.date = None
    end: datetime.date = None

    @validator("start", "end", pre=True)
    def _validate_date_format(cls, v):
        if v is not None and not validate_date_iso_8601(v):
            raise ValueError("Date must be a valid ISO 8601 format.")
        return v

    @validator("end")
    def _validate_date_order(cls, v, values, **kwargs):
        if v is not None and not validate_date_period(values['start'], v):
            raise ValueError("End date must come after start date")
        return v


def count_days_between_dates(d1: datetime.date,
                             d2: datetime.date,
                             ) -> int:
    """Count the number of days between two dates

    :param d1: first date
    :param d2: second date
    :return: number of days between d1 and d2
    """
    difference = d2 - d1
    return abs(difference.days)


def count_mondays(employee_period: Period, payment_period: Period) -> int:
    """Count the number of Mondays worked by an employee during the specified payroll period

    :param employee_period: period when the employee started and stopped working
    :param payment_period: period to consider
    :return: number of mondays
    """
    period = Period(
        Start=max(employee_period.start, payment_period.start),
        End=min(employee_period.end, payment_period.end) if employee_period.end is not None else payment_period.end
    )
    return len(list(rrule(freq=WEEKLY,
                          byweekday=MO,
                          dtstart=period.start,
                          until=period.end)))


def months_left_in_year(from_month: int) -> int:
    """Count the number of months left in the current year

    :param from_month: month to start counting from
    :return: number of months
    """
    return max(0, 12 - from_month)


def date_within_period(date: datetime.date,
                       period: Period,
                       ) -> bool:
    """
    Check whether a date is within a Period
    :param date: date to consider
    :param period: period to compare to date
    :return: is date within period
    """
    return period.start <= date <= period.end
