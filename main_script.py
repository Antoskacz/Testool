import json
import re
import subprocess
from pathlib import Path
import pandas as pd
import time
import unicodedata
import copy

# --- Cesty ---
BASE_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = BASE_DIR / "exports"
KROKY_PATH = BASE_DIR / "kroky.json"
PROJEKTY_PATH = BASE_DIR / "projekty.json"

# --- Globální proměnné ---
AKTUALNI_PROJEKT = None
projekty_data = {}

# --- Statické hodnoty ---
SYSTEM_APPLICATION = "Siebel_CZ"
TYPE = "Manual"
TEST_PHASE = "4-User Acceptance"
TEST_TEST_PHASE = "4-User Acceptance"
PRIORITY_MAP = {"1": "1-High", "2": "2-Medium", "3": "3-Low"}
COMPLEXITY_MAP = {"1": "1-Giant", "2": "2-Huge", "3": "3-Big", "4": "4-Medium", "5": "5-Low"}


# --- Pomocné funkce ---
def safe_print(text):
    print(text, flush=True)
    time.sleep(0.05)


def nacti_projekty():
    if PROJEKTY_PATH.exists():
        with open(PROJEKTY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def uloz_projekty():
    with open(PROJEKTY_PATH, "w", encoding="utf-8") as f:
        json.dump(projekty_data, f, ensure_ascii=False, indent=2)


def nacti_kroky():
    if not KROKY_PATH.exists():
        safe_print("⚠️ Soubor kroky.json nebyl nalezen! Vytvořím prázdný.")
        return {}
    with open(KROKY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.replace(" ", "_").replace("__", "_")


def extract_kanal(text: str) -> str:
    t = text.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"


def extract_segment(text: str) -> str:
    t = text.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"


def extract_service(text: str) -> str:
    t = text.lower()
    if "hlas" in t or "voice" in t:
        return "HLAS"
    if "fwa" in t and "bisi" in t:
        return "FWA_BISI"
    if "fwa" in t and re.search(r"\bbi\b", t):
        return "FWA_BI"
    for key in ["dsl", "fiber", "cable"]:
        if key in t:
            return key.upper()
    if "fwa" in t:
        return "FWA"
    return "UNKNOWN"


def build_test_name(poradi: int, veta: str) -> str:
    kanal = extract_kanal(veta)
    segment = extract_segment(veta)
    service = extract_service(veta)

    # Neupravujeme text věty – zůstává kompletní a nezměněná
    prefix = f"{poradi:03d}_{kanal}_{segment}_{service}"
    return f"{prefix}_{veta.strip().capitalize()}"


def detect_action(text: str, kroky_data: dict) -> str | None:
    t = text.lower()
    for akce in kroky_data.keys():
        if akce.lower() in t:
            return akce
    return None


def generuj_testcase(veta, kroky_data, akce, priority, complexity):
    poradi = projekty_data[AKTUALNI_PROJEKT]["next_id"]
    projekty_data[AKTUALNI_PROJEKT]["next_id"] += 1

    test_name = build_test_name(poradi, veta)
    segment = extract_segment(veta)
    kanal = extract_kanal(veta)

    # DŮLEŽITÉ: Použij deepcopy pro kroky
    kroky_pro_akci = copy.deepcopy(kroky_data.get(akce, []))

    tc = {
        "order_no": poradi,
        "test_name": test_name,
        "akce": akce,
        "segment": segment,
        "kanal": kanal,
        "priority": priority,
        "complexity": complexity,
        "veta": veta,
        "kroky": kroky_pro_akci,  # Tady používáme hlubokou kopii
    }

    projekty_data[AKTUALNI_PROJEKT]["scenarios"].append(tc)
    uloz_projekty()
    return tc


def debug_kroky():
    """Funkce pro ladění přiřazování kroků"""
    kroky_data = nacti_kroky()
    
    print("\n=== DEBUG KROKY ===")
    for akce in kroky_data.keys():
        kroky = kroky_data[akce]
        print(f"Akce: {akce}")
        print(f"  Počet kroků: {len(kroky)}")
        if kroky:
            print(f"  První krok: {kroky[0]['description'][:50]}...")
        print(f"  ID objektu: {id(kroky)}")
        print()
    
    # Test deepcopy
    if kroky_data:
        test_akce = list(kroky_data.keys())[0]
        original = kroky_data[test_akce]
        kopie = copy.deepcopy(kroky_data[test_akce])
        
        print(f"Test deepcopy pro '{test_akce}':")
        print(f"  Original ID: {id(original)}")
        print(f"  Kopie ID: {id(kopie)}")
        print(f"  Jsou stejné objekty? {original is kopie}")
        print(f"  Jsou stejné data? {original == kopie}")


# --- Správa projektů ---
def vyber_projekt():
    global AKTUALNI_PROJEKT
    safe_print("\n--- Správce projektů ---")
    if projekty_data:
        for idx, p in enumerate(projekty_data.keys(), start=1):
            safe_print(f"{idx}. {p}")

    volba = input("Zadej číslo existujícího projektu nebo nový název: ").strip()
    if volba.isdigit():
        idx = int(volba) - 1
        if 0 <= idx < len(projekty_data):
            AKTUALNI_PROJEKT = list(projekty_data.keys())[idx]
            safe_print(f"🔹 Načten projekt: {AKTUALNI_PROJEKT}")
            return
    else:
        subject = input("Zadej Subject (Enter = default UAT2\\Antosova\\): ").strip() or "UAT2\\Antosova\\"
        projekty_data[volba] = {"next_id": 1, "subject": subject, "scenarios": []}
        uloz_projekty()
        AKTUALNI_PROJEKT = volba
        safe_print(f"✅ Nový projekt {volba} vytvořen.")


def uprav_projekt():
    if not projekty_data:
        safe_print("⚠️ Žádné projekty k úpravě.")
        return

    for idx, p in enumerate(projekty_data.keys(), start=1):
        safe_print(f"{idx}. {p}")

    volba = input("Zadej číslo projektu k úpravě: ").strip()
    if not volba.isdigit():
        return
    idx = int(volba) - 1
    if idx >= len(projekty_data):
        return

    nazev = list(projekty_data.keys())[idx]
    projekt = projekty_data[nazev]

    safe_print(f"\n--- Úprava projektu {nazev} ---")
    safe_print("1. Změnit název")
    safe_print("2. Upravit Subject (HPQC umístění)")
    vyber = input("Zvol: ").strip()

    if vyber == "1":
        novy = input("Zadej nový název: ").strip()
        if novy:
            projekty_data[novy] = projekty_data.pop(nazev)
            global AKTUALNI_PROJEKT
            if AKTUALNI_PROJEKT == nazev:
                AKTUALNI_PROJEKT = novy
            safe_print(f"✅ Projekt přejmenován na {novy}")
    elif vyber == "2":
        novy_subject = input(f"Zadej nový Subject (aktuální: {projekt.get('subject','None')}): ").strip()
        if not novy_subject:
            novy_subject = "UAT2\\Antosova\\"
        projekt["subject"] = novy_subject
        safe_print(f"✅ Subject změněn na: {novy_subject}")

    uloz_projekty()


def smaz_projekt():
    if not projekty_data:
        safe_print("⚠️ Žádné projekty.")
        return
    for idx, p in enumerate(projekty_data.keys(), start=1):
        safe_print(f"{idx}. {p}")
    volba = input("Zadej číslo projektu k odstranění: ").strip()
    if volba.isdigit():
        idx = int(volba) - 1
        if 0 <= idx < len(projekty_data):
            nazev = list(projekty_data.keys())[idx]
            potvrdit = input(f"Opravdu smazat {nazev}? (ano/ne): ").strip().lower()
            if potvrdit == "ano":
                projekty_data.pop(nazev)
                uloz_projekty()
                safe_print("✅ Projekt smazán.")


# --- Úprava a mazání scénářů ---
def uprav_scenar():
    sc = projekty_data[AKTUALNI_PROJEKT]["scenarios"]
    if not sc:
        safe_print("⚠️ Žádné scénáře k úpravě.")
        return

    for idx, tc in enumerate(sc, start=1):
        safe_print(f"{idx}. {tc['test_name']}")

    volba = input("Zadej číslo scénáře: ").strip()
    if not volba.isdigit():
        return
    idx = int(volba) - 1
    if idx >= len(sc):
        return

    tc = sc[idx]
    safe_print(f"\n--- Úprava scénáře {tc['test_name']} ---")
    safe_print("1. Změnit název")
    safe_print("2. Změnit prioritu")
    safe_print("3. Změnit komplexitu")
    vyber = input("Zvol: ").strip()

    if vyber == "1":
        novy = input("Zadej nový název: ").strip()
        if novy:
            tc["test_name"] = novy
            safe_print("✅ Název změněn.")
    elif vyber == "2":
        p = input("Nová priorita (1=High,2=Medium,3=Low): ").strip()
        tc["priority"] = PRIORITY_MAP.get(p, tc["priority"])
        safe_print("✅ Priorita změněna.")
    elif vyber == "3":
        c = input("Nová komplexita (1–5): ").strip()
        tc["complexity"] = COMPLEXITY_MAP.get(c, tc["complexity"])
        safe_print("✅ Komplexita změněna.")

    uloz_projekty()


def smaz_scenar():
    sc = projekty_data[AKTUALNI_PROJEKT]["scenarios"]
    if not sc:
        safe_print("⚠️ Žádné scénáře.")
        return

    for idx, tc in enumerate(sc, start=1):
        safe_print(f"{idx}. {tc['test_name']}")
    volba = input("Zadej číslo scénáře k odstranění: ").strip()
    if volba.isdigit():
        idx = int(volba) - 1
        if 0 <= idx < len(sc):
            potvrdit = input("Opravdu smazat? (ano/ne): ").strip().lower()
            if potvrdit == "ano":
                sc.pop(idx)
                # 🧩 Přepočet pořadí po smazání
                for i, t in enumerate(sc, start=1):
                    t["order_no"] = i
                uloz_projekty()
                safe_print("✅ Scénář smazán a pořadí přepočítáno.")


# --- Export s přečíslováním ---
def exportuj_excel():
    EXPORTS_DIR.mkdir(exist_ok=True)
    safe_name = AKTUALNI_PROJEKT.replace(" ", "_")
    output_path = EXPORTS_DIR / f"testcases_{safe_name}.xlsx"
    subject = projekty_data[AKTUALNI_PROJEKT].get("subject", "UAT2\\Antosova\\")
    rows = []

    # Přepočítáme pořadí podle skutečného pořadí v seznamu (ne order_no)
    scenarios = projekty_data[AKTUALNI_PROJEKT]["scenarios"]
    for new_order, tc in enumerate(scenarios, start=1):

        veta = tc.get("veta", tc["test_name"])  # Fallback pro starší data
        new_test_name = build_test_name(new_order, veta)
        
        # Debug info
        safe_print(f"Scénář {new_order}: Akce='{tc['akce']}', Počet kroků={len(tc['kroky'])}")
        
        for i, krok in enumerate(tc["kroky"], start=1):
            desc = krok.get("description", "")
            expected = krok.get("expected", "TODO: doplnit očekávání")
            rows.append({
                "_order_no": new_order,
                "Project": AKTUALNI_PROJEKT,
                "System/Application": SYSTEM_APPLICATION,
                "Subject": subject,
                "Description": f"Segment: {tc['segment']}\nKanal: {tc['kanal']}\nAkce: {tc['akce']}",
                "Type": TYPE,
                "Test Phase": TEST_PHASE,
                "Test: Test Phase": TEST_TEST_PHASE,
                "Test Priority": tc["priority"],
                "Test Complexity": tc["complexity"],
                "Test Name": new_test_name,
                "Step Name (Design Steps)": str(i),
                "Description (Design Steps)": desc,
                "Expected (Design Steps)": expected
            })

    if not rows:
        safe_print("⚠️ Žádné scénáře k exportu.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values(by="_order_no").drop(columns=["_order_no"])
    df.to_excel(output_path, index=False)
    safe_print(f"✅ Exportováno do: {output_path}")

    # 🔹 Automatický commit & push na GitHub s rebase ochranou
    try:
        subprocess.run(["git", "add", str(output_path)], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto export {AKTUALNI_PROJEKT}"], check=True)

        # 🧩 Nejprve zkus pull s rebase, aby se vyřešily kolize
        subprocess.run(["git", "pull", "--rebase"], check=True)
        subprocess.run(["git", "push"], check=True)

        safe_print("✅ Soubor úspěšně nahrán do GitHub repozitáře.")
    except subprocess.CalledProcessError as e:
        safe_print(f"⚠️ Git operace selhala: {e}")
        safe_print("ℹ️ Zkus ručně spustit v terminálu: git pull --rebase && git push")
    except Exception as e:
        safe_print(f"⚠️ Nepodařilo se nahrát soubor: {e}")


# --- Menu ---
def menu():
    kroky_data = nacti_kroky()
    while True:
        safe_print(f"\n--- MENU ({AKTUALNI_PROJEKT}) ---")
        safe_print("1. Přepnout projekt")
        safe_print("2. Přidat nový scénář")
        safe_print("3. Zobrazit scénáře")
        safe_print("4. Upravit scénář")
        safe_print("5. Upravit projekt")
        safe_print("6. Smazat scénář")
        safe_print("7. Smazat projekt")
        safe_print("8. Exportovat do Excelu")
        safe_print("9. Debug kroky")
        safe_print("10. Konec")
        volba = input("Zvol možnost: ").strip()

        if volba == "1":
            vyber_projekt()
        elif volba == "2":
            veta = input("Zadej větu: ")
            akce = detect_action(veta, kroky_data)
            if not akce:
                safe_print("Nenalezena akce – vyber ručně:")
                for idx, a in enumerate(kroky_data.keys(), start=1):
                    safe_print(f"{idx}. {a}")
                idx = int(input("Číslo akce: ")) - 1
                akce = list(kroky_data.keys())[idx]
            p = input("Priorita (1=High,2=Medium,3=Low): ")
            c = input("Komplexita (1–5): ")
            tc = generuj_testcase(veta, kroky_data, akce, PRIORITY_MAP.get(p,"2-Medium"), COMPLEXITY_MAP.get(c,"4-Medium"))
            safe_print(f"✅ Vygenerován test: {tc['test_name']}")
        elif volba == "3":
            for tc in projekty_data[AKTUALNI_PROJEKT]["scenarios"]:
                safe_print(f"- {tc['test_name']} ({tc['priority']} | {tc['complexity']})")
        elif volba == "4":
            uprav_scenar()
        elif volba == "5":
            uprav_projekt()
        elif volba == "6":
            smaz_scenar()
        elif volba == "7":
            smaz_projekt()
        elif volba == "8":
            exportuj_excel()
        elif volba == "9":
            debug_kroky()
        elif volba == "10":
            safe_print("👋 Ukončuji program.")
            break
        else:
            safe_print("⚠️ Neplatná volba.")


if __name__ == "__main__":
    safe_print("✅ Program spuštěn, připraven k práci...")
    projekty_data = nacti_projekty()
    
    # Spust debug
    debug_kroky()
    
    vyber_projekt()
    menu()