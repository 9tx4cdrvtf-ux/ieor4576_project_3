import requests
import pandas as pd
import time
from bs4 import BeautifulSoup

# ── SETTINGS ──────────────────────────────────────────────
TERM     = "20261"          # Spring 2026
BASE_URL = "https://doc.sis.columbia.edu/subj"
DELAY    = 0.3              # time interval between requests to avoid overwhelming the server
HEADERS  = {"User-Agent": "Mozilla/5.0"}
MAX_SECTIONS = 25           # the maximum number of sections to try for each course

# ── TOOLS ──────────────────────────────────────────

def parse_course_code(code):
    """
    Split the course code into (dept, suffix).
    Examples:

    * ACCTB8008 → ('ACCT', 'B8008')
    * COMSW4111 → ('COMS', 'W4111')
    * IEORE4000 → ('IEOR', 'E4000')
    * STATS4206 → ('STAT', 'S4206') ← note the special case

    Rule: the first four letters form the **dept**, and the remaining part is the suffix.
    """
    # find the first digit in the code
    for i, c in enumerate(code):
        if c.isdigit():
            letters = code[:i]
            dept    = letters[:4]
            suffix  = letters[4:] + code[i:]
            return dept, suffix
    return code[:4], code[4:]


def fetch_section(dept, suffix, section_num):
    """fetch the section detail page, return a dict with all fields (including extra fields)"""
    section_str = f"{section_num:03d}"
    url = f"{BASE_URL}/{dept}/{suffix}-{TERM}-{section_str}/"
    
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        print(f"  ⚠ {url} → {r.status_code}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # section-header
    h2 = soup.select_one("div#section-header h2")
    h1 = soup.select_one("div#section-header h1")
    h3 = soup.select_one("div#section-header h3")

    # table.section 
    info = {}
    for row in soup.select("table.section tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            key = th.get_text(separator=" ", strip=True)
            val = td.get_text(separator=" ", strip=True)
            info[key] = val

    # Day/Time & Location 
    daytime_raw = info.get("Day & Time Location", "")

    return {
        "Course Name":           h2.get_text(strip=True) if h2 else "",
        "Short Name":            h1.get_text(strip=True) if h1 else "",
        "Short Name Alt":        h3.get_text(strip=True) if h3 else "",
        "Section":               section_str,
        "Section URL":           url,
        "Call Number":           info.get("Call Number", ""),
        "Points":                info.get("Points", ""),
        "Day/Time":              daytime_raw,
        "Location":              "",          
        "Enrollment":            info.get("Enrollment", ""),
        "Notes":                 info.get("Notes", ""),
        "Instructor":            info.get("Instructor", ""),
        "Type":                  info.get("Type", ""),
        "Method of Instruction": info.get("Method of Instruction", ""),
        "Course Description":    info.get("Course Description", ""),
        "Number":                info.get("Number", ""),
        "Division":              info.get("Division", ""),
        "Open To":               info.get("Open To", ""),
        "Section key":           info.get("Section key", ""),
    }


def scrape_course(course_code):
    """fecth all sections of a course, return a list of dicts with all fields (including extra fields)"""
    dept, suffix = parse_course_code(course_code)
    results = []

    for n in range(1, MAX_SECTIONS + 1):
        data = fetch_section(dept, suffix, n)
        if data is None:
            # stop at the first 404
            break
        data["Course Code"] = course_code
        results.append(data)
        time.sleep(DELAY)

    return results


def process_df(df, label=""):
    """enumerate the unique course codes in the dataframe, scrape each course, and return a new dataframe with all section info"""
    codes = df["Course Code"].dropna().unique()
    all_records = []

    for i, code in enumerate(codes):
        print(f"[{i+1}/{len(codes)}] {code}", end=" → ")
        records = scrape_course(code)
        print(f"{len(records)} sections")
        all_records.extend(records)

    result_df = pd.DataFrame(all_records)

    cols = [
        "Course Code", "Course Name", "Short Name", "Short Name Alt",
        "Section", "Section URL",
        "Call Number", "Points", "Day/Time", "Location",
        "Enrollment", "Notes", "Instructor",
        "Type", "Method of Instruction", "Course Description",
        "Number", "Division", "Open To", "Section key",
    ]
    cols = [c for c in cols if c in result_df.columns]
    result_df = result_df[cols]

    return result_df


# ── main ──────────────────────────────────────────
if __name__ == "__main__":
    courses_non_ieor = pd.read_excel("web_scrawl/non_ieor_cbs_approval/courses_electives_non_ieor.xlsx")
    courses_cbs      = pd.read_excel("web_scrawl/non_ieor_cbs_approval/CBS_electives_CBS.xlsx")

    print("═══ non-IEOR ═══")
    df_non_ieor = process_df(courses_non_ieor, "non_ieor")
    df_non_ieor.to_csv("web_scrawl/non_ieor_sections.csv", index=False, encoding="utf-8-sig")
    print(f"non-IEOR finish, total {len(df_non_ieor)} section info\n")

    print("═══ CBS ═══")
    df_cbs = process_df(courses_cbs, "cbs")
    df_cbs.to_csv("web_scrawl/ cbs_sections.csv", index=False, encoding="utf-8-sig")
    print(f"CBS finish, total {len(df_cbs)} section info")