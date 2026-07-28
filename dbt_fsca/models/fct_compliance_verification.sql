with rep_products as (
    select
        rp.id as rep_product_id,
        r.fsp_id,
        r.full_names || ' ' || r.surname as rep_name,
        rp.category,
        rp.subcategory,
        rp.product_name,
        rp.advice,
        rp.intermediary_scripted or rp.intermediary_other as intermediary,
        rp.under_supervision,
        rp.category_code,
        rp.sub_category_code,
        rp.combined_code
    from fsp_representative_products rp
    join fsp_representatives r on rp.representative_id = r.id
)

select
    fsp_id,
    rep_product_id,
    rep_name,
    category,
    product_name,
    advice,
    intermediary,
    under_supervision,
    combined_code
from rep_products