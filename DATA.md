# Project Data Documentation

This repository uses a small, hand-readable corpus designed for operations assistant retrieval testing:

### 1. Documents Folder (`/docs`)
Contains 12 plain-text operations documents for a fictional electronics retailer:
* **Shipping Policies (2):** Paraphrased from real Zappos and Amazon policies.
* **Return Policies (2):** Paraphrased from real Zappos and Best Buy policies.
* **Product Notes (2):** Technical specifications and workarounds for UCH-7001 (USB-C Hub) and WMK-2200 (Keyboard).
* **Support Tickets (3):** Summaries for case references TKT-4421, TKT-4489, and TKT-4601.
* **Inventory Alerts (2):** Operational low-stock (WMK-2200) and overstock (CAB-1100) alerts.
* **Escalation Procedure (1):** Guidelines for processing damaged goods based on real carrier processes.

### 2. Orders Dataset (`/data/inventory_orders.csv`)
A synthetic dataset containing exactly 40 rows of order records (with columns like `order_id`, `product_name`, `sku`, etc.). It includes two data anomalies (qty = -1), three returned orders matching support tickets, and mixed statuses for realistic retrieval testing.

### 3. Usage & Scope
* Policy documents are paraphrased from real public pages for educational use only.
* The CSV is entirely synthetic with no real customer PII.
* The corpus size is kept small to allow for direct verification by hand.
