import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

PRODUCT = {
    "product_id": "tomeforge_premium",
    "name": "TomeForge Premium",
    "tax_code": "txcd_10103001",  # SaaS
    "prices": [
        {"lookup_key": "premium_monthly", "amount": 500, "currency": "eur", "interval": "month"},
        {"lookup_key": "premium_yearly", "amount": 4800, "currency": "eur", "interval": "year"},
    ],
}


def ensure_tax_settings():
    s = stripe.tax.Settings.retrieve()
    if s.head_office and getattr(s.head_office, "address", None):
        return
    stripe.tax.Settings.modify(
        head_office={"address": {"country": "IT", "line1": "Via Roma 1", "city": "Roma", "postal_code": "00100"}},
        defaults={"tax_behavior": "exclusive"},
    )


def get_or_create_product(entry):
    for p in stripe.Product.list(active=True).auto_paging_iter():
        if p.to_dict().get("metadata", {}).get("product_id") == entry["product_id"]:
            return p
    return stripe.Product.create(
        name=entry["name"], tax_code=entry.get("tax_code"),
        metadata={"managed_by": "tomeforge", "product_id": entry["product_id"]},
    )


def main():
    try:
        ensure_tax_settings()
    except Exception as e:
        print("tax settings warning:", e)
    product = get_or_create_product(PRODUCT)
    for p in PRODUCT["prices"]:
        existing = stripe.Price.list(lookup_keys=[p["lookup_key"]], active=True, limit=1).data
        if existing and (existing[0].unit_amount != p["amount"] or existing[0].currency != p["currency"]):
            stripe.Price.modify(existing[0].id, active=False)
            existing = []
        if not existing:
            kwargs = dict(product=product.id, unit_amount=p["amount"], currency=p["currency"],
                          lookup_key=p["lookup_key"], transfer_lookup_key=True,
                          recurring={"interval": p["interval"]})
            price = stripe.Price.create(**kwargs)
            print("created price", p["lookup_key"], price.id)
        else:
            print("price exists", p["lookup_key"], existing[0].id)


if __name__ == "__main__":
    main()
