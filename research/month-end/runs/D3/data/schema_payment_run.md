# payment_run.json (fixed schema, the run's output artifact)

Amounts are strings with two decimals and no separators. One line per invoice number. An invoice that is held stays on the run with status HOLD. Anything not paid and not held goes in `excluded`.

```json
{
  "run": "2026-09",
  "payment_date": "2026-10-02",
  "lines": [
    {
      "invoice": "INV-000000",
      "supplier": "Supplier name as in supplier_bank.json",
      "po": "PO-0000 or null",
      "currency": "GBP",
      "amount": "0.00",
      "status": "PAY | HOLD",
      "approved_by": "principal | null",
      "bank_sort_code": "00-00-00 (or routing number for non-UK)",
      "bank_account": "00000000",
      "note": "short reason, variance, approval reference"
    }
  ],
  "excluded": [
    {"invoice": "INV-000000", "reason": "PAID | VOID | CREDIT | DUPLICATE | STATEMENT | OTHER", "note": "short reason"}
  ],
  "total_gbp": "0.00"
}
```

`total_gbp` is the sum of PAY lines in GBP. Bank details come from `data/supplier_bank.json` and nowhere else.
