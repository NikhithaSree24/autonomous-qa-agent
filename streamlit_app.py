# streamlit_app.py
import streamlit as st
import requests, json, io
from pathlib import Path

# Safe secrets fallback
try:
    API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")
except Exception:
    API_BASE = "http://localhost:8000"

st.title("Autonomous QA Agent — Test Case + Selenium Generator")

# ------------------------------------------------------
# 1) UPLOAD DOCUMENTS
# ------------------------------------------------------
st.sidebar.header("1) Upload assets")
uploaded_files = st.sidebar.file_uploader(
    "Upload support docs / checkout.html",
    accept_multiple_files=True,
    type=['md', 'txt', 'json', 'html', 'pdf']
)

if uploaded_files:
    files = []
    for f in uploaded_files:
        files.append(("files", (f.name, f.getvalue(), f.type or "application/octet-stream")))

    try:
        res = requests.post(f"{API_BASE}/upload/", files=files, timeout=120)
        try:
            payload = res.json()
            st.success(f"Uploaded: {payload.get('saved')}")
        except ValueError:
            st.warning(f"Upload returned non-JSON response.\nStatus: {res.status_code}\nResponse:\n{res.text}")
    except Exception as e:
        st.error(f"Upload request failed: {e}")

# ------------------------------------------------------
# 2) BUILD KNOWLEDGE BASE
# ------------------------------------------------------
if st.sidebar.button("Build Knowledge Base"):
    try:
        res = requests.post(f"{API_BASE}/build_kb/", timeout=180)
        try:
            payload = res.json()
            st.info(f"Build KB result: {payload}")
        except ValueError:
            st.warning(f"Build KB returned non-JSON.\nStatus: {res.status_code}\nResponse:\n{res.text}")
    except Exception as e:
        st.error(f"Build KB request failed: {e}")

# ------------------------------------------------------
# 3) GENERATE TEST CASES
# ------------------------------------------------------
st.header("2) Generate Test Cases")
query = st.text_area(
    "Agent prompt:",
    "Generate positive and negative test cases for discount code SAVE15."
)

if st.button("Generate Test Cases"):
    try:
        res = requests.post(f"{API_BASE}/generate_testcases/", data={"query": query}, timeout=180)
        try:
            # Accept both structured {"testcases": [...] } or {"testcases": {"raw": "..."}} shapes
            resp_json = res.json()
            tcs = resp_json.get("testcases")
            st.session_state['testcases'] = tcs
            st.subheader("Generated Test Cases")
            st.json(tcs)
        except ValueError:
            st.error(f"Testcase generation returned non-JSON:\n{res.text}")
    except Exception as e:
        st.error(f"Testcase request failed: {e}")

# ------------------------------------------------------
# 4) GENERATE SELENIUM SCRIPT (robust)
# ------------------------------------------------------
if 'testcases' in st.session_state:
    st.header("3) Select a Test Case and Generate Selenium Script")

    tcs = st.session_state['testcases']

    # Normalize and handle 'raw' responses
    parsed_list = None

    # If agent returned a dict with 'raw' key (string), try to extract JSON array
    if isinstance(tcs, dict) and 'raw' in tcs:
        raw = tcs['raw']
        st.warning("Agent returned raw text. Attempting to extract a JSON array from the raw output...")
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    parsed_list = parsed
                    st.success("Extracted JSON array from raw output.")
                else:
                    st.error("Found JSON but it is not an array.")
            except Exception as e:
                st.error(f"Failed to parse JSON from raw output: {e}")
                st.code(candidate[:2000])
        else:
            st.error("No JSON array found inside the raw output.")
            st.code(raw[:2000])

    # If agent returned a plain string (not dict), try same extraction
    elif isinstance(tcs, str):
        raw = tcs
        st.warning("Agent returned raw string. Attempting to extract a JSON array from the raw output...")
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    parsed_list = parsed
                    st.success("Extracted JSON array from raw output.")
                else:
                    st.error("Found JSON but it is not an array.")
            except Exception as e:
                st.error(f"Failed to parse JSON from raw output: {e}")
                st.code(candidate[:2000])
        else:
            st.error("No JSON array found inside the raw output.")
            st.code(raw[:2000])

    # If tcs is already a list, use it
    elif isinstance(tcs, list):
        parsed_list = tcs

    # If parsing succeeded, replace tcs with parsed list
    if parsed_list is not None:
        tcs = parsed_list
        st.session_state['testcases'] = tcs

    # Now tcs should be a list (or not)
    if not isinstance(tcs, list) or len(tcs) == 0:
        st.info("No structured test cases available to select. If the agent returned raw text, inspect it above.")
    else:
        # Build safe options list for selectbox
        options = list(range(len(tcs)))
        selection = st.selectbox(
            "Choose test case",
            options=options,
            format_func=lambda i: f"{tcs[i].get('Test_ID','TC-?')} - {tcs[i].get('Feature','(no feature)')}"
        )

        st.write("Selected Test Case:")
        st.json(tcs[selection])

        html_file = st.file_uploader("Upload checkout.html again", type=['html','htm'])
        if st.button("Generate Selenium Script"):
            if html_file is None:
                st.error("Please upload checkout.html")
            else:
                files = {"html_file": (html_file.name, html_file.getvalue(), "text/html")}
                data = {"test_case": json.dumps(tcs[selection])}

                try:
                    res = requests.post(f"{API_BASE}/generate_selenium/", data=data, files=files, timeout=180)
                    try:
                        script = res.json().get("script")
                        st.subheader("Generated Selenium Script")
                        st.code(script, language="python")
                        st.download_button(
                            "Download script",
                            script,
                            file_name=f"{tcs[selection].get('Test_ID','tc')}_selenium.py"
                        )
                    except ValueError:
                        st.error(f"Selenium generation returned non-JSON:\n{res.text}")
                except Exception as e:
                    st.error(f"Selenium script request failed: {e}")
