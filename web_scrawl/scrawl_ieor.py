import re
import time
import urllib.parse
import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://doc.sis.columbia.edu/sel/IEOR_Spring2026.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get(URL, headers=headers)
response.encoding = "utf-8"

with open(f"web_scrawl/raw.html", "w", encoding="utf-8") as f:
    f.write(response.text)





# ── SETTINGS ──────────────────────────────────────────────
HTML_FILE   = "raw.html"          
BASE_URL    = "https://doc.sis.columbia.edu/sel/IEOR_Spring2026.html"
OUTPUT_CSV  = "web_scrawl/IEOR_Spring2026_ieor.csv"
DELAY       = 0.5                  # wait time between requests to avoid overwhelming the server
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# extra fields to fetch from section detail page
EXTRA_FIELDS = [
    "Type",
    "Method of Instruction",
    "Course Description",
    "Number",
    "Section",
    "Division",
    "Open To",
    "Section key",
]
# ─────────────────────────────────────────────────────


def parse_main_page(html_file):
    """analyze the main page HTML, extract course and section info, return a list of dicts"""
    with open(html_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    courses = []
    current_course_name = None

    for row in soup.select("table.course-listing tr"):
        th = row.find("th")
        if th:
            current_course_name = th.get_text(separator=" ", strip=True)
            continue

        dl = row.find("dl")
        if not dl:
            continue

        # section 
        section_tag = row.find("a")
        section_href = section_tag["href"] if section_tag else ""
        section_text = section_tag.get_text(strip=True) if section_tag else ""
        section_url  = urllib.parse.urljoin(BASE_URL, section_href) if section_href else ""

        h1 = dl.find("h1")
        short_name = h1.get_text(strip=True) if h1 else ""

        fields = {}
        for dt in dl.find_all("dt"):
            key = dt.get_text(strip=True).rstrip(":")
            dd  = dt.find_next_sibling("dd")
            val = dd.get_text(strip=True) if dd else ""
            fields[key] = fields[key] + " | " + val if key in fields else val

        courses.append({
            "Course Name": current_course_name,
            "Short Name":  short_name,
            "Section":     section_text,
            "Section URL": section_url,
            "Call Number": fields.get("Call Number", ""),
            "Points":      fields.get("Points", ""),
            "Day/Time":    fields.get("Day/Time", ""),
            "Location":    fields.get("Location", ""),
            "Enrollment":  fields.get("Enrollment", ""),
            "Notes":       fields.get("Notes", ""),
            "Instructor":  fields.get("Instructor", ""),
        })

    return courses


def fetch_section_detail(url):
    """extract extra fields from section detail page, return a dict with keys in EXTRA_FIELDS"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        detail = {}
        for row in soup.select("table.section tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            key = th.get_text(separator=" ", strip=True)
            val = td.get_text(separator=" ", strip=True)
            detail[key] = val

        return {field: detail.get(field, "") for field in EXTRA_FIELDS}

    except Exception as e:
        print(f" execution fail {url}: {e}")
        return {field: "" for field in EXTRA_FIELDS}


def main():
    print("── Step 1: Analyze the main page ──")
    courses = parse_main_page(HTML_FILE)
    print(f"find total {len(courses)}  section info")

    print("\n── Step 2: Fetch the section detail pages one by one ──")
    for i, course in enumerate(courses):
        url = course.get("Section URL", "")
        if not url:
            for field in EXTRA_FIELDS:
                course[field] = ""
            continue

        print(f"[{i+1}/{len(courses)}] {url}")
        extra = fetch_section_detail(url)
        course.update(extra)
        time.sleep(DELAY)

    print("\n── Step 3: Save CSV ──")
    cols = [
        "Course Name", "Short Name", "Section", "Section URL",
        "Call Number", "Points", "Day/Time", "Location",
        "Enrollment", "Notes", "Instructor",
        "Type", "Method of Instruction", "Course Description",
        "Number", "Division", "Open To", "Section key",
    ]
    df = pd.DataFrame(courses)[cols]
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} info to {OUTPUT_CSV}")
    print(df[["Course Name", "Type", "Method of Instruction", "Section key"]].head(5).to_string())


if __name__ == "__main__":
    main()