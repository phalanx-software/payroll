import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import click
import yaml
from moneyed import Money

from payroll.custom_base_model import TaxComputation, SocialSecurityCategory
from payroll.payroll import Payroll
from payroll.yaml_utils import (decimal_representer, enum_representer, money_representer, decimal_constructor,
                                enum_constructor, money_constructor)

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')

yaml.add_representer(Decimal, decimal_representer)
yaml.add_representer(Money, money_representer)
yaml.add_representer(TaxComputation, enum_representer)
yaml.add_representer(SocialSecurityCategory, enum_representer)

yaml.add_constructor("!decimal", decimal_constructor)
yaml.add_constructor("!money", money_constructor)
yaml.add_constructor("!enum", enum_constructor)

yaml.Dumper.ignore_aliases = lambda *args: True


@click.group()
def main():
    pass


@main.command(name='payments')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to compute the payroll for. This is combined with the month to determine the payroll year-month. "
                   "Defaults to the current year.")
@click.option('-m', '--month', default=datetime.today().month,
              help="The month to compute the payroll for. This is combined with the year to determine the payroll year-month. "
                   "Defaults to the current month.")
def execute_payroll(data_dir: str,
                    year: int,
                    month: int):
    Payroll(Path(data_dir)).payments(year, month)


@main.command(name='payslips')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to compute the payroll for. This is combined with the month to determine the payroll year-month. "
                   "Defaults to the current year.")
@click.option('-m', '--month', default=datetime.today().month,
              help="The month to compute the payroll for. This is combined with the year to determine the payroll year-month. "
                   "Defaults to the current month.")
def execute_payslips(data_dir: str,
                     year: int,
                     month: int):
    Payroll(Path(data_dir)).payslips(year, month)


@main.command(name='revert')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to revert the payroll for. This is combined with the month to determine the payroll year-month. "
                   "Defaults to the current year.")
@click.option('-m', '--month', default=datetime.today().month,
              help="The month to revert the payroll for. This is combined with the year to determine the payroll year-month. "
                   "Defaults to the current month.")
def revert_payroll(data_dir: str,
                   year: int = datetime.today().year,
                   month: int = datetime.today().month):
    Payroll(Path(data_dir)).revert(year, month)


@main.command(name='fs3')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to generate the FS3 for. Defaults to the current year.")
def execute_fs3(data_dir: str,
                year: int = datetime.today().year):
    Payroll(Path(data_dir)).fs3_generator().generate_all(year)


@main.command(name='fs5')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to generate the FS5 for. This is combined with the month to determine the year-month. "
                   "Defaults to the current year.")
@click.option('-m', '--month', default=datetime.today().month,
              help="The month to generate the FS5 for. This is combined with the year to determine the year-month. "
                   "Defaults to the current month.")
def execute_fs5(data_dir: str,
                year: int = datetime.today().year,
                month: int = datetime.today().month):
    Payroll(Path(data_dir)).fs5_generator().generate(year, month)


@main.command(name='fs7')
@click.option('-d', '--data-dir', required=True,
              type=click.Path(exists=True),
              help="Absolute data directory where the payroll data should be read from and written to.")
@click.option('-y', '--year', default=datetime.today().year,
              help="The year to generate the FS7 for. Defaults to the current year.")
def execute_fs7(data_dir: str,
                year: int = datetime.today().year):
    Payroll(Path(data_dir)).fs7_generator().generate(year)


if __name__ == "__main__":
    main()
