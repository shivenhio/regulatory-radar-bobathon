import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

REQUIRED_COLUMNS = {
    "markets", "intended_use", "has_battery", "battery_type",
    "battery_capacity_wh", "connector", "substances",
    "company", "partner_id", "product_id", "product_name",
    "contact_email", "contact_phone", "preferred_channel",
}

CACHE_DIR = Path("rules_cache")
RULES_CATALOG = Path("rules_catalog.json")


class ComplianceEngine:
    def __init__(self, data_file: str):
        self.data_file = Path(data_file)
        self.rules = self._build_rules()

    # ------------------------------------------------------------------
    # Rule loading
    # ------------------------------------------------------------------

    def _build_rules(self) -> List[Dict[str, Any]]:
        """
        Build the active rule list by merging live-fetched rules from
        rules_cache/ with the hardcoded fallback set.

        Live rules (from rules_cache/) take precedence: if a cached file
        exists for a rule id, its metadata (deadline, source_url, summary)
        overrides the hardcoded values. The applies/gap/action logic stays
        in Python because it needs to inspect each product row at runtime.
        """
        live = self._load_live_rules()
        fallback = self._hardcoded_rules()
        catalog = self._load_catalog_rules()

        # Index live obligations by id so we can override fallback metadata
        live_by_id: Dict[str, Dict] = {}
        for reg in live.values():
            for ob in reg.get("obligations", []):
                live_by_id[ob["id"]] = {
                    "name": ob.get("name"),
                    "deadline": ob.get("deadline"),
                    "severity": ob.get("severity"),
                    "source_url": reg.get("source_url"),
                    "article": ob.get("article", ""),
                    "summary": ob.get("summary", ""),
                    "live": True,
                }

        # Merge live cache metadata into hardcoded rules
        merged = []
        for rule in fallback:
            override = live_by_id.get(rule["id"], {})
            merged.append({
                **rule,
                "name": override.get("name") or rule["name"],
                "deadline": override.get("deadline") or rule["deadline"],
                "severity": override.get("severity") or rule["severity"],
                "source_url": override.get("source_url") or rule["source_url"],
                "article": override.get("article", ""),
                "summary": override.get("summary", ""),
                "live_source": override.get("live", False),
            })

        # Append catalog rules, skipping any whose id is already covered
        existing_ids = {r["id"] for r in merged}
        catalog_added = 0
        for rule in catalog:
            if rule["id"] not in existing_ids:
                merged.append(rule)
                catalog_added += 1

        live_count = sum(1 for r in merged if r.get("live_source"))
        print(f"[ComplianceEngine] {len(merged)} rules loaded "
              f"({live_count} live-fetched, "
              f"{catalog_added} from rules_catalog.json, "
              f"{len(merged) - live_count - catalog_added} fallback)")
        return merged

    def _load_live_rules(self) -> Dict[str, Dict]:
        """Load all JSON files from rules_cache/ into a dict keyed by filename stem."""
        live = {}
        if not CACHE_DIR.exists():
            return live
        for path in sorted(CACHE_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                live[path.stem] = data
            except Exception as e:
                print(f"[ComplianceEngine] Warning: could not load {path}: {e}")
        print(f"[ComplianceEngine] Loaded {len(live)} cached rule file(s) from {CACHE_DIR}/")
        return live

    def _load_catalog_rules(self) -> List[Dict[str, Any]]:
        """
        Load rules from rules_catalog.json and convert them into the same
        internal format as _hardcoded_rules() so they can be merged and
        matched by the engine.
        """
        if not RULES_CATALOG.exists():
            return []

        try:
            catalog = json.loads(RULES_CATALOG.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ComplianceEngine] Warning: could not load {RULES_CATALOG}: {e}")
            return []

        rules = []
        for entry in catalog.get("rules", []):
            rule_id = entry.get("rule_id", "")
            scope   = entry.get("scope", {})
            req     = entry.get("requirement_text", "")
            deadline = entry.get("deadline", "")
            source_url = entry.get("source_url", "")
            article = entry.get("article", "")
            severity = entry.get("severity", "high")
            markets = scope.get("markets", ["EU"])
            battery_type = scope.get("battery_type")
            product_types = scope.get("product_types") or []
            category = scope.get("category", "")

            # Build an applies lambda from the catalog scope fields
            def make_applies(mkts, btype, cat, ptypes):
                def applies(r):
                    # Market check
                    if not any(m in str(r.get("markets", "")).split("|") for m in mkts):
                        return False
                    # Battery type check (only when rule scopes to one)
                    if btype and r.get("battery_type") != btype:
                        return False
                    # Category / product_types check
                    if cat == "all_eee":
                        return True  # applies to all electronics
                    if cat == "packaging":
                        # Applies when product has plastic packaging
                        pkg = str(r.get("packaging", "")).lower()
                        return "plastic" in pkg or any(
                            p in pkg for p in ["film", "blister", "tray"]
                        )
                    if ptypes:
                        return r.get("category", "") in ptypes
                    return True
                return applies

            rules.append({
                "id":         rule_id,
                "rule_id":    rule_id,
                "name":       f"{entry.get('regulation_id','')} — {article}",
                "article":    article,
                "deadline":   deadline,
                "severity":   severity,
                "source_url": source_url,
                "summary":    req,
                "live_source": False,
                "from_catalog": True,
                "applies":    make_applies(markets, battery_type, category, product_types),
                "gap":        lambda r, rid=rule_id, rq=req: (
                    f"'{r.get('product_name','')}' may be subject to {rid}: {rq[:120]}"
                ),
                "action":     lambda r, art=article, dl=deadline: (
                    f"Review {art} obligations and ensure compliance before {dl}."
                ),
            })

        print(f"[ComplianceEngine] Loaded {len(rules)} rule(s) from {RULES_CATALOG}")
        return rules

    def _hardcoded_rules(self) -> List[Dict[str, Any]]:
        """
        Fallback rule definitions with applies/gap/action logic.
        These are always present; metadata is overridden by live cache when available.
        """
        return [
            {
                "id": "battery_passport",
                "name": "Battery passport",
                "deadline": "2027-02-18",
                "severity": "high",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and self._to_bool(r.get("has_battery"))
                    and r.get("battery_type") in {"lmt", "industrial"}
                    and float(r.get("battery_capacity_wh") or 0) > 2,
                "gap": lambda r: "Battery passport required for LMT or industrial battery > 2 kWh.",
                "action": lambda r: "Create QR/data-carrier battery passport before the deadline.",
            },
            {
                "id": "battery_removability",
                "name": "Battery removability",
                "deadline": "2027-02-18",
                "severity": "high",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and r.get("intended_use") in {"consumer", "toy"}
                    and self._to_bool(r.get("has_battery"))
                    and r.get("battery_type") in {"portable", "button_cell"},
                "gap": lambda r: "Battery must be user-removable and replaceable.",
                "action": lambda r: "Redesign enclosure so the user can remove and replace the battery.",
            },
            {
                "id": "battery_carbon_footprint",
                "name": "Carbon footprint declaration (EV / industrial)",
                "deadline": "2025-02-18",
                "severity": "high",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and self._to_bool(r.get("has_battery"))
                    and r.get("battery_type") in {"ev", "industrial"},
                "gap": lambda r: "Carbon footprint declaration required for EV or industrial battery.",
                "action": lambda r: "Calculate and declare lifecycle carbon footprint per Annex II methodology.",
            },
            {
                "id": "common_charger",
                "name": "USB-C common charger",
                "deadline": "2024-12-28",
                "severity": "high",
                "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2380",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and r.get("intended_use") in {"consumer", "toy"}
                    and str(r.get("connector")).lower() in {"micro_usb", "microusb", "barrel", "proprietary"},
                "gap": lambda r: "USB-C is required for wired charging on this product class.",
                "action": lambda r: "Replace the wired charging port with USB-C.",
            },
            {
                "id": "gpsr_button_cell",
                "name": "Button-cell child safety",
                "deadline": "2024-12-13",
                "severity": "high",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2023/988/oj",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and r.get("intended_use") in {"consumer", "toy"}
                    and self._to_bool(r.get("has_battery"))
                    and r.get("battery_type") == "button_cell",
                "gap": lambda r: "Button-cell compartment must be secured against child access.",
                "action": lambda r: "Add tool-required or screw-fastened battery compartment and warnings.",
            },
            {
                "id": "reach_svhc",
                "name": "REACH SVHC screening",
                "deadline": "2026-10-30",
                "severity": "medium",
                "source_url": "https://echa.europa.eu/candidate-list-table",
                "applies": lambda r: self._markets_include_eu(r.get("markets"))
                    and any(
                        s in {"BPA", "DEHP", "TBBPA", "PFAS_PFHxA", "MCCP", "PFOA", "PFOS", "DBP", "BBP", "DIBP"}
                        for s in self._substances_list(r.get("substances"))
                    ),
                "gap": lambda r: "SVHC screening and customer/SCIP duties may apply.",
                "action": lambda r: "Screen articles and file SCIP notifications where required.",
            },
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bool(v: Any) -> bool:
        return str(v).strip().lower() == "true"

    @staticmethod
    def _markets_include_eu(v: Any) -> bool:
        return "EU" in str(v).split("|")

    @staticmethod
    def _substances_list(v: Any) -> List[str]:
        v = str(v).strip()
        if not v:
            return []
        return [s.strip() for s in v.split("|") if s.strip()]

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def parse_records(self) -> List[Dict[str, str]]:
        """Parse the CSV input file into a list of row dicts."""
        records = []
        with open(self.data_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records

    def generate_alerts(self, records: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Evaluate every rule against every product record; return matching alerts."""
        alerts = []
        for r in records:
            for rule in self.rules:
                if rule["applies"](r):
                    product_name = r.get("product_name", "")
                    company = r.get("company", "")
                    deadline = rule["deadline"]
                    source_url = rule["source_url"]
                    gap_text = rule["gap"](r)
                    action_text = rule["action"](r)
                    rule_id = rule.get("rule_id") or rule["id"]
                    alerts.append({
                        # Core fields — matches all_findings.json / sample_expected_output.json shape
                        "rule_id":            rule_id,
                        "company":            company,
                        "partner_id":         r.get("partner_id"),
                        "product_id":         r.get("product_id"),
                        "product":            product_name,
                        "product_name":       product_name,
                        "regulation":         rule["name"],
                        "article":            rule.get("article", ""),
                        "requirement":        rule.get("summary", ""),
                        "severity":           rule["severity"],
                        "deadline":           deadline,
                        "gap":                gap_text,
                        "recommended_action": action_text,
                        "source_url":         source_url,
                        "live_source":        rule.get("live_source", False),
                        # Contact info
                        "contact_email":      r.get("contact_email"),
                        "contact_phone":      r.get("contact_phone"),
                        "preferred_channel":  r.get("preferred_channel"),
                        # Alert block matching sample_expected_output.json
                        "alert": {
                            "channel": r.get("preferred_channel", "email"),
                            "to":      r.get("contact_email") or r.get("contact_phone", ""),
                            "message": (
                                f"{company}: your {product_name} must comply with "
                                f"{rule_id} by {deadline}. "
                                f"{action_text} Source: {source_url}"
                            ),
                        },
                    })
        return alerts


# ------------------------------------------------------------------
# Dataset discovery
# ------------------------------------------------------------------

def find_dataset(candidates: List[str]) -> str:
    """Return the first existing file from the candidate list."""
    for cand in candidates:
        if Path(cand).exists():
            return cand
    raise FileNotFoundError("No dataset file found. Tried: " + ", ".join(candidates))


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    try:
        # 1. Locate the CSV
        if len(sys.argv) > 1:
            target_file = sys.argv[1]
            if not Path(target_file).exists():
                raise FileNotFoundError(f"File not found: {target_file}")
        else:
            target_file = find_dataset(["partners.csv", "paste.txt", "paste-2.txt"])

        # 2. Build engine (loads live cache automatically)
        engine = ComplianceEngine(target_file)
        product_records = engine.parse_records()

        # 3. Validate columns
        if product_records:
            missing = REQUIRED_COLUMNS - set(product_records[0].keys())
            if missing:
                raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        # 4. Assess
        generated_alerts = engine.generate_alerts(product_records)

        # 5. Write results — both files so alerts.py can consume all_findings.json
        output = json.dumps(generated_alerts, indent=2, ensure_ascii=False)
        Path("alerts.json").write_text(output, encoding="utf-8")
        Path("all_findings.json").write_text(output, encoding="utf-8")

        # 6. Print summary
        live_alerts = sum(1 for a in generated_alerts if a.get("live_source"))
        catalog_alerts = sum(1 for a in generated_alerts if a.get("rule_id", "").count("-") >= 2)
        print(json.dumps({
            "products_parsed": len(product_records),
            "alerts_generated": len(generated_alerts),
            "alerts_from_live_rules": live_alerts,
            "alerts_from_catalog_rules": catalog_alerts,
            "alerts_from_fallback_rules": len(generated_alerts) - live_alerts - catalog_alerts,
        }, indent=2))

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
