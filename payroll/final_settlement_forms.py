import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

import yaml
from moneyed import Money, EUR

from payroll.custom_base_model import SocialSecurityCategory, TaxComputation, CustomBaseModel
from payroll.date_utils import Period
from payroll.employee import Employee, EmployeeStore
from payroll.organisation import Organisation
from payroll.payment import PaymentStore, Payment
from payroll.yaml_utils import decimal_representer, decimal_constructor, enum_representer

yaml.add_representer(Decimal, decimal_representer)
yaml.add_representer(TaxComputation, enum_representer)
yaml.add_representer(SocialSecurityCategory, enum_representer)
yaml.add_constructor(u'!decimal', decimal_constructor)
yaml.Dumper.ignore_aliases = lambda *args: True


class FormBaseFSS(CustomBaseModel):
    dated: datetime.date
    basis_year: int
    payer: Organisation


class FormFS3(FormBaseFSS):
    class Contribution(CustomBaseModel):
        basic_wage: Money
        number_of_mondays: int = 0
        category: str
        social_security_contributions_employee: Money = Money("0.0", EUR)
        social_security_contributions_employer: Money = Money("0.0", EUR)
        social_security_contributions_total: Money = Money("0.0", EUR)
        maternity_fund_contributions: Money = Money("0.0", EUR)

        def process_payment(self, payment: Payment):
            self.number_of_mondays += payment.number_of_mondays
            self.social_security_contributions_employee += payment.items.social_security_contribution_employee
            self.social_security_contributions_employer += payment.items.social_security_contribution_employer
            self.social_security_contributions_total += payment.items.social_security_contribution_employee + payment.items.social_security_contribution_employer
            self.maternity_fund_contributions += payment.items.maternity_fund_contribution_employer

    payee: Employee
    period: Period
    gross_emoluments_full_time: Money = Money(0.0, EUR)
    gross_emoluments_part_time: Money = Money(0.0, EUR)
    total_gross_emoluments_and_fringe_benefits: Money = Money(0.0, EUR)
    income_tax_full_time: Money = Money(0.0, EUR)
    income_tax_part_time: Money = Money(0.0, EUR)
    total_tax_deductions: Money = Money(0.0, EUR)
    social_security_and_maternity_fund_contributions: List[Contribution] = []
    total_social_security_contributions_employee: Money = Money(0.0, EUR)
    total_social_security_contributions_employer: Money = Money(0.0, EUR)
    total_social_security_contributions: Money = Money(0.0, EUR)
    total_maternity_fund_contributions: Money = Money(0.0, EUR)

    def process_payment(self, payment: Payment):
        if payment.employee.tax_computation != TaxComputation.parttime:
            self.gross_emoluments_full_time += payment.items.total_taxable_gross_emoluments
        else:
            self.gross_emoluments_part_time += payment.items.total_taxable_gross_emoluments
        self.total_gross_emoluments_and_fringe_benefits += payment.items.total_taxable_gross_emoluments
        self.income_tax_full_time += payment.items.income_tax_full_time
        self.income_tax_part_time += payment.items.income_tax_part_time
        self.total_tax_deductions += payment.items.income_tax_full_time + payment.items.income_tax_part_time
        self.__select_contribution(Money(payment.weekly_wage, EUR)).process_payment(payment)
        self.total_social_security_contributions_employee += payment.items.social_security_contribution_employee
        self.total_social_security_contributions_employer += payment.items.social_security_contribution_employer
        self.total_social_security_contributions += payment.items.social_security_contribution_employee \
                                                    + payment.items.social_security_contribution_employer
        self.total_maternity_fund_contributions += payment.items.maternity_fund_contribution_employer

    def __select_contribution(self, basic_wage: Money) -> Contribution:
        for contribution in self.social_security_and_maternity_fund_contributions:
            if contribution.basic_wage == basic_wage:
                return contribution
        contribution = FormFS3.Contribution(basic_wage=basic_wage, category="C/D #2")
        self.social_security_and_maternity_fund_contributions = [
            *self.social_security_and_maternity_fund_contributions,
            contribution
        ]
        return contribution


class GeneratorFS3:
    def __init__(self,  payer: Organisation, path: Path, employee_store: EmployeeStore, payment_store: PaymentStore):
        self.__payer = payer
        self.__path = path
        self.__employee_store = employee_store
        self.__payment_store = payment_store

    def compute(self, year: int, employee_key: str) -> FormFS3:
        employee = self.__employee_store.load_by_key(employee_key)
        period = Period(Start=max(datetime.date(year, 1, 1), employee.start_date),
                        End=datetime.date(year, 12, 31) if employee.end_date is None else min(
                            datetime.date(year, 12, 31), employee.end_date))
        form = FormFS3(payer=self.__payer, dated=datetime.date.today(), basis_year=year, payee=employee, period=period)
        for payment in self.__payment_store.load(employee_key, year):
            form.process_payment(payment)
        return form

    def compute_all(self, year: int) -> Iterable[FormFS3]:
        for employee in self.__employee_store.load(lambda e: e.end_date is None or e.end_date.year >= year):
            yield self.compute(year, employee.key)

    def generate(self, year: int, employee_key: str):
        subpath = self.__path.joinpath(F"{year}/{year}-fs3-{employee_key}.yml")
        subpath.parent.mkdir(exist_ok=True, parents=True)
        form = self.compute(year, employee_key)
        with open(subpath, 'w') as f:
            yaml.dump(form.dict(by_alias=True, exclude_none=True), f, sort_keys=False, default_style=False, default_flow_style=False)

    def generate_all(self, year: int):
        for employee in self.__employee_store.load(lambda e: e.end_date is None or e.end_date.year >= year):
            self.generate(year, employee.key)


