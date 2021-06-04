import calendar
from abc import abstractmethod
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Callable

from dateutil.relativedelta import relativedelta
from moneyed import Money, EUR

from payroll.custom_base_model import round_decimal, TaxComputation
from payroll.date_utils import count_days_between_dates, months_left_in_year, count_mondays, date_within_period
from payroll.line_item import Items
from payroll.payment import Payment
from payroll.tax_table import MonetaryBonusTable, IncomeTaxTable, CategoryRateTable
from payroll.transactions import TransactionStore


class Calculation:
    @abstractmethod
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        """
        Computes the value of the line item to be assigned to the given payment. The function is provided with
        the aggregated values of all prior payments from the beginning of the year in question up to the beginning
        of this payment's period.

        :param value_of: Use this function to obtain the value computed for another line item, thereby forming a line item
                           dependency. Ensure that there are no circular dependencies between line items.
        :param projection_of: Use this function to obtain the annual projected value for another line item, thereby forming a line item
                              dependency. Ensure that there are no circular dependencies between line items.
        :param payment: The current payment we are computing a value for.
        :param historical: These are the aggregated values of all items by summing up all the previous payments in the
                           year.
        :return: The computed value for the line item for the period represented by this payment
        """
        pass

    def project(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Optional[Money]:
        """
        Computes the annual projected value of this line item. If this line item cannot be projected, this function
        should return None. The function is provided with the aggregated values of all prior payments from the beginning
        of the year in question up to the beginning of this payment's period.

        :param value_of: Use this function to obtain the value computed for another line item, thereby forming a line item
                           dependency. Ensure that there are no circular dependencies between line items.
        :param projection_of: Use this function to obtain the annual projected value for another line item, thereby forming a line item
                              dependency. Ensure that there are no circular dependencies between line items.
        :param payment: The current payment we are computing a value for.
        :param historical: These are the aggregated values of all items by summing up all the previous payments in the
                           year.
        :return: The computed annual projected value for the line item
        """
        return None

    def describe(self, value: Money, payment: Payment, historical: Items) -> Optional[str]:
        """
        Optionally provide a text description that provides additional context for the computation. This text
        description could potentially appear on the payslip issued for the employee.

        :param value: The value computed by this calculation for the current period.
        :param payment: The current payment we are providing a descriptor for.
        :param historical: These are the aggregated values of all items by summing up all the previous payments in the
                           year.
        :return: Text to display, providing context for this calculation, if any
        """
        return None


class ZeroCalculation(Calculation):

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        return Money(Decimal("0.0"), "EUR")


class PriorGrossEmoluments(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        if payment.first_for_employee:
            return Money(payment.employee.prior_tax_information.gross_annual_emoluments, "EUR")
        else:
            return Money(Decimal("0.0"), "EUR")


class ManualAdjustments(Calculation):
    def __init__(self, store: TransactionStore):
        self.__store = store

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        total = Money("0.0", EUR)
        for transaction in self.__store.stream(payment.employee.key, payment.period.start.year,
                            lambda transaction: date_within_period(transaction.dated, payment.period)):
            total += transaction.value
        return total


class BasicPayFullTime(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        if payment.employee.tax_computation == TaxComputation.parttime:
            return Money("0.0", EUR)
        return Money(payment.monthly_wage * payment.time_worked, "EUR").round(2)

    def project(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Optional[Money]:
        if payment.employee.tax_computation == TaxComputation.parttime:
            return historical.basic_pay_full_time
        return value_of("basic_pay_full_time") + historical.basic_pay_full_time \
            + Money(payment.monthly_wage * months_left_in_year(payment.period.end.month), "EUR")

    def describe(self, value: Money, payment: Payment, historical: Items) -> Optional[str]:
        return F"{round_decimal(payment.time_worked)} months"


class BasicPayPartTime(Calculation):
    def __init__(self, store: TransactionStore):
        self.__store = store

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        total = Money("0.0", EUR)
        for transaction in self.__store.stream(payment.employee.key, payment.period.start.year,
                                               lambda transaction: date_within_period(transaction.dated, payment.period)):
            total += transaction.hours * transaction.hourly_wage
        return total

    def describe(self, value: Money, payment: Payment, historical: Items) -> Optional[str]:
        hours = Decimal(0.0)
        for transaction in self.__store.stream(payment.employee.key, payment.period.start.year,
                                               lambda transaction: date_within_period(transaction.dated,
                                                                                      payment.period)):
            hours += transaction.hours
        return F"{hours} hours"


class StatutoryBonus(Calculation):
    __months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

    def __init__(self, statutory_bonus_table_path: Path):
        self.__table = MonetaryBonusTable(statutory_bonus_table_path)

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        bonus = self.__calculate_bonus_for_year_and_month(payment.period.start.year, payment.period.start.month, payment)
        bonus *= Decimal(payment.employee.hours_per_week / 40)
        return Money(bonus, EUR).round(2)

    def project(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Optional[Money]:
        bonus = Decimal(0)
        for month in range(payment.period.start.month, 13):
            bonus += self.__calculate_bonus_for_year_and_month(payment.period.start.year, month, payment)
        bonus *= Decimal(payment.employee.hours_per_week / 40)
        return Money(bonus, EUR).round(2) + historical.statutory_bonus

    def __calculate_bonus_for_year_and_month(self, year, month, payment):
        for entry in self.__table.entries:
            if month == entry.month:
                month_end = date(year, month, calendar.monthrange(year, month)[1])
                date_six_months_ago = month_end - relativedelta(months=6)
                if payment.employee.start_date < date_six_months_ago:
                    return entry.bonus
                else:
                    diff_emp_start = count_days_between_dates(month_end, payment.employee.start_date)
                    diff_six_months = count_days_between_dates(month_end, date_six_months_ago)
                    return entry.bonus * Decimal(diff_emp_start / diff_six_months)
        return Decimal(0.0)


class TotalTaxableGrossEmoluments(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        return (value_of("basic_pay_full_time") + value_of("basic_pay_part_time") + value_of("manual_adjustments") + value_of("statutory_bonus")).round(2)


class IncomeTaxFullTime(Calculation):
    def __init__(self, tax_table_path: Path) -> None:
        self.__table = IncomeTaxTable(filepath=tax_table_path)

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        if payment.employee.tax_computation == TaxComputation.parttime:
            return Money("0.0", EUR)

        remaining_income_tax_payable = projection_of("income_tax_full_time") - historical.income_tax_full_time
        months_remaining = months_left_in_year(payment.period.end.month)
        return (remaining_income_tax_payable * Decimal(payment.time_worked / (payment.time_worked + months_remaining))).round(0)

    def project(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        if payment.employee.tax_computation == TaxComputation.parttime:
            return historical.income_tax_full_time

        projected_prior_gross_emoluments = value_of("prior_gross_emoluments") + historical.prior_gross_emoluments
        projected_basic_pay_full_time = projection_of("basic_pay_full_time")
        projected_manual_adjustments = value_of("manual_adjustments") + historical.manual_adjustments
        projected_statutory_bonus = projection_of("statutory_bonus")

        total_taxable_amount = projected_prior_gross_emoluments + projected_basic_pay_full_time \
                                + projected_manual_adjustments + projected_statutory_bonus
        total_tax_liability = self.__table.apply(total_taxable_amount)

        return max(total_tax_liability - value_of("prior_income_tax_deduction") - historical.prior_income_tax_deduction,
                   historical.income_tax_full_time).round(0)


class IncomeTaxPartTime(Calculation):
    def __init__(self, rate: Decimal) -> None:
        self.__rate = rate

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment, historical: Items) -> Money:
        if payment.employee.tax_computation != TaxComputation.parttime:
            return Money("0.0", EUR)
        return (value_of("total_taxable_gross_emoluments") * self.__rate).round(0)


class SocialSecurityContribution(Calculation):
    def __init__(self, ssc_table_path: Path) -> None:
        self.__table = CategoryRateTable(filepath=ssc_table_path)

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        if not payment.employee.pays_social_security_contributions:
            return Money("0.0", EUR)

        mondays = count_mondays(payment.employee.employment_period(), payment.period)
        return (self.__table.apply(payment.employee.social_security_category, Money(payment.weekly_wage, "EUR")) * mondays).round(2)

    def describe(self, value: Money, payment: Payment, historical: Items) -> Optional[str]:
        mondays = count_mondays(payment.employee.employment_period(), payment.period)
        return F"{mondays} weeks"


class MaternityFundContribution(Calculation):
    def __init__(self, maternity_fund_table_path: Path) -> None:
        self.__table = CategoryRateTable(filepath=maternity_fund_table_path)

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        mondays = count_mondays(payment.employee.employment_period(), payment.period)
        return (self.__table.apply(payment.employee.social_security_category, Money(payment.weekly_wage, "EUR")) * mondays).round(2)

    def describe(self, value: Money, payment: Payment, historical: Items) -> Optional[str]:
        mondays = count_mondays(payment.employee.employment_period(), payment.period)
        return F"{mondays} weeks"


class TotalDeductions(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        return (value_of("income_tax_full_time") + value_of("income_tax_part_time")
                + value_of("social_security_contribution_employee")).round(2)


class Reimbursements(Calculation):
    def __init__(self, store: TransactionStore):
        self.__store = store

    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        total = Money("0.0", EUR)
        for transaction in self.__store.stream(payment.employee.key, payment.period.start.year,
                            lambda transaction: date_within_period(transaction.dated, payment.period)):
            total += transaction.value
        return total


class NetPay(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        return (value_of("total_taxable_gross_emoluments") + value_of("reimbursements") - value_of("total_deductions")).round(2)


class TaxDue(Calculation):
    def compute(self, value_of: Callable[[str], Money], projection_of: Callable[[str], Money], payment: Payment,
                historical: Items) -> Money:
        return value_of("income_tax_full_time") + value_of("income_tax_part_time") \
            + value_of("social_security_contribution_employee") + value_of("social_security_contribution_employer") \
            + value_of("maternity_fund_contribution_employer")


class Calculator:
    def __init__(self,
                 payment: Payment,
                 historical: Items,
                 calculations: Dict[str, Calculation]):
        self.__payment = payment
        self.__historical = historical
        self.__calculations = calculations

        self.__values = Items()
        self.__projections = Items()

    def value_of(self, line_item_name: str) -> Money:
        """
        Get the currently computed value of a particular line item in the current payment. If the value is not yet
        computed, the system will compute it, thereby creating a dependency between two different line items. Developers
        must be careful not to create circular dependencies as this will cause stack overflows.

        :param line_item_name: The name of the line item to obtain a value for
        :return: The currently computed value for the given line item
        """
        if getattr(self.__values, line_item_name) is None:
            setattr(self.__values, line_item_name,
                    self.__calculations[line_item_name].compute(self.value_of, self.projection_of, self.__payment, self.__historical))
        return getattr(self.__values, line_item_name)

    def projection_of(self, line_item_name: str) -> Money:
        """
        Get the annual projected value of a particular line item. If the projection is not yet
        computed, the system will compute it, thereby creating a dependency between two different line items. Developers
        must be careful not to create circular dependencies as this will cause stack overflows.

        :param line_item_name: The name of the line item to obtain a projection for
        :return: The annual projected value for the given line item
        :raises ValueError: if the specified line item cannot be projected
        """
        if getattr(self.__projections, line_item_name) is None:
            projection = self.__calculations[line_item_name].project(self.value_of, self.projection_of, self.__payment, self.__historical)
            if projection is None:
                raise ValueError(F"Cannot compute an annual projected value for {line_item_name}")
            setattr(self.__projections, line_item_name, projection)
        return getattr(self.__projections, line_item_name)