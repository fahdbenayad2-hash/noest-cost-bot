def calculate(session: dict) -> dict:
    """Calculate all cost metrics from a completed session data dict.

    Args:
        session: The user_data dict containing fabric_batches,
                 sewing_cost_per_unit, accessories_cost, delivery_cost,
                 additional_costs_per_unit, and sizes.

    Returns:
        A dict with all cost breakdowns, per-unit costs, and size_breakdown.
    """
    fabric_cost = sum(
        b["meters"] * b["price_per_meter"] for b in session["fabric_batches"]
    )
    sewing_per_unit = session["sewing_cost_per_unit"]
    accessories_total = session["accessories_cost"]
    delivery_total = session["delivery_cost"]
    additional_per_unit = session["additional_costs_per_unit"]

    total_units = sum(s["quantity"] for s in session["sizes"])

    sewing_total = sewing_per_unit * total_units
    additional_total = additional_per_unit * total_units
    total_cost = fabric_cost + sewing_total + accessories_total + delivery_total + additional_total

    unit_cost = total_cost / total_units if total_units > 0 else 0
    fabric_unit = fabric_cost / total_units if total_units > 0 else 0
    accessories_unit = accessories_total / total_units if total_units > 0 else 0
    delivery_unit = delivery_total / total_units if total_units > 0 else 0

    size_breakdown = [
        {
            "size": s["label"],
            "qty": s["quantity"],
            "subtotal": round(unit_cost * s["quantity"], 2),
        }
        for s in session["sizes"]
    ]

    return {
        "fabric_cost": round(fabric_cost, 2),
        "sewing_cost": round(sewing_total, 2),
        "accessories_cost": round(accessories_total, 2),
        "delivery_cost": round(delivery_total, 2),
        "additional_costs": round(additional_total, 2),
        "fabric_unit_cost": round(fabric_unit, 2),
        "sewing_unit_cost": round(sewing_per_unit, 2),
        "accessories_unit_cost": round(accessories_unit, 2),
        "delivery_unit_cost": round(delivery_unit, 2),
        "additional_unit_cost": round(additional_per_unit, 2),
        "total_cost": round(total_cost, 2),
        "total_units": total_units,
        "unit_cost": round(unit_cost, 2),
        "size_breakdown": size_breakdown,
    }
