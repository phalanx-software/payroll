# Payroll

A Python command-line tool to help Phalanx Software compute and execute their monthly payroll in accordance
with the Maltese tax system.

This tool supports:
* computing the net payments for full-time and part-time employees
* making income tax deductions and social security contribution deductions 
* generating PDF and HTML payslips
* aggregating data required to submit FS3, FS5 and FS7 forms

## Dependencies

The payroll tool must be run using `poetry`. Install `poetry` by executing:

```
pip install poetry
```

## Usage

The payroll tools requires a data directory where it will find all the files it needs to work on. Whenever executing
the tool specify the data directory that it will work on by passing in the `-d` flag.

Run commands from the project root directory. For help with the available commands run ```poetry run payroll --help```.

```poetry run payroll payments -d /data```

### Compute Payments

Before executing the payroll, you must first create the employee, organisation and transaction files that define the 
payroll computation. This information must be located in `organisation.yml`, `/employees`, `/tables` and `/templates`,
inside the data directory.
Optionally, you may also provide information about one-off transactions in `/manualadjustments`, `/reimbursements` and
`/worklogs`.

When ready, simply execute the following command to execute the payroll and generate payment files for all employees.

```
poetry run payroll payments -d /data
```

After generating the payments, you may generate payslip documents by executing:

```
poetry run payroll payslips -d /data
```

For more options and information about how to generate the FS3, FS5 and FS7 reports, please check the
help command.

## Templates

The payroll application requires a number of YAML files to describe the organisation and employees.

_Note: Fields that are commented out are optional._

### Organisation (YAML)

```yaml
Name: The Software Company
Address: 17 Flat 3, Triq Il-Bronja, Tas-Sliema
Postcode: SLM9183
RegistrationNumber: C 123456
TaxNumber: "123456"
TelephoneNumber: "+35679123456"
EmployerNumber: "1234567"
ManagerName: John Smith
ManagerRole: Director & Software Developer
Currency: EUR
```

### Employee (YAML)

```yaml
Identifier: E-001
FirstName: Alice
Surname: Doe
Role: Software Developer
Address: 10, Triq il-Kbira, Mosta
Postcode: MST1000
TelephoneNumber: "+35679123457"
RegistrationNumber: "123456M"
# SocialSecurityNumber: "1234567"
# SpouseRegistrationNumber: "0123456"
StartDate: 2020-02-01
# EndDate: 2020-12-31
HoursPerWeek: 32
TaxComputation: single
SocialSecurityCategory: "C/D #2"
GrossAnnualSalary: 24000
# PriorTaxInformation:
#  GrossAnnualEmoluments: 1200
#  IncomeTax: 0
```

### Tax Tables (CSV)

The tax tables are all stored in `/tables` as CSV files, within the data directory. Please be advised that the tables
provided with this source code are for the "Single" income tax computation and for the 2020 social security
contributions rates.

#### Income Tax

```
upto,rate,subtract
9100,0,0
14500,0.15,1365
19500,0.25,2815
60000,0.25,2725
-1,0.35,8725
```

#### Maternity Fund & Social Security Contributions

```
category,rate_type,rate,maximum
A,Fixed,0.20,0.20
B,Fixed,0.54,0.54
C/D #1,Rate,0.003,1.08
C/D #2,Rate,0.003,1.44
E,Rate,0.003,0.13
F,Rate,0.003,0.24
```

#### Statutory Bonus


```
month,bonus
march,121.16
june,135.10
september,121.16
december,135.10
```

### PDFKit on Linux

[PDFKit](https://pypi.org/project/pdfkit/) uses `wkhtmltopdf` which needs to be installed to your machine if you are using Linux. 

Debian/Ubuntu: `sudo apt-get install wkhtmltopdf` (may have reduced functionality)

ArchLinux: `sudo pacman -S wkhtmltopdf`

[Binaries](https://wkhtmltopdf.org/downloads.html) are also available.

## Licence

The payroll tool is open-source software, licensed under the GPL v3 license. For this reason, you are free to look
through its code, run it and even make changes and contributions to it. If you'd like to make a contribution, kindly 
open a pull request on GitHub with your changes.

Please be advised that the developers cannot take responsibility for the output and computations of this software. In
particular, the developers offer no warranty or guarantees for the correct performance of this software and its computations.

You may view the license document below:

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)