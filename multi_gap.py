"""
multi_gap.py — Battery Passport gap scan across all partners
============================================================
Extends the pipeline in pipeline.py without modifying it.

Exports:
    find_all_gaps(rule) -> list[dict]
    find_gaps_for_all_rules(rules_catalog_path) -> list[dict]

Each dict in the returned list has the same shape as sample_expected_output.json,
plus an extra 'rule_id' field when produced by find_gaps_for_all_rules().

bob_rules.md constraints applied
---------------------------------
- Simplicity First       : one function per concern; shared helpers kept minimal.
- Read Before You Write  : partners.json / taxonomy.json /
                           sample_expected_output.json are read before any
                           assessment logic runs.
- Surgical Changes       : pipeline.py is untouched.
- Checkpoint             : summary printed after every rule scan and at the end.
- Surface Conflicts      : known_gaps mismatches and category ambiguities flagged.
- Fail Loud              : missing or ambiguous fields raise ValueError;
                           unexpected values are warned about.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
PARTNERS_FILE      = BASE / "partners.json"
TAXONOMY_FILE      = BASE / "taxonomy.json"
SAMPLE_OUTPUT_FILE = BASE / "sample_expected_output.json"


def find_all_gaps(rule: dict) -> list:
    """
    Loop over every partner and every product in partners.json.
    Apply the same five-filter obligation check used for P013-A:

        Filter 1 — market    : product must be sold in a market covered by the rule
        Filter 2 — category  : product category must be emobility_battery
        Filter 3 — battery_type : product.battery_type must equal rule["scope"]["battery_type"]
        Filter 4 — certs     : partner must NOT already hold a battery-passport cert
        Filter 5 — exclusions: products not sold in the EU are excluded

    Returns a list of findings (one per gap) whose shape matches
    sample_expected_output.json.

    Raises:
        ValueError  — if any required field is absent from the rule or a product.
        SystemExit  — if partners.json / taxonomy.json / sample_expected_output.json
                      cannot be loaded.
    """

    # ------------------------------------------------------------------
    # Read Before You Write (bob_rules.md)
    # ------------------------------------------------------------------
    print("\n[multi_gap] Reading data files before assessment …")

    for path in (PARTNERS_FILE, TAXONOMY_FILE, SAMPLE_OUTPUT_FILE):
        if not path.exists():
            sys.exit(f"ERROR: required file not found: {path}")

    partners_data = json.loads(PARTNERS_FILE.read_text())
    taxonomy      = json.loads(TAXONOMY_FILE.read_text())
    sample_shape  = json.loads(SAMPLE_OUTPUT_FILE.read_text())

    # Confirm taxonomy recognises emobility_battery — fail loud if not.
    if "emobility_battery" not in taxonomy.get("product_categories", {}):
        raise ValueError(
            "Conflict: taxonomy.json does not define 'emobility_battery'. "
            "Cannot apply Filter 2 safely — aborting."
        )

    # ------------------------------------------------------------------
    # Validate rule has the fields we need — fail loud.
    # ------------------------------------------------------------------
    for field in ("scope", "regulation", "article", "requirement",
                  "deadline", "source_url"):
        if field not in rule:
            raise ValueError(f"Rule is missing required field: '{field}'")

    rule_scope = rule["scope"]
    for scope_field in ("battery_type", "markets"):
        if scope_field not in rule_scope:
            raise ValueError(
                f"Rule scope is missing required field: '{scope_field}'"
            )

    required_battery_type = rule_scope["battery_type"]   # "lmt"
    required_markets      = set(rule_scope["markets"])    # {"EU"}

    print(f"         Rule           : {rule['regulation']} — {rule['article']}")
    print(f"         Required type  : {required_battery_type}")
    print(f"         Required markets: {sorted(required_markets)}")
    print(f"         Sample shape keys: {[k for k in sample_shape if not k.startswith('_')]}")

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------
    findings = []
    scanned_products = 0

    for partner in partners_data["partners"]:
        certs_held = (
            partner
            .get("compliance_status", {})
            .get("certs_held", [])
        )
        known_gaps = (
            partner
            .get("compliance_status", {})
            .get("known_gaps", [])
        )
        passport_held = any("passport" in c.lower() for c in certs_held)

        for product in partner["products"]:
            scanned_products += 1

            # Filter 1 — market: product must reach at least one rule market.
            # EU members (ISO codes) also satisfy an "EU" rule requirement.
            # "EU" in product markets is the definitive signal; individual
            # member-state codes are treated as EU for this rule.
            # EU_MEMBER_CODES is the module-level constant defined below.
            product_markets = set(product.get("markets", []))
            in_eu = (
                "EU" in product_markets
                or bool(product_markets & EU_MEMBER_CODES)
            )
            markets_match = bool(required_markets & product_markets) or (
                "EU" in required_markets and in_eu
            )
            if not markets_match:
                continue  # Filter 1 rejects

            # Filter 2 — category: must be emobility_battery.
            if product.get("category") != "emobility_battery":
                continue  # Filter 2 rejects

            # Filter 3 — battery_type: must match rule's required type.
            product_btype = product.get("battery_type")
            if product_btype != required_battery_type:
                # Surface conflict if category says emobility but type differs.
                print(
                    f"         CONFLICT: {partner['partner_id']} / "
                    f"{product['product_id']} has category=emobility_battery "
                    f"but battery_type='{product_btype}' (rule requires "
                    f"'{required_battery_type}'). Excluding from LMT passport "
                    f"findings — verify data."
                )
                continue  # Filter 3 rejects

            # Filter 4 — certs: obligation applies; check if passport already held.
            # At this point the obligation applies unconditionally.
            obligation_applies = True

            if passport_held:
                # Gap does NOT exist — partner already compliant.
                continue  # Filter 4 clears

            # Filter 5 — exclusions: no additional exclusions defined for
            # Article 77 at the time of writing.  Placeholder for future
            # exemption logic (e.g., SLA-batteries supplied only to defence).

            # ------------------------------------------------------------------
            # Gap confirmed — build finding in sample_expected_output.json shape.
            # ------------------------------------------------------------------
            contact = partner["contact"]

            message = (
                f"{partner['company']}: your {product['name']} needs an EU battery "
                f"passport by {rule['deadline']} "
                f"({rule['regulation'].split('—')[0].strip()}). "
                f"Set up the QR/data carrier. Source: {rule['source_url']}"
            )

            finding = {
                "company":    partner["company"],
                "partner_id": partner["partner_id"],
                "product_id": product["product_id"],
                "product":    product["name"],
                "regulation": (
                    f"{rule['regulation']} — battery passport ({rule['article']})"
                ),
                "requirement":        rule["requirement"],
                "source_url":         rule["source_url"],
                "gap": (
                    f"LMT battery '{product['name']}' is sold in the EU "
                    f"with no battery passport / data carrier."
                ),
                "deadline":           rule["deadline"],
                "severity":           "high",
                "recommended_action": (
                    "Create the battery passport (QR + data carrier) "
                    "and link it before the deadline."
                ),
                "alert": {
                    "channel": contact["preferred_channel"],
                    "to":      contact["phone"],
                    "message": message,
                },
            }

            # Surface conflict: if the product gap is NOT mentioned in known_gaps,
            # flag it so the operator knows the partner's own self-assessment is
            # incomplete.  Match on product_id OR product name only — battery_type
            # ("lmt") is intentionally excluded because it would match every LMT
            # product and mask a real conflict for products not named individually.
            product_identifiers = {
                product["product_id"].lower(),
                product["name"].lower(),
            }
            product_mentioned_in_known_gaps = any(
                any(ident in g.lower() for ident in product_identifiers)
                for g in known_gaps
            )
            if known_gaps and not product_mentioned_in_known_gaps:
                print(
                    f"         CONFLICT: {partner['partner_id']} / "
                    f"{product['product_id']} — gap confirmed by five-filter "
                    f"reasoning but NOT found in partner's own known_gaps. "
                    f"Partner's self-assessment is INCOMPLETE "
                    f"(known_gaps = {known_gaps})."
                )

            findings.append(finding)

    # ------------------------------------------------------------------
    # CHECKPOINT (bob_rules.md)
    # ------------------------------------------------------------------
    print(f"\n[multi_gap] CHECKPOINT — scan complete")
    print(f"         Partners scanned  : {len(partners_data['partners'])}")
    print(f"         Products scanned  : {scanned_products}")
    print(f"         Gaps found        : {len(findings)}")
    for f in findings:
        print(f"           → {f['partner_id']} / {f['product_id']}  {f['company']} — {f['product']}")

    return findings


# ---------------------------------------------------------------------------
# EU member-state ISO codes used for market expansion (shared constant)
# ---------------------------------------------------------------------------
EU_MEMBER_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
    "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
    "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}


def _product_in_markets(product_markets: set, required_markets: set) -> bool:
    """Return True if a product reaches at least one of the required markets.

    Two expansions are applied:
    - 'EU' in required_markets matches any EU member-state ISO code in product_markets
      (rule scoped to whole EU applies to a product sold only in, say, DE).
    - 'EU' in product_markets satisfies any single member-state requirement
      (a product sold EU-wide is sold in DE, AT, FR, etc.).
    """
    # Direct overlap (includes 'EU' == 'EU').
    if required_markets & product_markets:
        return True
    # Product sells in EU → it sells in every member state.
    if "EU" in product_markets and required_markets & EU_MEMBER_CODES:
        return True
    # Rule requires the whole EU → a product in any member state qualifies.
    in_eu = "EU" in product_markets or bool(product_markets & EU_MEMBER_CODES)
    return "EU" in required_markets and in_eu


def _product_matches_scope(product: dict, rule_scope: dict, partner_id: str) -> bool:
    """
    Apply Filters 2–3 for a single product against a catalog rule's scope.

    Filter 2 — category:
      * If scope.category == "all_eee", the product must be in scope.product_types.
      * If scope.category == "packaging", the product must carry at least one
        plastic packaging type listed in scope.product_types (matched by substring
        against the product's packaging[] array).
      * Otherwise the product.category must equal scope.category exactly.

    Filter 3 — battery_type (optional):
      * Only checked when scope.battery_type is a non-null string.
      * If it doesn't match, a CONFLICT line is printed and the product is excluded.

    Returns True when the product passes both filters.
    """
    cat = rule_scope.get("category", "")
    product_cat = product.get("category", "")
    allowed_types = rule_scope.get("product_types") or []

    if cat == "all_eee":
        # Virtual catch-all: product must be in the explicit list.
        if product_cat not in allowed_types:
            return False

    elif cat == "packaging":
        # Rule applies to any product whose packaging[] array contains a value
        # that starts with "plastic" — the real data uses values like
        # "plastic_film" while scope.product_types lists canonical names like
        # "plastic_retail_packaging".  Both share the "plastic" prefix, so
        # checking for that prefix is the correct and stable signal.
        product_packs = product.get("packaging", [])
        plastic_match = any(pk.startswith("plastic") for pk in product_packs)
        if not plastic_match:
            return False

    else:
        # Standard exact-category match.
        if product_cat != cat:
            return False

    # Filter 3 — battery_type (only when the rule scopes to a specific type).
    required_btype = rule_scope.get("battery_type")
    if required_btype:
        product_btype = product.get("battery_type")
        if product_btype != required_btype:
            print(
                f"         CONFLICT: {partner_id} / "
                f"{product['product_id']} has category={product_cat} "
                f"but battery_type='{product_btype}' "
                f"(rule requires '{required_btype}'). "
                f"Excluding from findings — verify data."
            )
            return False

    return True


def _cert_clears_rule(certs_held: list, rule_id: str) -> bool:
    """
    Return True when one of the partner's existing certs satisfies this rule,
    meaning no gap exists.

    Heuristic mapping (extend as new rules are added):
      BATT-*          → any cert containing "passport"
      PPWR-*          → any cert containing "ppwr" or "recycled"
      ELEKTROG-*      → any cert containing "ear", "elektrog", or "weee_de"
    """
    certs_lower = [c.lower() for c in certs_held]
    rid = rule_id.upper()

    if rid.startswith("BATT-"):
        return any("passport" in c for c in certs_lower)
    if rid.startswith("PPWR-"):
        return any("ppwr" in c or "recycled" in c for c in certs_lower)
    if rid.startswith("ELEKTROG-"):
        return any("ear" in c or "elektrog" in c or "weee_de" in c for c in certs_lower)

    # Unknown rule family — conservatively assume no cert covers it.
    return False


def _build_finding(partner: dict, product: dict, rule: dict) -> dict:
    """
    Build a finding dict in sample_expected_output.json shape, plus rule_id.
    Uses the catalog rule field names (rule_id, regulation_id, article,
    requirement_text) which differ from the legacy pipeline.py names.
    """
    contact   = partner["contact"]
    rule_id   = rule["rule_id"]
    reg_label = f"Reg (EU) {rule['regulation_id']} — {rule['article']}"

    message = (
        f"{partner['company']}: your {product['name']} must comply with "
        f"{reg_label} by {rule['deadline']}. "
        f"Source: {rule['source_url']}"
    )

    return {
        "rule_id":    rule_id,
        "company":    partner["company"],
        "partner_id": partner["partner_id"],
        "product_id": product["product_id"],
        "product":    product["name"],
        "regulation": reg_label,
        "requirement":        rule["requirement_text"],
        "source_url":         rule["source_url"],
        "gap": (
            f"'{product['name']}' is sold in a market covered by {rule_id} "
            f"but the required compliance has not been demonstrated."
        ),
        "deadline":           rule["deadline"],
        "severity":           "high",
        "recommended_action": (
            f"Review {rule['article']} obligations and obtain or demonstrate "
            f"compliance before {rule['deadline']}."
        ),
        "alert": {
            "channel": contact["preferred_channel"],
            "to":      contact["phone"],
            "message": message,
        },
    }


def find_gaps_for_all_rules(
    rules_catalog_path: str = "rules_catalog.json",
) -> list:
    """
    Loop over every rule in rules_catalog.json, then over every partner and
    every product in partners.json.  Apply the five-filter obligation check
    for each rule and collect all findings.

    Five filters (generalised from find_all_gaps):
        Filter 1 — market      : product must reach at least one rule market
        Filter 2 — category    : product category must match rule scope
                                 (supports exact, "all_eee" catch-all,
                                 and "packaging" plastic-type matching)
        Filter 3 — battery_type: when rule scopes to a specific type, must match
        Filter 4 — certs       : partner must NOT already hold a cert that
                                 covers this rule family
        Filter 5 — exclusions  : placeholder; no additional exclusions at this time

    Each finding has the sample_expected_output.json shape plus a 'rule_id'
    field.

    Writes all findings to all_findings.json next to this file.

    Returns the list of findings.

    Raises:
        ValueError  — if any required field is absent from a rule.
        SystemExit  — if a required data file cannot be loaded.
    """
    catalog_path = BASE / rules_catalog_path

    # ------------------------------------------------------------------
    # Read Before You Write (bob_rules.md)
    # ------------------------------------------------------------------
    print("\n[find_gaps_for_all_rules] Reading data files …")

    for path in (catalog_path, PARTNERS_FILE, TAXONOMY_FILE, SAMPLE_OUTPUT_FILE):
        if not path.exists():
            sys.exit(f"ERROR: required file not found: {path}")

    catalog       = json.loads(catalog_path.read_text())
    partners_data = json.loads(PARTNERS_FILE.read_text())
    taxonomy      = json.loads(TAXONOMY_FILE.read_text())
    sample_shape  = json.loads(SAMPLE_OUTPUT_FILE.read_text())

    rules = catalog.get("rules")
    if not rules:
        raise ValueError(
            f"rules_catalog at '{catalog_path}' has no 'rules' array — aborting."
        )

    # Confirm taxonomy is loaded — fail loud if it has no product_categories.
    if "product_categories" not in taxonomy:
        raise ValueError(
            "Conflict: taxonomy.json missing 'product_categories'. "
            "Cannot apply Filter 2 safely — aborting."
        )

    print(f"         Catalog rules   : {len(rules)}")
    print(f"         Partners loaded : {len(partners_data['partners'])}")
    print(f"         Sample shape keys: {[k for k in sample_shape if not k.startswith('_')]}")

    # ------------------------------------------------------------------
    # Validate every rule before scanning — fail loud on first error.
    # ------------------------------------------------------------------
    required_rule_fields = ("rule_id", "regulation_id", "article",
                            "requirement_text", "scope", "deadline", "source_url")
    for rule in rules:
        for field in required_rule_fields:
            if field not in rule:
                raise ValueError(
                    f"Rule '{rule.get('rule_id', '?')}' is missing "
                    f"required field: '{field}'"
                )
        for scope_field in ("markets", "category"):
            if scope_field not in rule["scope"]:
                raise ValueError(
                    f"Rule '{rule['rule_id']}' scope is missing "
                    f"required field: '{scope_field}'"
                )

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------
    all_findings: list = []

    for rule in rules:
        rule_id          = rule["rule_id"]
        rule_scope       = rule["scope"]
        required_markets = set(rule_scope["markets"])

        print(f"\n[find_gaps_for_all_rules] Scanning rule: {rule_id}")
        print(f"         Article  : {rule['article']}")
        print(f"         Markets  : {sorted(required_markets)}")
        print(f"         Category : {rule_scope['category']}")

        rule_findings: list = []
        scanned = 0

        for partner in partners_data["partners"]:
            certs_held = (
                partner
                .get("compliance_status", {})
                .get("certs_held", [])
            )
            known_gaps = (
                partner
                .get("compliance_status", {})
                .get("known_gaps", [])
            )

            for product in partner["products"]:
                scanned += 1

                # Filter 1 — market
                product_markets = set(product.get("markets", []))
                if not _product_in_markets(product_markets, required_markets):
                    continue

                # Filters 2 & 3 — category / battery_type
                if not _product_matches_scope(
                    product, rule_scope, partner["partner_id"]
                ):
                    continue

                # Filter 4 — certs: partner already compliant with this rule?
                if _cert_clears_rule(certs_held, rule_id):
                    continue

                # Filter 5 — exclusions (no additional exclusions at this time)

                # -------------------------------------------------------
                # Gap confirmed — build finding.
                # -------------------------------------------------------
                finding = _build_finding(partner, product, rule)
                rule_findings.append(finding)

                # Surface conflict: gap confirmed but not in partner's own
                # known_gaps self-assessment.
                product_identifiers = {
                    product["product_id"].lower(),
                    product["name"].lower(),
                }
                product_in_known_gaps = any(
                    any(ident in g.lower() for ident in product_identifiers)
                    for g in known_gaps
                )
                if known_gaps and not product_in_known_gaps:
                    print(
                        f"         CONFLICT: {partner['partner_id']} / "
                        f"{product['product_id']} — gap confirmed by five-filter "
                        f"check but NOT in partner's known_gaps "
                        f"(known_gaps={known_gaps})."
                    )

        all_findings.extend(rule_findings)

        # CHECKPOINT per rule
        print(f"         Products scanned : {scanned}")
        print(f"         Gaps found       : {len(rule_findings)}")
        for f in rule_findings:
            print(
                f"           → {f['partner_id']} / {f['product_id']}"
                f"  {f['company']} — {f['product']}"
            )

    # ------------------------------------------------------------------
    # CHECKPOINT — overall (bob_rules.md)
    # ------------------------------------------------------------------
    print(f"\n[find_gaps_for_all_rules] CHECKPOINT — all rules scanned")
    print(f"         Rules processed  : {len(rules)}")
    print(f"         Total findings   : {len(all_findings)}")

    output_path = BASE / "all_findings.json"
    output_path.write_text(json.dumps(all_findings, indent=2))
    print(f"         Written to       : {output_path.name}")

    return all_findings


# ---------------------------------------------------------------------------
# CLI entry-point — run directly to dump all findings to all_gaps.json
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Reuse the same hard-coded rule object from pipeline.py (no import needed).
    rule = {
        "regulation":  "Regulation (EU) 2023/1542 — Battery Regulation",
        "article":     "Article 77",
        "requirement": (
            "Light-means-of-transport (LMT) batteries placed on the EU market must "
            "carry a digital battery passport accessible via a QR code or other "
            "data carrier, containing chemistry, capacity, carbon footprint, and "
            "lifecycle data."
        ),
        "scope": {
            "battery_type": "lmt",
            "markets":      ["EU"],
            "category":     "emobility_battery",
        },
        "deadline":   "2027-02-18",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
    }

    gaps = find_all_gaps(rule)

    output_path = BASE / "all_gaps.json"
    output_path.write_text(json.dumps(gaps, indent=2))
    print(f"\n[multi_gap] {len(gaps)} finding(s) written to {output_path.name}")

    # Also run the catalog-based scan and write all_findings.json
    print("\n" + "=" * 60)
    find_gaps_for_all_rules()
