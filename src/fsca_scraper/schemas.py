from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

def split_physical_address(address: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None, None, None
    raw_lines = [line.strip() for line in address.split('\n') if line.strip()]
    
    postal_code = None
    lines = []
    for line in raw_lines:
        if re.match(r'^\d{3,4}$', line):
            postal_code = line.zfill(4)
        else:
            lines.append(line)
            
    if not postal_code and lines:
        m = re.search(r'\b\d{3,4}\b', lines[-1])
        if m:
            postal_code = m.group(0).zfill(4)
            lines[-1] = re.sub(r'\b\d{3,4}\b', '', lines[-1]).strip()
            if not lines[-1]:
                lines.pop()
                
    line1 = lines[0] if len(lines) > 0 else None
    line2 = lines[1] if len(lines) > 1 else None
    line3 = lines[2] if len(lines) > 2 else None
    line4 = lines[3] if len(lines) > 3 else None
    
    if len(lines) > 4:
        line4 = ", ".join(lines[3:])
        
    return line1, line2, line3, line4, postal_code


class FspApprovedProductSchema(BaseModel):
    category: str
    product_name: str
    advice_automated: bool = False
    advice_non_automated: bool = False
    intermediary_scripted: bool = False
    intermediary_other: bool = False
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    combined_code: Optional[str] = None


class FspRepresentativeProductSchema(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_name: str
    advice: bool = False
    intermediary_scripted: bool = False
    intermediary_other: bool = False
    under_supervision: bool = False
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    combined_code: Optional[str] = None


class FspKeyIndividualClassOfBusinessSchema(BaseModel):
    cob_description: str
    category_i: bool = False
    category_ii: bool = False
    category_iia: bool = False
    category_iii: bool = False
    category_iv: bool = False
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    combined_code: Optional[str] = None


class FspKeyIndividualCryptoSchema(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_name: str
    advice: bool = False
    intermediary_scripted: bool = False
    intermediary_other: bool = False
    under_supervision: bool = False
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    combined_code: Optional[str] = None


class FspSoleProprietorProductSchema(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_name: str
    advice: bool = False
    intermediary_scripted: bool = False
    intermediary_other: bool = False
    under_supervision: bool = False
    category_code: Optional[str] = None
    sub_category_code: Optional[str] = None
    combined_code: Optional[str] = None


class FspSoleProprietorSchema(BaseModel):
    full_names: str
    surname: str
    conditions_apply: Optional[str] = None
    products: List[FspSoleProprietorProductSchema] = []


class FspRepresentativeSchema(BaseModel):
    rep_id: Optional[str] = None
    full_names: str
    surname: str
    ki_of_rep: Optional[str] = None
    products: List[FspRepresentativeProductSchema] = []


class FspKeyIndividualSchema(BaseModel):
    ki_id: Optional[str] = None
    full_names: str
    surname: str
    class_of_business: Optional[str] = None
    crypto_oversee: Optional[str] = None
    cobs: List[FspKeyIndividualClassOfBusinessSchema] = []
    cryptos: List[FspKeyIndividualCryptoSchema] = []


class FspComplianceOfficerSchema(BaseModel):
    name: str
    telephone: Optional[str] = None


class FspDetailsSchema(BaseModel):
    fsp_no: str
    name: str
    trading_name: Optional[str] = None
    fsp_type: Optional[str] = None
    registration_number: Optional[str] = None
    date_authorised: Optional[str] = None
    status: Optional[str] = None
    physical_address: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    address_line_3: Optional[str] = None
    address_line_4: Optional[str] = None
    postal_code: Optional[str] = None
    telephone: Optional[str] = None
    compliance_officers: List[FspComplianceOfficerSchema] = []
    representatives: List[FspRepresentativeSchema] = []
    key_individuals: List[FspKeyIndividualSchema] = []
    approved_products: List[FspApprovedProductSchema] = []
    sole_proprietors: List[FspSoleProprietorSchema] = []

    @model_validator(mode="after")
    def process_address(self) -> "FspDetailsSchema":
        if self.physical_address:
            l1, l2, l3, l4, pc = split_physical_address(self.physical_address)
            self.address_line_1 = l1
            self.address_line_2 = l2
            self.address_line_3 = l3
            self.address_line_4 = l4
            if not self.postal_code:
                self.postal_code = pc
        return self
