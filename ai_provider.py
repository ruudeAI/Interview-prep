"""
ai_provider.py
==============
Module to handle integrations with AI providers:
- Google Gemini API (with Search Grounding)
- Local OpenAI-compatible LLM endpoints (Ollama/Odysseus)
Includes robust retries, structured JSON formatting, and fallback configurations.
"""

import time
import re
import textwrap
import json
import urllib.request
import urllib.error

from google.genai import types
from utils import parse_qa_json

MAX_RETRIES = 5
BASE_BACKOFF = 15  # seconds

def _gemini_call_with_retry(client, model, contents, config, label="Gemini API Call"):
    """Wrap a Gemini generate_content call with retry + exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            is_retryable = any(code in err_str for code in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"))

            if not is_retryable or attempt == MAX_RETRIES:
                raise

            delay_match = re.search(r'retry\s+in\s+([\d.]+)s', err_str, re.IGNORECASE)
            if delay_match:
                wait = float(delay_match.group(1)) + 2
            else:
                wait = BASE_BACKOFF * (2 ** (attempt - 1))

            print(f"  [Rate Limit] {label}: (attempt {attempt}/{MAX_RETRIES}). "
                  f"Waiting {wait:.0f}s …")
            time.sleep(wait)
    raise RuntimeError(f"Gemini API call failed after {MAX_RETRIES} attempts.")

def _local_call(endpoint, model, prompt):
    """Call a local OpenAI-compatible API endpoint (like Ollama or Odysseus)."""
    endpoint = endpoint.rstrip("/")
    url = f"{endpoint}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        print(f"  [Local LLM] Sending request to local LLM ({model}) at {url} ...")
        with urllib.request.urlopen(req, timeout=300) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        raise ConnectionError(f"Failed to communicate with local LLM server at {url}. "
                              f"Ensure Ollama/Odysseus is running and healthy. Error: {e}")

def fetch_interview_questions(client, company, role):
    """Use Gemini with Google Search grounding to find real-world interview questions."""
    if not client:
        raise ValueError("Gemini client is required for search grounding.")
        
    prompt = textwrap.dedent(f"""\
        Search for the most common and recent interview questions asked at
        **{company}** for the role of **{role}**.

        Find 15–20 specific interview questions including:
        • Technical / domain-specific questions
        • Behavioral / situational questions (STAR format)
        • Company-specific questions unique to {company}
        • Common screening questions for this role

        Return the list of questions formatted clearly, prefixing each with its category
        in square brackets. Example:
        [Technical] What is the difference between IDS and IPS?
        [Behavioral] Describe a time you handled a critical incident under pressure.
    """)

    print(f"  [Search] Sourcing {company} interview questions using Google Search ...")
    return _gemini_call_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        ),
        label=f"Search ({company})",
    )

def generate_tailored_answers(client, company, role, questions_text, resume_text, ruc_text, 
                              candidate_name="Candidate", provider="gemini", 
                              local_endpoint=None, local_model=None):
    """Generate tailored answers matching candidate experience to questions, returning a parsed JSON list."""
    ruc_excerpt = ruc_text[:12000] if ruc_text else ""
    
    prompt = textwrap.dedent(f"""\
        You are an elite career coach preparing a professional for an interview.
        Target Company: {company}
        Target Role: {role}
        Candidate Name: {candidate_name}

        ─── CANDIDATE RESUME ───
        {resume_text}

        ─── CANDIDATE BACKGROUND (RUC) ───
        {ruc_excerpt}

        ─── INTERVIEW QUESTIONS ───
        {questions_text}

        ═══════════════════════════════════════════════════════════════
        INSTRUCTIONS
        ═══════════════════════════════════════════════════════════════
        Produce a detailed, tailored answer for EVERY interview question listed above.
        1. Directly reference the candidate's actual experience, tools, and achievements from the resume/RUC.
        2. Use the STAR format (Situation, Task, Action, Result) for behavioral and situational questions.
        3. Do not invent details; only mention things the candidate has actually done.
        4. For technical questions, provide detailed answers (3-6 sentences).
        5. For behavioral questions, output the full STAR narrative.

        ═══════════════════════════════════════════════════════════════
        OUTPUT FORMAT
        ═══════════════════════════════════════════════════════════════
        You MUST respond ONLY with a JSON array of objects.
        Do not include markdown tags like ```json or any other conversational text.
        Each object in the array must have the following keys:
        - "category": (must be one of: "Technical", "Behavioral", "Situational", "Company-Specific", "General")
        - "question": (the full interview question text)
        - "answer": (your custom tailored answer using STAR or deep technical detail)
        - "key_terms": (a comma-separated string of 3-5 key technical terms or concepts used)
    """)

    print(f"  [AI] Generating tailored answers for {company} using {provider} ...")
    
    raw_response = ""
    if provider == "local":
        if not local_endpoint:
            local_endpoint = "http://localhost:11434/v1"
        if not local_model:
            local_model = "llama3"
        raw_response = _local_call(local_endpoint, local_model, prompt)
    else:
        if not client:
            raise ValueError("Gemini client is required for cloud generation.")
        raw_response = _gemini_call_with_retry(
            client,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
            label=f"Answers ({company})",
        )
        
    if not raw_response or not raw_response.strip():
        raise ValueError("Received empty response from the AI provider.")

    # Validate and Parse JSON with Retry
    try:
        return parse_qa_json(raw_response)
    except Exception as parse_err:
        print(f"  [Warning] AI output JSON parsing failed: {parse_err}")
        print("  [Retry] Attempting to fix the malformed JSON with a correction prompt (Retry 1/1) ...")
        
        correction_prompt = textwrap.dedent(f"""\
            Your previous response was not a valid JSON array or was malformed.
            Here is the malformed text you produced:
            ---
            {raw_response}
            ---
            Please correct the JSON format and return ONLY a valid, parseable JSON array.
            Do not include any chat introductory or concluding text, only the raw JSON.
        """)
        
        retry_raw = ""
        try:
            if provider == "local":
                retry_raw = _local_call(local_endpoint, local_model, correction_prompt)
            else:
                retry_raw = _gemini_call_with_retry(
                    client,
                    model="gemini-2.5-flash",
                    contents=correction_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                    label="Correction Retry",
                )
                
            return parse_qa_json(retry_raw)
        except Exception as retry_err:
            print(f"  [Error] JSON correction retry failed: {retry_err}")
            # Save raw response to a debug file to protect privacy while aiding troubleshooting
            debug_file = "debug_raw_ai_response.txt"
            try:
                with open(debug_file, "w", encoding="utf-8") as df:
                    df.write(raw_response)
                print(f"  [Debug] Raw malformed response saved to '{debug_file}' for troubleshooting.")
            except Exception as file_err:
                print(f"  [Warning] Could not write raw debug file: {file_err}")
            raise ValueError(f"AI response parsing failed: {retry_err}")
