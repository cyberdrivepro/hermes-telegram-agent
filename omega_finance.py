"""Deterministic financial calculations from explicit user assumptions.

Rates are inputs, never fetched or presented as current tax or investment advice.
"""
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math
import xml.etree.ElementTree as ET


def amount(value, *, low="0", high="1000000000000000"):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Expected a decimal number") from exc
    if not number.is_finite() or not Decimal(low) <= number <= Decimal(high):
        raise ValueError(f"Number must be finite and between {low} and {high}")
    return number


def money(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def amortization(payload, workspace):
    """Generate a reducing-balance monthly loan schedule with optional prepayment."""
    principal = amount(payload["principal"], low="0.01")
    rate = amount(payload.get("annual_rate_percent", 0), high="100") / 1200
    months = payload.get("months", 12)
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 1200:
        raise ValueError("months must be an integer from 1 to 1200")
    extra = amount(payload.get("monthly_prepayment", 0))
    payment = principal / months if rate == 0 else principal * rate / (1 - (1 + rate) ** -months)
    balance, interest_total, rows = principal, Decimal(0), []
    for month in range(1, months + 1):
        interest = balance * rate
        paid = min(payment + extra, balance + interest)
        if month == months:
            paid = balance + interest
        principal_paid = paid - interest
        balance = max(Decimal(0), balance - principal_paid)
        interest_total += interest
        rows.append([month, money(paid), money(principal_paid), money(interest), money(balance)])
        if balance == 0:
            break
    with (workspace / "amortization.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["month", "payment", "principal", "interest", "remaining"])
        writer.writerows(rows)
    return {"summary": f"Loan repaid in {len(rows)} months; total interest {money(interest_total)}.",
            "data": {"monthly_payment": money(payment), "total_interest": money(interest_total),
                     "months": len(rows), "rounding": "Internal Decimal precision; displayed amounts rounded to 2 decimals"},
            "artifacts": ["amortization.csv"]}


def dcf(payload, workspace):
    """Value explicit projected cash flows with a user-supplied discount and terminal growth rate."""
    flows = payload.get("cash_flows")
    if not isinstance(flows, list) or not 1 <= len(flows) <= 100:
        raise ValueError("cash_flows must contain 1 to 100 yearly projections")
    flows = [amount(x, low="-1000000000000000") for x in flows]
    rate = amount(payload["discount_rate_percent"], low="0.01", high="100") / 100
    growth = amount(payload.get("terminal_growth_percent", 0), low="-99", high="100") / 100
    if growth >= rate:
        raise ValueError("Terminal growth must be below the discount rate")
    discounted = [flow / (1 + rate) ** (year + 1) for year, flow in enumerate(flows)]
    terminal = flows[-1] * (1 + growth) / (rate - growth)
    value = sum(discounted) + terminal / (1 + rate) ** len(flows)
    result = {"enterprise_value": money(value), "terminal_value": money(terminal),
              "discounted_cash_flows": [money(x) for x in discounted],
              "assumptions": payload, "method": "Year-end cash flows; perpetual terminal growth"}
    (workspace / "dcf.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"summary": f"DCF enterprise value: {money(value)} in the input currency.", "data": result, "artifacts": ["dcf.json"]}


def invoice(payload, workspace):
    """Calculate invoice totals and tax splits from explicit rates, exporting JSON and CSV."""
    items = payload.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 1000:
        raise ValueError("items must contain 1 to 1000 invoice lines")
    interstate = payload.get("interstate", False)
    if not isinstance(interstate, bool):
        raise ValueError("interstate must be a boolean")
    lines, totals = [], {k: Decimal(0) for k in ("taxable", "cgst", "sgst", "igst", "total")}
    for item in items:
        label = str(item.get("description", "Item"))[:300]
        taxable = (amount(item["quantity"], high="1000000") * amount(item["unit_price"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = amount(item["tax_rate_percent"], high="100")
        tax = (taxable * rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cgst = Decimal(0) if interstate else (tax / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = Decimal(0) if interstate else tax - cgst
        values = {"taxable": taxable, "cgst": cgst, "sgst": sgst, "igst": tax if interstate else Decimal(0), "total": taxable + tax}
        lines.append({"description": label, **{k: money(v) for k, v in values.items()}})
        for key, value in values.items():
            totals[key] += value
    result = {"lines": lines, "totals": {k: money(v) for k, v in totals.items()}, "interstate": interstate,
              "rate_source": "User-supplied; no HSN lookup or statutory compliance validation"}
    (workspace / "invoice.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (workspace / "invoice.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(lines[0]))
        writer.writeheader()
        for row in lines:
            safe = dict(row)
            if safe["description"].lstrip().startswith(("=", "+", "-", "@")):
                safe["description"] = "'" + safe["description"]
            writer.writerow(safe)
    return {"summary": f"Invoice total: {money(totals['total'])}.", "data": result, "artifacts": ["invoice.json", "invoice.csv"]}


CAPABILITIES = {"finance.amortization": amortization, "finance.dcf": dcf, "finance.invoice": invoice}
CAPABILITY_INFO = {
    "finance.amortization": {"example": {"principal": "100000", "annual_rate_percent": "12", "months": 12}},
    "finance.dcf": {"example": {"cash_flows": [100, 120, 140], "discount_rate_percent": 10, "terminal_growth_percent": 2}},
    "finance.invoice": {"example": {"interstate": False, "items": [{"description": "Service", "quantity": 1, "unit_price": "1000", "tax_rate_percent": 18}]}}
}
