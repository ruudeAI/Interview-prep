#!/usr/bin/env python3
"""
interview_prep_generator.py
===========================
Main CLI entry point for the Interview Prep Guide Generator.
Orchestrates CLI parsing, document loading, AI generation, and PDF building.
Supports a secure demo mode for testing without real candidate files or API keys.
"""

import argparse
import os
import sys
import textwrap
from dotenv import load_dotenv

from google import genai

# Import modular project components
import utils
import doc_loader
import ai_provider
import pdf_generator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_api_key():
    """Resolve the Gemini API key from environment, .env, or interactive prompt."""
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
        
    print("\n+---------------------------------------------+")
    print("|  No GEMINI_API_KEY found in environment.    |")
    print("|  Provide a key or set it in a .env file.    |")
    print("+---------------------------------------------+")
    key = input("  [Key] Enter your Gemini API key (press Enter to skip): ").strip()
    return key

def check_privacy_consent(provider, yes_flag):
    """Confirm the user consents to upload files to a cloud service if using Gemini."""
    if provider != "gemini":
        return True
        
    if yes_flag:
        return True

    print("\n+--------------------------------------------------------+")
    print("|  PRIVACY NOTE                                          |")
    print("|  This tool will send your resume and career            |")
    print("|  information (resume/RUC files) to the Gemini cloud API|")
    print("|  for analysis and answer generation.                   |")
    print("+--------------------------------------------------------+")
    
    confirm = input("  Do you want to proceed sending this data to Gemini? (y/N): ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("\n  [Cancelled] Upload cancelled. Use '--provider local' for private local generation.")
        sys.exit(0)
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Generate premium interview prep PDFs tailored to a candidate's background.",
    )
    # Target Job Configurations
    parser.add_argument(
        "--companies",
        type=str,
        default=None,
        help='Comma-separated company names, e.g. "CloudCorp, CyberSecInc"',
    )
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="Target job role (default: Cybersecurity Analyst)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=SCRIPT_DIR,
        help="Directory to save generated PDFs (default: current script directory)",
    )
    
    # Candidate Configurations (Removed hardcoded credentials)
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to candidate resume (.docx file)",
    )
    parser.add_argument(
        "--ruc",
        type=str,
        default=None,
        help="Path to candidate detailed RUC / background details (.docx file)",
    )
    parser.add_argument(
        "--candidate-name",
        type=str,
        default="Candidate",
        help="Candidate's name for document headers and cover page (default: 'Candidate')",
    )

    # AI Model Provider Configurations
    parser.add_argument(
        "--provider",
        type=str,
        choices=["gemini", "local"],
        default="gemini",
        help="Inference engine provider: 'gemini' (default) or 'local' (Ollama/Odysseus)",
    )
    parser.add_argument(
        "--local-endpoint",
        type=str,
        default="http://localhost:11434/v1",
        help="Local OpenAI-compatible API base URL (default: http://localhost:11434/v1)",
    )
    parser.add_argument(
        "--local-model",
        type=str,
        default="llama3",
        help="Model name on the local LLM server (default: llama3)",
    )
    
    # Flags
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip privacy prompts and automatically approve cloud upload",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode using fake sample candidate and company data",
    )
    args = parser.parse_args()

    # ── Banner ──
    print()
    print("+----------------------------------------------------------+")
    print("|             INTERVIEW PREP GENERATOR                     |")
    print("|       Tailored Q&A guides from your resume & history     |")
    print("+----------------------------------------------------------+")
    print()

    # ── Resolve Input Files & Parameters ──
    resume_text = ""
    ruc_text = ""
    candidate_name = args.candidate_name
    companies = []
    use_mock_qa = False

    if args.demo:
        print("  [Warning] DEMO MODE ACTIVE")
        print("  Generating demo prep guide with mock data.")
        candidate_name = "Jane Doe"
        resume_text = textwrap.dedent("""\
            Jane Doe is a Cybersecurity Analyst with 3 years of experience in SOC monitoring,
            vulnerability scanning with Nessus, and incident response. Proficient in Wireshark,
            Splunk, and Python scripting. Certified CompTIA Security+ and CEH.
        """)
        ruc_text = textwrap.dedent("""\
            Vulnerability Management: Configured Nessus scanner to perform weekly scans across 150+ subnets.
            Remediation: Stood up Splunk dashboards to track ticket remediation times, decreasing SLA breaches by 15%.
            Incident Response: Investigated phishing alerts and coordinated host isolation for infected systems.
        """)
        companies = [c.strip() for c in (args.companies.split(",") if args.companies else ["CloudCorp"])]
        role = args.role if args.role else "Security Analyst"
    else:
        # Resolve companies
        if args.companies:
            companies = [c.strip() for c in args.companies.split(",") if c.strip()]
        else:
            raw = input("  [Input] Enter target company names (comma-separated): ").strip()
            if not raw:
                print("  [Error] No companies provided.")
                sys.exit(1)
            companies = [c.strip() for c in raw.split(",") if c.strip()]

        # Resolve role
        role = args.role if args.role else input("  [Input] Enter target role (press Enter for 'Cybersecurity Analyst'): ").strip()
        if not role:
            role = "Cybersecurity Analyst"

        # Resolve resume file path
        resume_path = args.resume
        if not resume_path:
            fallback_resume = os.path.join(SCRIPT_DIR, "resume.docx")
            if os.path.exists(fallback_resume):
                resume_path = fallback_resume
            else:
                print("  [Error] Resume file path is missing.")
                print("  Provide it via '--resume <path>' or place a 'resume.docx' in the current directory.")
                sys.exit(1)

        # Resolve RUC file path
        ruc_path = args.ruc
        if not ruc_path:
            fallback_ruc = os.path.join(SCRIPT_DIR, "ruc.docx")
            if os.path.exists(fallback_ruc):
                ruc_path = fallback_ruc

        # Load documents
        try:
            resume_text = doc_loader.load_docx(resume_path)
            print(f"  [Load] Resume loaded: '{os.path.basename(resume_path)}' ({len(resume_text):,} chars)")
        except Exception as e:
            print(f"  [Error] Loading resume failed: {e}")
            sys.exit(1)

        if ruc_path:
            try:
                ruc_text = doc_loader.load_docx(ruc_path)
                print(f"  [Load] RUC loaded: '{os.path.basename(ruc_path)}' ({len(ruc_text):,} chars)")
            except Exception as e:
                print(f"  [Warning] Loading RUC details failed: {e}")
                print("  Continuing with resume details only.")
        else:
            print("  [Info] No RUC file specified. Continuing with resume details only.")

    print(f"  [Config] Companies : {', '.join(companies)}")
    print(f"  [Config] Role      : {role}")
    print(f"  [Config] Candidate : {candidate_name}")
    print()

    # ── Privacy warnings and consent ──
    if not args.demo:
        check_privacy_consent(args.provider, args.yes)

    # ── Initialize Gemini Client if required ──
    client = None
    if args.provider == "gemini":
        api_key = get_api_key()
        if not api_key:
            if args.demo:
                print("  [Info] No Gemini API key found. Using preset mock data for demo generation.")
                use_mock_qa = True
            else:
                print("  [Error] Gemini API key is missing. Cannot proceed using 'gemini' provider.")
                print("  Set GEMINI_API_KEY in a .env file or run with '--provider local' for offline mode.")
                sys.exit(1)
        else:
            try:
                client = genai.Client(api_key=api_key)
                print("  [Client] Gemini client initialized successfully.\n")
            except Exception as e:
                if args.demo:
                    print(f"  [Warning] Initializing Gemini Client failed: {e}. Using preset mock data.")
                    use_mock_qa = True
                else:
                    print(f"  [Error] Initializing Gemini Client failed: {e}")
                    sys.exit(1)

    # ── Process each company ──
    generated_files = []
    os.makedirs(args.output_dir, exist_ok=True)

    for idx, company in enumerate(companies, 1):
        print(f"  {'-' * 58}")
        print(f"  [{idx}/{len(companies)}]  Processing target: {company}")
        print(f"  {'-' * 58}")

        try:
            # Step 1: Question sourcing
            questions_text = ""
            if client and not use_mock_qa:
                try:
                    questions_text = ai_provider.fetch_interview_questions(client, company, role)
                except Exception as e:
                    print(f"  [Warning] Search grounding failed: {e}")
                    print("  [Fallback] Sourcing standard questions as a fallback ...")
            
            if not questions_text:
                if not use_mock_qa:
                    print("  [Info] Sourcing standard cybersecurity interview questions offline ...")
                questions_text = textwrap.dedent(f"""\
                    [Technical] What is the difference between IDS and IPS?
                    [Technical] How do you secure a web application?
                    [Technical] Can you describe the difference between symmetric and asymmetric encryption?
                    [Technical] What is DNS spoofing and how do you prevent it?
                    [Behavioral] Describe a time you handled a critical incident under pressure.
                    [Behavioral] Tell me about a time you had to explain a complex technical issue to a non-technical stakeholder.
                    [Situational] What would you do if you detected an active ransomware attack on a critical server?
                    [Company-Specific] Why do you want to work at {company} as a {role}?
                """)

            # Step 2: Answer tailored generation and secure JSON parsing
            qa_pairs = []
            if use_mock_qa:
                print("  [Info] Generating mock tailored answers for Demo ...")
                qa_pairs = [
                    {
                        "category": "Technical",
                        "question": "What is the difference between IDS and IPS?",
                        "answer": "Situation: At CloudCorp, we monitored traffic anomalies.\nTask: Differentiate detection vs prevention.\nAction: Configured Snort in detection mode (IDS) to alert on malicious traffic, and inline mode (IPS) to block known attack signatures.\nResult: Blocked 99% of perimeter scans and logged alerts for custom analysis.",
                        "key_terms": "IDS, IPS, Snort, Network Security"
                    },
                    {
                        "category": "Behavioral",
                        "question": "Describe a time you handled a critical incident under pressure.",
                        "answer": "Situation: A phishing alert was triggered indicating potential credential harvesting.\nTask: Contain the breach and verify compromise.\nAction: Checked logs in Splunk, isolated the target host, and revoked user credentials.\nResult: Resolved within 15 minutes, preventing data exfiltration.",
                        "key_terms": "Incident Response, Phishing, Splunk, Containment"
                    }
                ]
            else:
                try:
                    qa_pairs = ai_provider.generate_tailored_answers(
                        client=client,
                        company=company,
                        role=role,
                        questions_text=questions_text,
                        resume_text=resume_text,
                        ruc_text=ruc_text,
                        candidate_name=candidate_name,
                        provider=args.provider,
                        local_endpoint=args.local_endpoint,
                        local_model=args.local_model,
                    )
                except Exception as e:
                    if args.demo:
                        print(f"  [Warning] AI generation failed ({e}). Falling back to demo mock data ...")
                        qa_pairs = [
                            {
                                "category": "Technical",
                                "question": "What is the difference between IDS and IPS?",
                                "answer": "Situation: At CloudCorp, we monitored traffic anomalies.\nTask: Differentiate detection vs prevention.\nAction: Configured Snort in detection mode (IDS) to alert on malicious traffic, and inline mode (IPS) to block known attack signatures.\nResult: Blocked 99% of perimeter scans and logged alerts for custom analysis.",
                                "key_terms": "IDS, IPS, Snort, Network Security"
                            },
                            {
                                "category": "Behavioral",
                                "question": "Describe a time you handled a critical incident under pressure.",
                                "answer": "Situation: A phishing alert was triggered indicating potential credential harvesting.\nTask: Contain the breach and verify compromise.\nAction: Checked logs in Splunk, isolated the target host, and revoked user credentials.\nResult: Resolved within 15 minutes, preventing data exfiltration.",
                                "key_terms": "Incident Response, Phishing, Splunk, Containment"
                            }
                        ]
                    else:
                        raise

            if not qa_pairs:
                print(f"  [Warning] No Q&A pairs could be structured for {company}. Skipping PDF generation.")
                continue

            print(f"  [Success] Structured {len(qa_pairs)} Q&A pairs.")

            # Step 3: PDF Generation
            safe_company = utils.sanitize_filename(company)
            safe_role = utils.sanitize_filename(role)
            filename = f"{safe_company}_{safe_role}_Interview_Prep.pdf"
            output_path = os.path.join(args.output_dir, filename)

            pdf_generator.generate_pdf(
                qa_pairs=qa_pairs,
                company=company,
                role=role,
                candidate_name=candidate_name,
                output_path=output_path,
            )

            generated_files.append(output_path)
            print(f"  [Output] PDF saved successfully: {filename}\n")

        except Exception as e:
            print(f"  [Error] Error processing {company}: {e}\n")

    # ── Summary ──
    print()
    print("+----------------------------------------------------------+")
    print("|              GENERATION COMPLETE                         |")
    print("+----------------------------------------------------------+")
    print()
    if generated_files:
        print(f"  Generated {len(generated_files)} PDF(s):")
        for f in generated_files:
            print(f"    - {os.path.basename(f)}")
        print(f"\n  Output directory: {args.output_dir}")
    else:
        print("  [Warning] No preparation PDFs were generated.")
    print()

if __name__ == "__main__":
    main()