class FormFS5(FormBaseFSS):
    month: int
    number_of_payees_full_time: int = 0
    number_of_payees_part_time: int = 0
    total_gross_emoluments_full_time: Money = Money(0.0, EUR)
    total_gross_emoluments_part_time: Money = Money(0.0, EUR)
    total_gross_emoluments_and_fringe_benefits: Money = Money(0.0, EUR)
    total_income_tax_full_time: Money = Money(0.0, EUR)
    total_income_tax_part_time: Money = Money(0.0, EUR)
    total_tax_deductions: Money = Money(0.0, EUR)
    total_social_security_contributions: Money = Money(0.0, EUR)
    total_maternity_fund_contributions: Money = Money(0.0, EUR)
    total_tax_due: Money = Money(0.0, EUR)

    def process_payment(self, payment: Payment):
        if payment.employee.tax_computation != TaxComputation.parttime:
            self.number_of_payees_full_time += 1
            self.total_gross_emoluments_full_time += payment.items.total_taxable_gross_emoluments.round(0)
        else:
            self.number_of_payees_part_time += 1
            self.total_gross_emoluments_part_time += payment.items.total_taxable_gross_emoluments.round(0)
        self.total_gross_emoluments_and_fringe_benefits += payment.items.total_taxable_gross_emoluments.round(0)
        self.total_income_tax_full_time += payment.items.income_tax_full_time
        self.total_income_tax_part_time += payment.items.income_tax_part_time
        self.total_tax_deductions += payment.items.income_tax_full_time + payment.items.income_tax_part_time
        self.total_social_security_contributions += payment.items.social_security_contribution_employee + payment.items.social_security_contribution_employer
        self.total_maternity_fund_contributions += payment.items.maternity_fund_contribution_employer
        self.total_tax_due += payment.items.tax_due


class GeneratorFS5:
    def __init__(self, payer: Organisation, path: Path, payment_store: PaymentStore):
        self.__payer = payer
        self.__path = path
        self.__payment_store = payment_store

    def compute(self, year: int, month: int) -> FormFS5:
        form = FormFS5(payer=self.__payer, dated=datetime.date.today(), basis_year=year, month=month)
        for payment in self.__payment_store.load_for_month(year, month):
            form.process_payment(payment)
        return form

    def generate(self, year: int, month: int):
        subpath = self.__path.joinpath(F"{year}/{year}-{month:0>2}-fs5.yml")
        subpath.parent.mkdir(exist_ok=True, parents=True)
        form = self.compute(year, month)
        with open(subpath, 'w') as f:
            yaml.dump(form.dict(by_alias=True, exclude_none=True), f, sort_keys=False, default_style=False, default_flow_style=False)


class FormFS7(FormBaseFSS):
    number_fs3_forms: int = 0
    total_gross_emoluments_full_time: Money = Money(0.0, EUR)
    total_gross_emoluments_part_time: Money = Money(0.0, EUR)
    total_gross_emoluments_and_fringe_benefits: Money = Money(0.0, EUR)
    total_income_tax_full_time: Money = Money(0.0, EUR)
    total_income_tax_part_time: Money = Money(0.0, EUR)
    total_tax_deductions: Money = Money(0.0, EUR)
    total_social_security_contributions: Money = Money(0.0, EUR)
    total_maternity_fund_contributions: Money = Money(0.0, EUR)

    def process_fs3(self, form: FormFS3):
        self.number_fs3_forms += 1
        self.total_gross_emoluments_full_time += form.gross_emoluments_full_time
        self.total_gross_emoluments_part_time += form.gross_emoluments_part_time
        self.total_gross_emoluments_and_fringe_benefits += form.gross_emoluments_full_time + form.gross_emoluments_part_time
        self.total_income_tax_full_time += form.income_tax_full_time
        self.total_income_tax_part_time += form.income_tax_part_time
        self.total_tax_deductions += form.income_tax_full_time + form.income_tax_part_time
        self.total_social_security_contributions += form.total_social_security_contributions
        self.total_maternity_fund_contributions += form.total_maternity_fund_contributions


class GeneratorFS7:
    def __init__(self,  payer: Organisation, path: Path, fs3_store_path: Path):
        self.__payer = payer
        self.__path = path
        self.__fs3_store_path = fs3_store_path

    def compute(self, year: int) -> FormFS7:
        form = FormFS7(payer=self.__payer, dated=datetime.date.today(), basis_year=year)
        for fs3_file in self.__fs3_store_path.joinpath(F"{year}").glob(F"{year}-fs3-*.yml"):
            with open(fs3_file, "r") as fs3_content:
                fs3 = FormFS3(**yaml.load(fs3_content, Loader=yaml.FullLoader))
                form.process_fs3(fs3)
        return form

    def generate(self, year: int):
        subpath = self.__path.joinpath(F"{year}-fs7.yml")
        subpath.parent.mkdir(exist_ok=True, parents=True)
        form = self.compute(year)
        with open(subpath, 'w') as f:
            yaml.dump(form.dict(by_alias=True, exclude_none=True), f, sort_keys=False, default_style=False, default_flow_style=False)