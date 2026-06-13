import requests
from bs4 import BeautifulSoup
import time
from playwright.sync_api import sync_playwright
import concurrent.futures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

def scrape_devfolio():
    """Scrapes open hackathons from Devfolio API."""
    url = "https://api.devfolio.co/api/hackathons"
    params = {"filter": "application_open", "page": 1}
    opportunities = []
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("result", [])
            for item in results:
                name = item.get("name")
                slug = item.get("slug")
                # Construct SEO URL
                link = f"https://{slug}.devfolio.co/" if slug else item.get("seo_url")
                if not link:
                    link = f"https://devfolio.co/hackathons/{slug}"
                
                opportunities.append({
                    "platform": "Devfolio",
                    "id": f"devfolio-{item.get('id')}",
                    "title": name,
                    "link": link,
                    "raw_context": f"Title: {name} | Starts: {item.get('starts_at')} | Ends: {item.get('ends_at')} | Registrations: {item.get('submissions_count', 'N/A')}"
                })
        else:
            print(f"Devfolio scraper returned status code: {response.status_code}")
    except Exception as e:
        print(f"Error scraping Devfolio: {e}")
    return opportunities

def scrape_unstop():
    """Scrapes open hackathons from Unstop search API."""
    url = "https://unstop.com/api/public/opportunity/search-result"
    params = {"opportunity": "hackathons", "page": 1, "oppstatus": "open"}
    opportunities = []
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            opps = data.get("data", {}).get("data", [])
            for opp in opps:
                title = opp.get("title")
                opp_id = opp.get("id")
                seo_url = opp.get("seo_url")
                if not seo_url:
                    seo_url = f"https://unstop.com/{opp.get('public_url')}"
                
                company = opp.get("organisation", {}).get("name")
                end_date = opp.get("end_date")
                skills = ", ".join([sk.get("skill") for sk in opp.get("required_skills", []) if sk.get("skill")])
                
                opportunities.append({
                    "platform": "Unstop",
                    "id": f"unstop-{opp_id}",
                    "title": title,
                    "link": seo_url,
                    "raw_context": f"Title: {title} | Host: {company} | Deadline: {end_date} | Required Skills: {skills} | Registrations: {opp.get('registerCount', 'N/A')}"
                })
        else:
            print(f"Unstop scraper returned status code: {response.status_code}")
    except Exception as e:
        print(f"Error scraping Unstop: {e}")
    return opportunities

def scrape_internshala():
    """Scrapes internships from Internshala matching general lists."""
    url = "https://internshala.com/internships"
    opportunities = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="individual_internship")
            for card in cards:
                title_el = card.select_one(".job-title-href")
                if not title_el:
                    continue
                
                title = title_el.text.strip()
                href = "https://internshala.com" + title_el["href"]
                
                company_el = card.select_one(".company-name")
                company = company_el.text.strip() if company_el else "N/A"
                
                location_el = card.select_one(".locations span")
                location = location_el.text.strip() if location_el else "N/A"
                
                stipend_el = card.select_one(".stipend")
                stipend = stipend_el.text.strip().replace("\u20b9", "Rs. ") if stipend_el else "N/A"
                
                skills = ", ".join([sk.text.strip() for sk in card.select(".job_skills .job_skill")])
                details = card.select_one(".about_job .text")
                details_text = details.text.strip() if details else ""
                
                opp_id = card.get("internshipid") or card.get("id") or href.split("-")[-1]
                
                opportunities.append({
                    "platform": "Internshala",
                    "id": f"internshala-{opp_id}",
                    "title": title,
                    "link": href,
                    "raw_context": f"Title: {title} | Company: {company} | Location: {location} | Stipend: {stipend} | Required Skills: {skills} | Details: {details_text}"
                })
        else:
            print(f"Internshala scraper returned status code: {response.status_code}")
    except Exception as e:
        print(f"Error scraping Internshala: {e}")
    return opportunities

def scrape_hackerearth():
    """Scrapes contests from HackerEarth using Playwright for dynamic rendering."""
    opportunities = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Guide Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Optimize request overhead by blocking unneeded resources
            def block_heavy_resources(route):
                if route.request.resource_type in ["image", "stylesheet", "font", "media", "websocket", "manifest"]:
                    route.abort()
                else:
                    route.continue_()
            
            page.route("**/*", block_heavy_resources)
            
            # Lower timeout to 15 seconds to fail fast on network block/hang
            page.goto("https://www.hackerearth.com/challenges/", timeout=15000)
            
            # Wait a few seconds for dynamic contents to render
            time.sleep(5)
            
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all anchor tags that contain an h3 (representing challenge cards)
            for a in soup.find_all("a", href=True):
                h3 = a.find("h3")
                if h3:
                    title = h3.text.strip()
                    if "HOST YOUR OWN" in title.upper() or "HIRING RADAR" in title.upper():
                        continue
                        
                    href = a["href"]
                    if href.startswith("/"):
                        href = "https://www.hackerearth.com" + href
                        
                    # Clean up context string
                    card_text = a.text.strip().replace('\n', '  ')
                    
                    # Extract ID from the url slug
                    opp_id = href.rstrip("/").split("/")[-1]
                    
                    opportunities.append({
                        "platform": "HackerEarth",
                        "id": f"hackerearth-{opp_id}",
                        "title": title,
                        "link": href,
                        "raw_context": f"Title: {title} | Context: {card_text}"
                    })
    except Exception as e:
        print(f"Error scraping HackerEarth: {e}")
    return opportunities

def scrape_all():
    """Aggregates opportunities from all platforms concurrently."""
    scrapers = [
        ("Devfolio", scrape_devfolio),
        ("Unstop", scrape_unstop),
        ("Internshala", scrape_internshala),
        ("HackerEarth", scrape_hackerearth)
    ]
    
    all_opps = []
    print(f"Starting concurrent scrapers for: {[name for name, _ in scrapers]}...")
    
    # Run scrapers concurrently using a ThreadPoolExecutor
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        future_to_platform = {executor.submit(func): name for name, func in scrapers}
        
        for future in concurrent.futures.as_completed(future_to_platform):
            platform_name = future_to_platform[future]
            try:
                data = future.result()
                print(f"Fetched {len(data)} items from {platform_name}.")
                all_opps.extend(data)
            except Exception as e:
                print(f"Error executing scraper for {platform_name}: {e}")
                
    elapsed = time.time() - start_time
    print(f"Total opportunities fetched: {len(all_opps)} (Scraping took {elapsed:.2f}s)")
    return all_opps

if __name__ == "__main__":
    opps = scrape_all()
    for o in opps[:5]:
        print(f"\n- Platform: {o['platform']}\n  Title: {o['title']}\n  Link: {o['link']}\n  Context: {o['raw_context'][:150]}...")
