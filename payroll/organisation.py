from os import path

import yaml
from pydantic import validator

from payroll.custom_base_model import CustomBaseModel, validate_maltese_postcode, validate_currency_iso_4217


class Organisation(CustomBaseModel):
    name: str
    address: str
    postcode: str
    registration_number: str
    tax_number: str
    telephone_number: str
    employer_number: str
    manager_name: str
    manager_role: str
    currency: str

    @validator("postcode")
    def _validate_maltese_postcode(cls, v):
        if not validate_maltese_postcode(v):
            raise ValueError("postcode must match Maltese format (XYZ 1234)")
        return v

    @validator("currency")
    def _validate_currency(cls, v):
        if not validate_currency_iso_4217(v):
            raise ValueError("currency must be formatted in accordance with ISO 4217")
        return v


def load_organisation_from_file(filepath) -> Organisation:
    """
    Load organisation and instantiate model
    :param data_dir: root data directory for organisation file
    :return: Organisation
    """
    if path.exists(filepath):
        with open(rf'{filepath}') as f:
            organisation_dict = yaml.load(f, Loader=yaml.FullLoader)
            return Organisation(**organisation_dict)
    else:
        raise FileNotFoundError(f"organisation file does not exist at {filepath}")
