import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
You are HackAlert AI, an intelligent opportunity-matching assistant. 
Your job is to analyze scraped listings of hackathons, coding contests, technical events, competitions, and internships (both paid and unpaid), and determine if they match the target Student Profile.

Target Student Profile:
{student_profile}

For the given opportunity context, you must output a raw JSON object containing the following keys:
- is_match (boolean): True if this opportunity fits the student profile, False if it is irrelevant or mismatched.
  * You MUST match technical opportunities including: software engineering, web/app development, AI/ML, data science, cybersecurity, tech hackathons, coding contests, hackathons, technical events, competitions, and tech internships (accept both paid and unpaid internships).
  * You MUST filter out sales, banking, HR, finance, content writing, marketing, or general non-technical roles.
- confidence_score (number): A score from 0 to 100 representing your confidence.
- reason (string): A short, single-sentence explanation of why it matches or doesn't match.
- summary (string): A detailed, 3-4 sentence comprehensive description of the opportunity. Explain what the candidate will do or what the event/competition tasks are.
- key_requirements (string): A clear, bullet-pointed list of required skills, prerequisites, or eligibility criteria (e.g. "• Python, React\n• Open to pre-final years"). If none, output "N/A".
- benefits (string): Stipend details (explicitly state "Unpaid" if it is unpaid, or the specific payment/stipend range), prizes, certificates, or perks. If none, output "N/A".
- event_mode (string): The mode of the opportunity, which must be "Online" (for remote/virtual/hybrid) or "Offline (Location)" (if in-person; specify location if known, e.g. "Offline (Mumbai)"). Default to "Online" or "N/A" if unknown.
- title (string): A cleaned-up, human-readable title of the opportunity.
- company (string): Cleaned name of the company or hosting organization.
- deadline (string): The extracted registration deadline date or "N/A" if not found.
- eligibility (string): Eligibility criteria (e.g., "All students", "Pre-final years only") or "Open to all" if not specified.

Do not include any markdown backticks, explanations, or leading/trailing text. Output ONLY valid JSON.
"""

SYSTEM_PROMPT_BATCH = """
You are HackAlert AI, an intelligent opportunity-matching assistant. 
Your job is to analyze a batch of scraped listings of hackathons, coding contests, technical events, competitions, and internships (both paid and unpaid), and determine if each matches the target Student Profile.

Target Student Profile:
{student_profile}

For the given JSON list of opportunities, you must output a raw JSON array of objects. Each object in the array corresponds to one opportunity in the input, preserving its "id", and must contain the following keys:
- id (string): The exact ID of the opportunity from the input.
- is_match (boolean): True if this opportunity fits the student profile, False if it is irrelevant or mismatched.
  * You MUST match technical opportunities including: software engineering, web/app development, AI/ML, data science, cybersecurity, tech hackathons, coding contests, hackathons, technical events, competitions, and tech internships (accept both paid and unpaid internships).
  * You MUST filter out sales, banking, HR, finance, content writing, marketing, or general non-technical roles.
- confidence_score (number): A score from 0 to 100 representing your confidence.
- reason (string): A short, single-sentence explanation of why it matches or doesn't match.
- summary (string): A detailed, 3-4 sentence comprehensive description of the opportunity. Explain what the candidate will do or what the event/competition tasks are.
- key_requirements (string): A clear, bullet-pointed list of required skills, prerequisites, or eligibility criteria (e.g. "• Python, React\n• Open to pre-final years"). If none, output "N/A".
- benefits (string): Stipend details (explicitly state "Unpaid" if it is unpaid, or the specific payment/stipend range), prizes, certificates, or perks. If none, output "N/A".
- event_mode (string): The mode of the opportunity, which must be "Online" (for remote/virtual/hybrid) or "Offline (Location)" (if in-person; specify location if known, e.g. "Offline (Mumbai)"). Default to "Online" or "N/A" if unknown.
- title (string): A cleaned-up, human-readable title of the opportunity.
- company (string): Cleaned name of the company or hosting organization.
- deadline (string): The extracted registration deadline date or "N/A" if not found.
- eligibility (string): Eligibility criteria (e.g., "All students", "Pre-final years only") or "Open to all" if not specified.

CRITICAL: Evaluate each opportunity independently. Do NOT copy, duplicate, or bleed titles, reasons, companies, summaries, or metadata between different opportunities in the batch. Each opportunity in the output JSON array must represent its own unique input context.

