# Brief: Supplier invoice extraction, August 2026

Task: extract every supplier invoice from the attached email thread into a JSON array. One object per invoice.

Fields per object: supplier (string), invoice_number (string, exactly as written), date (ISO 8601, YYYY-MM-DD), amount (number), currency (ISO 4217 code), vat (number or null), due_date (ISO 8601 or null).

Amounts: report the net amount (excluding VAT) in the amount field.

Scope: GBP invoices only. Exclude any invoice in another currency.

Invoice numbers must be kept exactly as written, including leading zeros and prefixes.

Exclude: voided or cancelled invoices, credit notes, and statements (a statement is not an invoice).

Output: a single JSON array, no prose, no code fences.

Where payment terms are stated (e.g. 30 days, 14 days), compute due_date from the invoice date; otherwise null.

---

## Attached email thread

From: accounts@northfield-supplies.co.uk
Subject: Invoices for August
Hi, attached are our August invoices. INV-000482 dated 4 Aug 2026 for £1,240.00 net (VAT £248.00, gross £1,488.00), 30 days. INV-000491 dated 18 Aug 2026 for £310.50 net (VAT £62.10, gross £372.60). Please note INV-000488 dated 11 Aug 2026 for £2,000.00 net was raised in error and has been VOIDED; ignore it.

From: billing@kestrel-cloud.io
Subject: Your invoice 7731
Invoice 7731, issued 2026-08-09, total $960.00 USD (no VAT, reverse charge). Due 2026-09-08. Service: compute, August.

From: hello@marlow-design.studio
Subject: Re: final invoice
Final invoice MD-2026-057, date 27/08/2026, £4,500 plus VAT at 20% (£900), total £5,400. Payment terms 14 days. Also, a credit note CN-012 for £300 net against MD-2026-041 was issued on 27/08/2026.

From: accounts@northfield-supplies.co.uk
Subject: Correction
Apologies, INV-000491 should read £315.50 net (VAT £63.10, gross £378.60). Please use the corrected figures.

From: no-reply@evergreen-energy.co.uk
Subject: Statement
Your account statement for August shows a balance of £642.18. No new invoices were issued this month.
