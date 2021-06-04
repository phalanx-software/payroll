from payroll.tax_table import IncomeTaxTable, CategoryRateTable, MonetaryBonusTable


class TaxTableManager:
    def __init__(self,
                 year: str,
                 data_dir: str = "data",
                 ):
        """Load all the relevant tax tables
        :param year:
        :param data_dir: root directory for tax tables
        """
        self.income_tax_single = IncomeTaxTable(filepath=f"{data_dir}/tables/{year}-income-tax-single.csv")
        self.maternity_fund = CategoryRateTable(filepath=f"{data_dir}/tables/{year}-maternity.csv")
        self.social_security = CategoryRateTable(filepath=f"{data_dir}/tables/{year}-ssc.csv")
        self.statutory_bonus = MonetaryBonusTable(filepath=f"{data_dir}/tables/{year}-statutory-bonus.csv")
