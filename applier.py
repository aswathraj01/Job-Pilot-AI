"""
applier.py  —  Automated job application via Playwright
Supports: LinkedIn Easy Apply, Indeed Apply
"""
import time
import random
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from fpdf import FPDF

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _sleep(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))


# ── Resume PDF builder ────────────────────────────────────────────────────────

def build_resume_pdf(text: str, output_path: str) -> str:
    """Convert plain-text resume to a clean PDF. Returns path."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    for line in text.splitlines():
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        # Detect section headers (ALL CAPS or ends with colon)
        if line.isupper() or (line.endswith(":") and len(line) < 40):
            pdf.ln(2)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 6, line, ln=True)
            pdf.set_font("Helvetica", size=10)
        else:
            pdf.multi_cell(0, 5, line)

    pdf.output(output_path)
    return output_path


# ── LinkedIn Easy Apply ───────────────────────────────────────────────────────

def apply_linkedin(job: dict, resume_path: str, cover_letter: str, config: dict) -> bool:
    """Apply via LinkedIn Easy Apply. Returns True on success."""
    cfg = config.get("linkedin", {})
    email    = cfg.get("email", "")
    password = cfg.get("password", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        try:
            # Login
            page.goto("https://www.linkedin.com/login", timeout=30000)
            _sleep(1, 2)
            page.fill("#username", email)
            page.fill("#password", password)
            page.click("[data-litms-control-urn='login-submit']")
            page.wait_for_load_state("networkidle", timeout=15000)
            _sleep(2, 3)

            # Navigate to job
            page.goto(job["url"], timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            _sleep(2, 3)

            # Click Easy Apply
            easy_btn = page.query_selector(".jobs-apply-button--top-card button, .jobs-s-apply button")
            if not easy_btn:
                logger.warning(f"No Easy Apply button for {job['url']}")
                return False

            btn_text = easy_btn.inner_text().lower()
            if "easy apply" not in btn_text:
                logger.info(f"Not Easy Apply for {job['title']} — skipping auto-apply")
                return False

            easy_btn.click()
            _sleep(2, 3)

            # Walk through multi-step form (up to 10 pages)
            for step in range(10):
                _sleep(1, 2)

                # Upload resume if prompted
                upload = page.query_selector("input[type='file']")
                if upload and Path(resume_path).exists():
                    upload.set_input_files(resume_path)
                    _sleep(1, 2)

                # Cover letter textarea
                cover_area = page.query_selector("textarea[name*='cover'], textarea[id*='cover']")
                if cover_area and cover_letter:
                    cover_area.fill(cover_letter[:2000])
                    _sleep(0.5, 1)

                # Handle text input questions (phone, years of experience, etc.)
                text_inputs = page.query_selector_all("input[type='text']:visible, input[type='tel']:visible")
                for inp in text_inputs:
                    try:
                        label = ""
                        label_id = inp.get_attribute("id")
                        if label_id:
                            lbl = page.query_selector(f"label[for='{label_id}']")
                            if lbl:
                                label = lbl.inner_text().lower()
                        if inp.input_value():
                            continue  # already filled
                        if "phone" in label or "mobile" in label:
                            # leave blank — user should pre-fill in LinkedIn profile
                            pass
                        elif "year" in label and "experience" in label:
                            inp.fill("3")
                        elif "salary" in label:
                            inp.fill("0")
                    except Exception:
                        pass

                # Handle dropdowns (Yes/No questions)
                selects = page.query_selector_all("select:visible")
                for sel in selects:
                    try:
                        opts = sel.query_selector_all("option")
                        labels = [o.inner_text().strip().lower() for o in opts]
                        if "yes" in labels:
                            sel.select_option(label="Yes")
                    except Exception:
                        pass

                # Check for Next / Review / Submit buttons
                next_btn = page.query_selector("button[aria-label='Continue to next step']")
                review_btn = page.query_selector("button[aria-label='Review your application']")
                submit_btn = page.query_selector("button[aria-label='Submit application']")

                if submit_btn:
                    submit_btn.click()
                    _sleep(2, 3)
                    logger.success(f"Applied: {job['title']} @ {job['company']} (LinkedIn)")
                    # Close success modal if any
                    dismiss = page.query_selector("button[aria-label='Dismiss']")
                    if dismiss:
                        dismiss.click()
                    browser.close()
                    return True
                elif review_btn:
                    review_btn.click()
                elif next_btn:
                    next_btn.click()
                else:
                    logger.warning(f"LinkedIn apply stuck at step {step}")
                    break

        except PWTimeout:
            logger.error(f"LinkedIn apply timed out: {job['url']}")
        except Exception as e:
            logger.error(f"LinkedIn apply error: {e}")
        finally:
            browser.close()

    return False


# ── Indeed Easy Apply ─────────────────────────────────────────────────────────

def apply_indeed(job: dict, resume_path: str, cover_letter: str, config: dict) -> bool:
    """Apply via Indeed Quick Apply. Returns True on success."""
    cfg = config.get("indeed", {})
    email    = cfg.get("email", "")
    password = cfg.get("password", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        try:
            # Login to Indeed
            page.goto("https://secure.indeed.com/auth", timeout=30000)
            _sleep(1, 2)
            email_btn = page.query_selector("button[data-tn-element='auth-page-google-sign-in-link']")
            # Use email login
            email_input = page.query_selector("input[type='email'], input[name='__email']")
            if email_input:
                email_input.fill(email)
                page.click("button[type='submit'], #signin-button")
                _sleep(1, 2)
                pw_input = page.query_selector("input[type='password'], input[name='__password']")
                if pw_input:
                    pw_input.fill(password)
                    page.click("button[type='submit'], #signin-button")
                    page.wait_for_load_state("networkidle", timeout=15000)
                    _sleep(2, 3)

            # Go to job page
            page.goto(job["url"], timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            _sleep(2, 3)

            apply_btn = page.query_selector("[id*='indeedApplyButton'], .ia-IndeedApplyButton")
            if not apply_btn:
                logger.info(f"No Indeed Quick Apply for {job['title']}")
                return False

            apply_btn.click()
            _sleep(2, 4)

            # Walk multi-step form
            for step in range(8):
                _sleep(1, 2)

                upload = page.query_selector("input[type='file']")
                if upload and Path(resume_path).exists():
                    upload.set_input_files(resume_path)
                    _sleep(1, 2)

                cover_area = page.query_selector("textarea")
                if cover_area and cover_letter and not cover_area.input_value():
                    cover_area.fill(cover_letter[:2000])
                    _sleep(0.5, 1)

                # Continue / Submit
                submit_btn = page.query_selector("button[data-tn-element='submit-cv-button']")
                continue_btn = page.query_selector("button[data-tn-element='continueButton']")

                if submit_btn:
                    submit_btn.click()
                    _sleep(2, 3)
                    logger.success(f"Applied: {job['title']} @ {job['company']} (Indeed)")
                    browser.close()
                    return True
                elif continue_btn:
                    continue_btn.click()
                else:
                    logger.warning(f"Indeed apply stuck at step {step}")
                    break

        except Exception as e:
            logger.error(f"Indeed apply error: {e}")
        finally:
            browser.close()

    return False


# ── Dispatcher ────────────────────────────────────────────────────────────────

def apply_to_job(job: dict, resume_path: str, cover_letter: str, config: dict) -> bool:
    source = job.get("source", "")
    if source == "linkedin":
        return apply_linkedin(job, resume_path, cover_letter, config)
    elif source == "indeed":
        return apply_indeed(job, resume_path, cover_letter, config)
    else:
        # For other sources, log for manual review
        logger.info(f"Manual apply needed: {job['title']} @ {job['url']}")
        return False
