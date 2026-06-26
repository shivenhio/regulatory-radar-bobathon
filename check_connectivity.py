import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime

# =========================
# SOURCES
# =========================

SOURCES = {
    "safety_gate_rss": "https://ec.europa.eu/safety-gate-alerts/screen/webService/rss",
    "echa_reference": "https://echa.europa.eu/candidate-list-table"
}

# =========================
# SAFE XML HELPER
# =========================

def safe_text(elem):
    return elem.text.strip() if elem is not None and elem.text else ""


# =========================
# SAFETY GATE RSS FETCH
# =========================

def fetch_safety_gate():
    print("\n📡 Fetching Safety Gate RSS...\n")

    try:
        response = requests.get(SOURCES["safety_gate_rss"], timeout=15)
        response.raise_for_status()

        xml_data = response.text

        # Debug fallback (uncomment if needed)
        # print(xml_data[:500])

        root = ET.fromstring(xml_data)

        alerts = []

        # Namespace-safe parsing
        for item in root.findall(".//{*}item"):

            title = safe_text(item.find("{*}title"))
            link = safe_text(item.find("{*}link"))

            # Skip broken entries
            if not title and not link:
                continue

            alerts.append({
                "title": title,
                "source_url": link,
                "fetched_date": str(datetime.today().date())
            })

        print(f"✅ Retrieved {len(alerts)} alerts")

        return alerts

    except Exception as e:
        print(f"❌ Safety Gate fetch failed: {e}")
        return []


# =========================
# ECHA CHECK (REFERENCE ONLY)
# =========================

def check_echa_access():
    print("\n🧪 Checking ECHA accessibility...\n")

    try:
        r = requests.get(SOURCES["echa_reference"], timeout=15)

        print(f"HTTP Status: {r.status_code}")

        if r.status_code == 200:
            print("✅ ECHA accessible (manual extraction required)")
        elif r.status_code == 403:
            print("⚠️ ECHA blocks automation → manual extraction required")
        else:
            print("⚠️ Unexpected response → treat as manual-only source")

    except Exception as e:
        print(f"❌ ECHA check failed: {e}")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("\n=== STEP 2 SOURCE VALIDATION ===")

    # 1. Safety Gate RSS (real usable API feed)
    alerts = fetch_safety_gate()

    # 2. ECHA check (manual-only source)
    check_echa_access()

    # 3. Save output snapshot
    output = {
        "safety_gate_sample": alerts[:10],
        "total_alerts": len(alerts),
        "generated_at": str(datetime.today())
    }

    with open("step2_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n✅ Step 2 complete → step2_output.json created")