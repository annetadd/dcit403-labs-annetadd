import csv
from datetime import date, timedelta
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pharmacy-stock")
DATA_PATH = Path(__file__).resolve().parent / "data" / "pharmacy_stock.csv"
FIELDNAMES = ["item", "strength", "form", "quantity", "unit_price_ghs", "expiry_date"]


def _load_rows() -> list[dict]:
    with open(DATA_PATH, mode="r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_rows(rows: list[dict]) -> None:
    with open(DATA_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


@mcp.tool()
def check_stock(item: str, strength: str = "") -> list[dict]:
    """Check pharmacy stock rows matching item name (case-insensitive) and optional strength."""
    rows = _load_rows()
    matches = [r for r in rows if item.strip().lower() in r["item"].lower()]
    if strength.strip():
        matches = [r for r in matches if strength.strip().lower() in r["strength"].lower()]
    return matches


@mcp.tool()
def search_items(query: str) -> list[dict]:
    """Search pharmacy stock by matching query across item name, strength, or form."""
    q = query.strip().lower()
    if not q:
        return []
    return [
        r
        for r in _load_rows()
        if q in r["item"].lower() or q in r["strength"].lower() or q in r["form"].lower()
    ]


@mcp.tool()
def list_expiring(days: int = 60) -> list[dict]:
    """List pharmacy items expiring on or before today + days (default 60 days)."""
    if days < 0:
        return []
    today = date.today()
    cutoff = today + timedelta(days=days)
    expiring = []
    for r in _load_rows():
        try:
            exp_date = date.fromisoformat(r["expiry_date"].strip())
        except ValueError:
            continue
        if exp_date <= cutoff:
            expiring.append({**r, "days_until_expiry": (exp_date - today).days})
    return expiring


@mcp.tool()
def record_sale(item: str, strength: str, qty: int) -> dict:
    """Record a sale by reducing stock quantity in the CSV. Refuses non-positive qty or insufficient stock."""
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        return {
            "status": "refused",
            "reason": f"Quantity must be a positive integer; got {qty}.",
        }

    rows = _load_rows()
    for idx, r in enumerate(rows):
        item_ok = item.strip().lower() in r["item"].lower()
        strength_ok = (not strength.strip()) or (strength.strip().lower() in r["strength"].lower())
        if item_ok and strength_ok:
            available = int(r["quantity"])
            if qty > available:
                return {
                    "status": "refused",
                    "reason": (
                        f"Insufficient stock for {r['item']} ({r['strength']}): "
                        f"requested {qty}, only {available} available."
                    ),
                }
            new_qty = available - qty
            rows[idx]["quantity"] = str(new_qty)
            _save_rows(rows)
            unit_price = float(r["unit_price_ghs"])
            return {
                "status": "recorded",
                "item": r["item"],
                "strength": r["strength"],
                "qty_sold": qty,
                "remaining_quantity": new_qty,
                "unit_price_ghs": unit_price,
                "total_ghs": round(qty * unit_price, 2),
            }

    return {
        "status": "refused",
        "reason": f"No stock item matched item='{item}' and strength='{strength}'.",
    }


if __name__ == "__main__":
    mcp.run()