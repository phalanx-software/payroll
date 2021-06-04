import calendar
from datetime import date
from pathlib import Path
from typing import Iterable

import pdfkit
import yaml
from jinja2 import FileSystemLoader, select_autoescape, Environment
from pydantic.types import Decimal

from payroll.calculation import (
    TaxDue, NetPay, ZeroCalculation, TotalDeductions, MaternityFundContribution, SocialSecurityContribution,
    IncomeTaxFullTime, TotalTaxableGrossEmoluments, StatutoryBonus, BasicPayFullTime, PriorGrossEmoluments, Calculator,
    Reimbursements, BasicPayPartTime, IncomeTaxPartTime, ManualAdjustments)
from payroll.custom_base_model import TaxComputation
from payroll.date_utils import count_mondays, Period
from payroll.employee import FilesystemEmployeeStore
from payroll.final_settlement_forms import GeneratorFS3, GeneratorFS5, GeneratorFS7
from payroll.line_item import Items
from payroll.organisation import load_organisation_from_file
from payroll.payment import FilesystemPaymentStore, Payment
from payroll.transactions import Reimbursement, FilesystemTransactionStore, WorkLog, ManualAdjustment

_PART_TIME_TAX_RATE = 0.15


class Payroll:
    """
    Implements the Payroll command of the tool: executes the Payroll for a given year/month, generating new payments
    calculating the amount payable to each employee configured in the system.
    """

    def __init__(self,
                 root_path: Path):
        self.__root_path = root_path
        self.__organisation = load_organisation_from_file(root_path.joinpath("organisation.yml"))
        self.__employee_store = FilesystemEmployeeStore(root_path.joinpath("employees"))
        self.__payment_store = FilesystemPaymentStore(root_path.joinpath("payments"))
        self.__jinja = Environment(
            loader=FileSystemLoader(root_path.joinpath("templates")),
            autoescape=select_autoescape(['html'])
        )

    def fs3_generator(self) -> GeneratorFS3:
        return GeneratorFS3(self.__organisation, self.__root_path.joinpath("tax-fs3"), self.__employee_store,
                            self.__payment_store)

    def fs5_generator(self) -> GeneratorFS5:
        return GeneratorFS5(self.__organisation, self.__root_path.joinpath("tax-fs5"), self.__payment_store)

    def fs7_generator(self) -> GeneratorFS7:
        return GeneratorFS7(self.__organisation, self.__root_path.joinpath("tax-fs7"),
                            self.__root_path.joinpath("tax-fs3"))

    def execute(self, year: int, month: int) -> Iterable[Payment]:
        calculations = {
            "prior_gross_emoluments": PriorGrossEmoluments(),
            "manual_adjustments": ManualAdjustments(
                FilesystemTransactionStore(ManualAdjustment, self.__root_path.joinpath("manualadjustments"))),
            "basic_pay_full_time": BasicPayFullTime(),
            "basic_pay_part_time": BasicPayPartTime(
                FilesystemTransactionStore(WorkLog, self.__root_path.joinpath("worklogs"))),
            "statutory_bonus": StatutoryBonus(
                self.__root_path.joinpath("tables").joinpath(F"{year}-statutory-bonus.csv")),
            "total_taxable_gross_emoluments": TotalTaxableGrossEmoluments(),
            "prior_income_tax_deduction": ZeroCalculation(),
            "income_tax_full_time": IncomeTaxFullTime(
                self.__root_path.joinpath("tables").joinpath(F"{year}-income-tax-single.csv")),
            "income_tax_part_time": IncomeTaxPartTime(Decimal(_PART_TIME_TAX_RATE)),
            "social_security_contribution_employee": SocialSecurityContribution(
                self.__root_path.joinpath("tables").joinpath(F"{year}-ssc.csv")),
            "social_security_contribution_employer": SocialSecurityContribution(
                self.__root_path.joinpath("tables").joinpath(F"{year}-ssc.csv")),
            "maternity_fund_contribution_employer": MaternityFundContribution(
                self.__root_path.joinpath("tables").joinpath(F"{year}-maternity.csv")),
            "total_deductions": TotalDeductions(),
            "reimbursements": Reimbursements(
                FilesystemTransactionStore(Reimbursement, self.__root_path.joinpath("reimbursements"))),
            "net_pay": NetPay(),
            "tax_due": TaxDue()
        }

        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        period = Period(Start=start, End=end)

        for employee in self.__employee_store.load(lambda employee: employee.time_worked_in_period(period) > 0):
            historical = self.__payment_store.aggregate_for_employee(employee.key, start.year,
                                                                     lambda payment: payment.period.end < start)
            payment = Payment(Organisation=self.__organisation, Employee=employee, Period=period,
                              TimeWorked=employee.time_worked_in_period(period),
                              NumberOfMondays=count_mondays(employee.employment_period(), period),
                              MonthlyWage=employee.monthly_wage.amount, WeeklyWage=employee.weekly_wage.amount,
                              PartTime=employee.tax_computation == TaxComputation.parttime)
            calculator = Calculator(payment, historical, calculations)
            payment.items = Items(**{key: calculator.value_of(key) for key in calculations.keys()})
            yield payment

    def payments(self, year: int, month: int):
        for payment in self.execute(year, month):
            subpath = self.__root_path.joinpath(
                F"payments/{payment.employee.key}/{year}/{year}-{month:0>2}-payment-{payment.employee.key}.yml")
            subpath.parent.mkdir(parents=True, exist_ok=True)
            with open(subpath, "w") as payment_file:
                serialized = payment.dict(by_alias=True, exclude_none=True, exclude={"line_items"})
                yaml.dump(serialized, payment_file, default_flow_style=False, sort_keys=False)

    def payslips(self, year: int, month: int, html: bool = True, pdf: bool = True):
        for payment in self.__payment_store.load_for_month(year, month):
            if html:
                subpath = self.__root_path.joinpath(
                    F"payslips/html/{payment.employee.key}/{year}/{year}-{month:0>2}-payslip-{payment.employee.key}.html")
                subpath.parent.mkdir(parents=True, exist_ok=True)
                self.__write_payslip_html(payment, subpath)
            if pdf:
                subpath = self.__root_path.joinpath(
                    F"payslips/pdf/{payment.employee.key}/{year}/{year}-{month:0>2}-payslip-{payment.employee.key}.pdf")
                subpath.parent.mkdir(parents=True, exist_ok=True)
                self.__write_payslip_pdf(payment, subpath)

    def revert(self, year: int, month: int):
        for subpath in self.__root_path.glob(F"payments/*/{year}/{year}-{month:0>2}-payment-*.yml"):
            subpath.unlink()
        for subpath in self.__root_path.glob(F"payslips/pdf/*/{year}/{year}-{month:0>2}-payslip-*.pdf"):
            subpath.unlink()
        for subpath in self.__root_path.glob(F"payslips/html/*/{year}/{year}-{month:0>2}-payslip-*.html"):
            subpath.unlink()

    def __write_payslip_html(self, payment: Payment, subpath: Path):
        template = self.__jinja.get_template(f"payslip_template_basic.html")
        content = template.render(payment.dict())
        with open(subpath, "w") as payslip_file:
            payslip_file.write(content)

    def __write_payslip_pdf(self, payment: Payment, subpath: Path):
        template = self.__jinja.get_template(f"payslip_template_basic.html")
        content = template.render(payment.dict())
        pdfkit.from_string(content, subpath, options={'quiet': '', 'page-size': 'A4', 'dpi': 400})
