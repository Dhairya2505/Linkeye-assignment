from playwright.sync_api import sync_playwright
import time
import hashlib
import json

URL = "https://api.freshservice.com/"
CONTENT_SELECTOR = ".api-content-main"

documents = []
seen_hashes = set()
with open("documents.json", "w", encoding="utf-8") as f:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle")

        sections = page.evaluate("""
    () => Array.from(document.querySelectorAll('div.scroll-spy'))
    .map(el => ({
        id: el.id,
        parent_id: el.parentElement ? el.parentElement.id : null
    }))
    .filter(obj => obj.id)
    """)
        

        print(f"Found {len(sections)} anchors")

        for sec in sections:
            sid = sec["id"]
            parent_id = sec["parent_id"]

            page.evaluate(
                "id => document.getElementById(id).scrollIntoView({block:'start'})",
                sid
            )

            time.sleep(0.8)

            content = page.evaluate(f"""
            () => {{
                const el = document.querySelector('{CONTENT_SELECTOR}');
                return el ? el.innerText.trim() : '';
            }}
            """)

            if not content:
                continue
            
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in seen_hashes:
                continue

            seen_hashes.add(content_hash)
            documents.append({
                "page_content":content,
                "source": URL,
                "anchor_id": sid,
                "parent_id": parent_id
            })
            print(f"{parent_id}  -  {sid}")

        browser.close()

    json.dump(documents, f, ensure_ascii=False, indent=2)