Do not include any markdown backticks, explanations, or leading/trailing text. Output ONLY valid JSON array.
"""

def evaluate_opportunities_batch(opportunities):
    """
    Evaluates a batch of scraped opportunities against the student profile using Gemini in a single API call.
    """
    student_profile = os.getenv(
        "STUDENT_PROFILE", 
        "Undergraduate Computer Science student in India interested in software engineering, AI/ML, web development, and competitive programming."
    )
    
    # Return mock negative results if Gemini API Key is not set yet
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        print("[Gemini Filter] Warning: GEMINI_API_KEY is not set. Returning default match=False for batch.")
        return [{
            "id": opp["id"],
            "success": False,
            "is_match": False,
            "confidence_score": 0,
            "reason": "Gemini API Key is not configured.",
            "summary": "N/A",
            "key_requirements": "N/A",
            "benefits": "N/A",
            "event_mode": "Online",
            "title": opp["title"],
            "company": "N/A",
            "deadline": "N/A",
            "eligibility": "N/A"
        } for opp in opportunities]

    batch_input = []
    for opp in opportunities:
        batch_input.append({
            "id": opp["id"],
            "platform": opp["platform"],
            "title": opp["title"],
            "raw_context": opp["raw_context"]
        })
    
    max_retries = 3
    retry_delay = 8.0
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT_BATCH.format(student_profile=student_profile)
            )
            
            prompt = f"""
            Opportunities Batch JSON:
            ---
            {json.dumps(batch_input, indent=2)}
            ---
            Please evaluate all {len(batch_input)} opportunities and output the JSON array response.
            """
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                }
            )
            
            # Parse the JSON response
            results = json.loads(response.text.strip())
            
            # Make sure it's a list
            if not isinstance(results, list):
                raise ValueError("Gemini response is not a JSON list")
                
            # Create a lookup for results
            result_map = {res["id"]: res for res in results if "id" in res}
            
            # Reconstruct full details including success flag
            final_results = []
            for opp in opportunities:
                res = result_map.get(opp["id"])
                if res:
                    res["success"] = True
                    # Set defaults for missing fields to avoid KeyError
                    for field in ["is_match", "confidence_score", "reason", "summary", "key_requirements", "benefits", "event_mode", "title", "company", "deadline", "eligibility"]:
                        if field not in res:
                            if field == "is_match":
                                res[field] = False
                            elif field == "confidence_score":
                                res[field] = 0
                            elif field in ["title", "company"]:
                                res[field] = opp.get(field, "N/A")
                            else:
                                res[field] = "N/A"
                    final_results.append(res)
                else:
                    final_results.append({
                        "id": opp["id"],
                        "success": False,
                        "is_match": False,
                        "confidence_score": 0,
                        "reason": "Item missing from Gemini batch response.",
                        "summary": "N/A",
                        "key_requirements": "N/A",
                        "benefits": "N/A",
                        "event_mode": "Online",
                        "title": opp["title"],
                        "company": "N/A",
                        "deadline": "N/A",
                        "eligibility": "N/A"
                    })
            return final_results
            
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                if attempt < max_retries - 1:
                    print(f"[Gemini Filter] Rate limit (429) hit during batch evaluation. Sleeping {retry_delay}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2.0
                    continue
            
            print(f"[Gemini Filter] Error in batch evaluation: {e}")
            break
            
    # Return failure array on complete failure
    return [{
        "id": opp["id"],
        "success": False,
        "is_match": False,
        "confidence_score": 0,
        "reason": f"Failed batch evaluation.",
        "summary": "N/A",
        "key_requirements": "N/A",
        "benefits": "N/A",
        "event_mode": "Online",
        "title": opp["title"],
        "company": "N/A",
        "deadline": "N/A",
        "eligibility": "N/A"
    } for opp in opportunities]

def evaluate_opportunity(platform, title, raw_context):
    """
    Evaluates a scraped opportunity against the student profile using Gemini.
    """
    student_profile = os.getenv(
        "STUDENT_PROFILE", 
        "Undergraduate Computer Science student in India interested in software engineering, AI/ML, web development, and competitive programming."
    )
    
    # Return mock negative result if Gemini API Key is not set yet
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        print("[Gemini Filter] Warning: GEMINI_API_KEY is not set. Returning default match=False.")
        return {
            "success": False,
            "is_match": False,
            "confidence_score": 0,
            "reason": "Gemini API Key is not configured.",
            "summary": "N/A",
            "key_requirements": "N/A",
            "benefits": "N/A",
            "event_mode": "Online",
            "title": title,
            "company": "N/A",
            "deadline": "N/A",
            "eligibility": "N/A"
        }

    max_retries = 3
    retry_delay = 8.0  # seconds (since rate limit is 5 RPM, a sleep of 8-15s helps bypass it)
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT.format(student_profile=student_profile)
            )
            
            prompt = f"""
            Opportunity Source Platform: {platform}
            Opportunity Scraped Title: {title}
            Scraped Raw Content/Context:
            ---
            {raw_context}
            ---
            Please evaluate and output the JSON response.
            """
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                }
            )
            
            # Parse the JSON response
            result = json.loads(response.text.strip())
            result["success"] = True
            return result
            
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                if attempt < max_retries - 1:
                    print(f"[Gemini Filter] Rate limit (429) hit for '{title}'. Sleeping {retry_delay}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2.0  # increase backoff delay
                    continue
            
            print(f"[Gemini Filter] Error evaluating opportunity '{title}': {e}")
            break

    # Return standard negative state on failure
    return {
        "success": False,
        "is_match": False,
        "confidence_score": 0,
        "reason": "Failed to evaluate due to persistent API rate limits.",
        "summary": "N/A",
        "key_requirements": "N/A",
        "benefits": "N/A",
        "event_mode": "Online",
        "title": title,
        "company": "N/A",
        "deadline": "N/A",
        "eligibility": "N/A"
    }

if __name__ == "__main__":
    # Local quick test
    print("Running Gemini AI evaluation test...")
    sample_context = "Title: HackGenome | Starts: 2026-06-12T03:30:00.000Z | Ends: 2026-06-14T03:30:00.000Z | Required Skills: Bioinformatics, Python, Machine Learning"
    res = evaluate_opportunity("Devfolio", "HackGenome", sample_context)
    print(json.dumps(res, indent=2))
