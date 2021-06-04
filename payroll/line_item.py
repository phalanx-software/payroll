from decimal import Decimal
from typing import Optional

from moneyed import Money, EUR
from pydantic import validator

from payroll.custom_base_model import validate_monetary_value, CustomBaseModel


class LineItem(CustomBaseModel):
    """
    A single item required to calculate income and taxes
    current_period: amount computed for the current payroll period
    year_to_date: cumulative amount computed since the start of the current year
    projected_yearly: cumulative amount that system projects by end of the year
    """
    current_period: Decimal = Decimal(0)
    year_to_date: Decimal = Decimal(0)
    projected_yearly: Decimal = Decimal(0)

    @validator("current_period", "year_to_date", "projected_yearly")
    def _validate_monetary_values(cls, v):
        if not validate_monetary_value(v):
            raise ValueError(f"amount '{v}' cannot be < 0")
        return v


class Items(CustomBaseModel):
    prior_gross_emoluments: Optional[Money] = None
    basic_pay_full_time: Optional[Money] = None
    basic_pay_part_time: Optional[Money] = None
    manual_adjustments: Optional[Money] = None
    statutory_bonus: Optional[Money] = None
    total_taxable_gross_emoluments: Optional[Money] = None
    prior_income_tax_deduction: Optional[Money] = None
    income_tax_full_time: Optional[Money] = None
    income_tax_part_time: Optional[Money] = None
    social_security_contribution_employee: Optional[Money] = None
    social_security_contribution_employer: Optional[Money] = None
    total_deductions: Optional[Money] = None
    maternity_fund_contribution_employer: Optional[Money] = None
    reimbursements: Optional[Money] = None
    net_pay: Optional[Money] = None
    tax_due: Optional[Money] = None

    @staticmethod
    def zero() -> "Items":
        return Items(
            PriorGrossEmoluments=Money("0.0", EUR),
            BasicPayFullTime=Money("0.0", EUR),
            BasicPayPartTime=Money("0.0", EUR),
            ManualAdjustments=Money("0.0", EUR),
            StatutoryBonus=Money("0.0", EUR),
            TotalTaxableGrossEmoluments=Money("0.0", EUR),
            PriorIncomeTaxDeduction=Money("0.0", EUR),
            IncomeTaxFullTime=Money("0.0", EUR),
            IncomeTaxPartTime=Money("0.0", EUR),
            SocialSecurityContributionEmployee=Money("0.0", EUR),
            SocialSecurityContributionEmployer=Money("0.0", EUR),
            TotalDeductions=Money("0.0", EUR),
            MaternityFundContributionEmployer=Money("0.0", EUR),
            Reimbursements=Money("0.0", EUR),
            NetPay=Money("0.0", EUR),
            TaxDue=Money("0.0", EUR),
        )

    def __add__(self, other: "Items") -> "Items":
        return Items(
            PriorGrossEmoluments=self.prior_gross_emoluments + other.prior_gross_emoluments,
            BasicPayFullTime=self.basic_pay_full_time + other.basic_pay_full_time,
            BasicPayPartTime=self.basic_pay_part_time + other.basic_pay_part_time,
            ManualAdjustments=self.manual_adjustments + other.manual_adjustments,
            StatutoryBonus=self.statutory_bonus + other.statutory_bonus,
            TotalTaxableGrossEmoluments=self.total_taxable_gross_emoluments + other.total_taxable_gross_emoluments,
            PriorIncomeTaxDeduction=self.prior_income_tax_deduction + other.prior_income_tax_deduction,
            IncomeTaxFullTime=self.income_tax_full_time + other.income_tax_full_time,
            IncomeTaxPartTime=self.income_tax_part_time + other.income_tax_part_time,
            SocialSecurityContributionEmployee=self.social_security_contribution_employee + other.social_security_contribution_employee,
            SocialSecurityContributionEmployer=self.social_security_contribution_employer + other.social_security_contribution_employer,
            TotalDeductions=self.total_deductions + other.total_deductions,
            MaternityFundContributionEmployer=self.maternity_fund_contribution_employer + other.maternity_fund_contribution_employer,
            Reimbursements=self.reimbursements + other.reimbursements,
            NetPay=self.net_pay + other.net_pay,
            TaxDue=self.tax_due + other.tax_due,
        )


class LineItems(CustomBaseModel):
    prior_gross_emoluments: LineItem = LineItem()
    basic_pay: LineItem = LineItem()
    manual_adjustments: LineItem = LineItem()
    statutory_bonus: LineItem = LineItem()
    total_taxable_gross_emoluments: LineItem = LineItem()
    prior_income_tax_deduction: LineItem = LineItem()
    income_tax: LineItem = LineItem()
    social_security_contribution_employee: LineItem = LineItem()
    social_security_contribution_employer: LineItem = LineItem()
    total_deductions: LineItem = LineItem()
    maternity_fund_contribution_employer: LineItem = LineItem()
    net_employee_pay: LineItem = LineItem()
    net_tax_payment: LineItem = LineItem()

    def as_items(self, part_time: bool) -> Items:
        return Items(
            PriorGrossEmoluments=Money(self.prior_gross_emoluments.current_period, EUR),
            BasicPayFullTime=Money(self.basic_pay.current_period, EUR) if not part_time else Money("0.0", EUR),
            BasicPayPartTime=Money(self.basic_pay.current_period, EUR) if part_time else Money("0.0", EUR),
            ManualAdjustments=Money(self.manual_adjustments.current_period, EUR),
            StatutoryBonus=Money(self.statutory_bonus.current_period, EUR),
            TotalTaxableGrossEmoluments=Money(self.total_taxable_gross_emoluments.current_period, EUR),
            PriorIncomeTaxDeduction=Money(self.prior_income_tax_deduction.current_period, EUR),
            IncomeTaxFullTime=Money(self.income_tax.current_period, EUR) if not part_time else Money("0.0", EUR),
            IncomeTaxPartTime=Money(self.income_tax.current_period, EUR) if part_time else Money("0.0", EUR),
            SocialSecurityContributionEmployee=Money(self.social_security_contribution_employee.current_period, EUR),
            SocialSecurityContributionEmployer=Money(self.social_security_contribution_employer.current_period, EUR),
            TotalDeductions=Money(self.total_deductions.current_period, EUR),
            MaternityFundContributionEmployer=Money(self.maternity_fund_contribution_employer.current_period, EUR),
            Reimbursements=Money("0.0", EUR),
            NetPay=Money(self.net_employee_pay.current_period, EUR),
            TaxDue=Money(self.net_tax_payment.current_period, EUR),
        )
