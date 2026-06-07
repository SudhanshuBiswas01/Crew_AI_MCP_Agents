# Example Questions and Saved Outputs

Three fixed questions with expected tool calls and saved outputs.
Run logs proving tools were actually called are in `traces/`.

---

## Question 1

**Question:** What is our return policy for hardware items?

**Expected tool calls:**
- `search_documents(query="return policy hardware")`
- `save_report(title="Return Policy for Hardware", content=...)`

**Expected answer snippet:**
> Hardware items can be returned within 30 days of purchase in original unopened packaging.
> A 10% restocking fee applies to all hardware returns.
> [Source: return_policy.txt]

**Saved output:** `output/return_policy_for_hardware_<timestamp>.md`

---

## Question 2

**Question:** List all pending orders and calculate their total value.

**Expected tool calls:**
- `search_documents(query="pending orders")`
- `read_record(record_id="2")` → Widget B, $49.50
- `read_record(record_id="5")` → Widget E, $9.99 × 10
- `read_record(record_id="7")` → Widget G, $39.99 × 4
- `read_record(record_id="9")` → Widget I, $199.00 × 2
- `save_report(title="Pending Orders Summary", content=...)`

**Expected answer snippet:**
> There are 4 pending orders with a combined value of $697.40.
> [Source: records.csv — ids 2, 5, 7, 9]

**Saved output:** `output/pending_orders_summary_<timestamp>.md`

---

## Question 3

**Question:** What does our shipping policy say and are there any fulfilled orders for Acme Corp?

**Expected tool calls:**
- `search_documents(query="shipping delivery")`
- `search_documents(query="Acme Corp")`
- `read_record(record_id="1")` → Widget A, fulfilled
- `read_record(record_id="4")` → Widget D — not Acme, skip
- `read_record(record_id="6")` → Widget F — not Acme, skip
- `save_report(title="Shipping Policy and Acme Corp Orders", content=...)`

**Expected answer snippet:**
> Standard shipping takes 5–7 business days; express 1–2 days. [Source: shipping_info.txt]
> Acme Corp has 1 fulfilled order: Widget A (id=1), $99.99. [Source: records.csv, id=1]

**Saved output:** `output/shipping_policy_and_acme_corp_orders_<timestamp>.md`
