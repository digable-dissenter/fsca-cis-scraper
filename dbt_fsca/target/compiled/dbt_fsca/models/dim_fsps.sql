select
    id as fsp_id,
    fsp_no,
    name,
    trading_name,
    fsp_type,
    registration_number,
    date_authorised,
    status,
    physical_address,
    address_line_1,
    address_line_2,
    address_line_3,
    address_line_4,
    case 
        when postal_code is not null and length(postal_code) > 0 
        then substr('0000' || trim(postal_code), -4)
        else null 
    end as padded_postal_code,
    telephone,
    scraped_at
from fsps