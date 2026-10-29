from datetime import timedelta
from .domain import Invoice, new_case, audit, now, local_today
from . import store

SAMPLE = {
    "supplier": "Shree Ganesh Distributors",
    "supplier_phone": "",
    "reference": "A-104",
    "date": "2026-10-29",
    "pricing_note": "Synthetic invoice. Net unit prices; no additional tax, discount or scheme.",
    "lines": [
        {"name": "Parle-G biscuits", "billed": 12, "unit": "pack", "price_paise": 4000},
        {"name": "Tata Tea 250 g", "billed": 6, "unit": "pack", "price_paise": 12500},
        {
            "name": "Lifebuoy soap",
            "billed": 24,
            "unit": "unknown",
            "price_paise": 3500,
            "note": "Unit on bill is unclear. Confirm with the supplier.",
        },
    ],
}


def sample_invoice():
    return Invoice.model_validate(SAMPLE).model_dump()


def demo_seed():
    """A small, clearly synthetic ledger. No measured merchant outcomes."""
    if store.all_cases():
        return
    today = local_today()
    with store.connect() as db:
        for cid, ref, name, billed, received, price, status, days in [
            ("MNF-1003", "SG-318", "Fortune sunflower oil 1 L", 24, 20, 12000, "promised", -1),
            ("MNF-1002", "KR-092", "Aashirvaad atta 5 kg", 10, 8, 24000, "sent", 2),
            ("MNF-1001", "VT-210", "Amul ghee 500 ml", 12, 10, 30000, "resolved", 0),
        ]:
            inv = Invoice(
                supplier={
                    "SG-318": "Shree Ganesh Distributors",
                    "KR-092": "Kaveri Wholesale",
                    "VT-210": "Vijaya Traders",
                }[ref],
                reference=ref,
                date=(today - timedelta(days=4)).isoformat(),
                lines=[
                    {
                        "name": name,
                        "billed": billed,
                        "received": received,
                        "unit": "pack",
                        "received_unit": "pack",
                        "unit_confirmed": True,
                        "price_paise": price,
                    }
                ],
            ).model_dump()
            c = new_case(inv, cid, True)
            c.update(
                delivery_complete=True,
                pricing_confirmed=True,
                approved_version=1,
                status=status,
                approved_amount_paise=(billed - received) * price,
                follow_up=(today + timedelta(days=days)).isoformat(),
            )
            audit(c, "Evidence approved", "Synthetic demonstration history")
            audit(c, "Sharing confirmed", "Synthetic merchant confirmation")
            if status == "promised":
                c["promise"] = "Will adjust against the next bill."
                audit(c, "Supplier promise recorded", c["promise"])
            if status == "resolved":
                proofid = "demo-proof-1001"
                c["resolutions"] = [
                    {
                        "id": "demo-resolution-1001",
                        "kind": "credit",
                        "supplier": inv["supplier"],
                        "invoice_reference": ref,
                        "evidence_reference": "DEMO-CN-210",
                        "amount_paise": 60000,
                        "attachment_id": proofid,
                        "applied_confirmed": True,
                        "at": now(),
                    }
                ]
                c["follow_up"] = None
                audit(c, "Credit verified", "₹600 applied. Synthetic evidence DEMO-CN-210.")
            store.save(db, c)
            if status == "resolved":
                db.execute(
                    "INSERT INTO attachments VALUES (?,?,?,?,?)",
                    (
                        proofid,
                        cid,
                        "DEMO-CN-210.txt",
                        "text/plain",
                        b"SYNTHETIC CREDIT NOTE\nSupplier: Vijaya Traders\nInvoice: VT-210\nReference: DEMO-CN-210\nCredit applied: INR 600.00",
                    ),
                )
                db.execute(
                    "INSERT INTO resolution_keys VALUES (?,?)", ("vijaya traders", "demo-cn-210")
                )
                import hashlib

                proof = db.execute(
                    "SELECT data FROM attachments WHERE id=?", (proofid,)
                ).fetchone()["data"]
                db.execute(
                    "INSERT INTO resolution_proofs VALUES (?,?)",
                    ("vijaya traders", hashlib.sha256(proof).hexdigest()),
                )
