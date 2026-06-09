"""
test_prep_generator.py
======================
Unit tests for the modular Interview Prep Guide Generator.
Uses fake sample data and unittest mocks to verify document loading,
JSON parsing, filename sanitization, HTML escaping, and PDF generation.
"""

import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

import utils
import doc_loader
import pdf_generator
import ai_provider

class TestUtils(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(utils.sanitize_filename("PNC Financial"), "PNC_Financial")
        self.assertEqual(utils.sanitize_filename("Google & Co."), "Google_Co")
        self.assertEqual(utils.sanitize_filename("Role: SOC Analyst / Admin"), "Role_SOC_Analyst_Admin")
        self.assertEqual(utils.sanitize_filename(""), "unnamed")
        self.assertEqual(utils.sanitize_filename(None), "unnamed")

    def test_escape_html_for_reportlab(self):
        self.assertEqual(utils.escape_html_for_reportlab("A & B < C > D"), "A &amp; B &lt; C &gt; D")
        self.assertEqual(utils.escape_html_for_reportlab(""), "")
        self.assertEqual(utils.escape_html_for_reportlab(None), "")

    def test_format_answer_html(self):
        raw_answer = "Situation: Alert fired.\nTask: Investigate.\nAction: Ran scan.\nResult: Clean.\nAlso **bold** text."
        formatted = utils.format_answer_html(raw_answer, "#415A77")
        self.assertIn("<b><font color=\"#415A77\">Situation:</font></b>", formatted)
        self.assertIn("<b>bold</b>", formatted)
        self.assertIn("<br/>", formatted)

    def test_clean_json_string(self):
        raw_md = "```json\n[\n  {\"question\": \"Q1\"}\n]\n```"
        self.assertEqual(utils.clean_json_string(raw_md), "[\n  {\"question\": \"Q1\"}\n]")
        self.assertEqual(utils.clean_json_string("   []   "), "[]")

    def test_parse_qa_json(self):
        # Valid JSON
        valid_json = json.dumps([
            {
                "category": "Technical",
                "question": "What is TLS?",
                "answer": "Transport Layer Security secures web traffic.",
                "key_terms": "TLS, HTTPS, encryption"
            }
        ])
        qa_list = utils.parse_qa_json(valid_json)
        self.assertEqual(len(qa_list), 1)
        self.assertEqual(qa_list[0]["category"], "Technical")
        self.assertEqual(qa_list[0]["question"], "What is TLS?")

        # Invalid JSON
        with self.assertRaises(Exception):
            utils.parse_qa_json("invalid json string")

        # Invalid Schema (Not a list)
        with self.assertRaises(ValueError):
            utils.parse_qa_json("{\"question\": \"What is TLS?\"}")


class TestDocLoader(unittest.TestCase):
    @patch('docx.Document')
    def test_load_docx_success(self, mock_doc):
        # Setup mock paragraphs
        mock_p1 = MagicMock()
        mock_p1.text = "This is paragraph 1."
        mock_p2 = MagicMock()
        mock_p2.text = "This is paragraph 2."
        
        mock_instance = MagicMock()
        mock_instance.paragraphs = [mock_p1, mock_p2]
        mock_doc.return_value = mock_instance
        
        # We mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            text = doc_loader.load_docx("fake_path.docx")
            self.assertEqual(text, "This is paragraph 1.\nThis is paragraph 2.")

    def test_load_docx_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            doc_loader.load_docx("non_existent_file.docx")

    def test_load_docx_empty_path(self):
        with self.assertRaises(ValueError):
            doc_loader.load_docx("")


class TestPdfGenerator(unittest.TestCase):
    def test_generate_pdf_success(self):
        qa_pairs = [
            {
                "category": "Technical",
                "question": "What is hashing?",
                "answer": "Hashing maps data to fixed-size values.",
                "key_terms": "SHA-256, collision resistance"
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "test_output.pdf")
            pdf_generator.generate_pdf(
                qa_pairs=qa_pairs,
                company="TestCorp",
                role="Security Engineer",
                candidate_name="John Doe",
                output_path=pdf_path
            )
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 0)

    def test_generate_pdf_empty_qa(self):
        with self.assertRaises(ValueError):
            pdf_generator.generate_pdf(
                qa_pairs=[],
                company="TestCorp",
                role="Security Engineer",
                candidate_name="John Doe",
                output_path="test.pdf"
            )


class TestAiProvider(unittest.TestCase):
    @patch('ai_provider._local_call')
    def test_generate_tailored_answers_local(self, mock_local):
        # Setup mock local response
        mock_response = json.dumps([
            {
                "category": "Technical",
                "question": "How do you secure SSH?",
                "answer": "Disable password authentication, use key pairs.",
                "key_terms": "SSH keys, pam, secure configurations"
            }
        ])
        mock_local.return_value = mock_response

        qa_pairs = ai_provider.generate_tailored_answers(
            client=None,
            company="TestCorp",
            role="Analyst",
            questions_text="[Technical] How do you secure SSH?",
            resume_text="Resume details",
            ruc_text="Ruc details",
            candidate_name="Jane Doe",
            provider="local",
            local_endpoint="http://localhost:11434/v1",
            local_model="llama3"
        )
        self.assertEqual(len(qa_pairs), 1)
        self.assertEqual(qa_pairs[0]["category"], "Technical")
        self.assertEqual(qa_pairs[0]["question"], "How do you secure SSH?")
        
if __name__ == '__main__':
    unittest.main()
