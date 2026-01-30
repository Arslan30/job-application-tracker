"""
Tests for email classification
"""

import pytest
from classifier import classify_email, extract_company, extract_role, extract_metadata


class TestClassification:
    """Test email classification"""
    
    def test_applied_classification_high_confidence(self):
        subject = "Application Received - Software Engineer"
        sender = "noreply@careers.example.com"
        body = "Thank you for applying. We have received your application."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Applied"
        assert confidence == "High"
        assert score >= 5
    
    def test_rejected_classification(self):
        subject = "Unfortunately, we are moving forward with other candidates"
        sender = "recruiting@example.com"
        body = "We regret to inform you that we will not be moving forward."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Rejected"
        assert confidence in ["High", "Medium"]
    
    def test_interview_classification(self):
        subject = "Interview Invitation - Next Steps"
        sender = "hr@example.com"
        body = "We would like to schedule an interview with you."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Interview"
        assert confidence in ["High", "Medium"]
    
    def test_offer_classification(self):
        subject = "Congratulations! Job Offer"
        sender = "hr@example.com"
        body = "We are pleased to offer you the position."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Offer"
        assert confidence in ["High", "Medium"]
    
    def test_other_classification(self):
        subject = "Newsletter"
        sender = "marketing@example.com"
        body = "Check out our latest products."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Other"
        assert confidence == "Low"
    
    def test_german_keywords(self):
        subject = "Ihre Bewerbung ist eingegangen"
        sender = "bewerbung@firma.de"
        body = "Vielen Dank für Ihre Bewerbung."
        
        event_type, confidence, score = classify_email(subject, sender, body)
        
        assert event_type == "Applied"


class TestExtraction:
    """Test metadata extraction"""
    
    def test_extract_company_with_gmbh(self):
        text = "Application at Acme Solutions GmbH"
        company = extract_company(text, "")
        
        assert company is not None
        assert "Acme" in company
        assert "GmbH" in company
    
    def test_extract_company_with_inc(self):
        text = "Thank you for applying to TechCorp Inc"
        company = extract_company(text, "")
        
        assert company is not None
        assert "TechCorp" in company
    
    def test_extract_role_software_engineer(self):
        text = "Application for Senior Software Engineer position"
        role = extract_role(text, "")
        
        assert role is not None
        assert "Software Engineer" in role
    
    def test_extract_role_data_scientist(self):
        text = "Your application for Data Scientist role"
        role = extract_role(text, "")
        
        assert role is not None
        assert "Data Scientist" in role
    
    def test_extract_metadata_complete(self):
        subject = "Application Received - Senior Developer at TechCorp Inc"
        sender = "jobs@techcorp.com"
        body = "We have received your application for Senior Software Developer."
        
        metadata = extract_metadata(subject, sender, body)
        
        assert metadata["event_type"] == "Applied"
        assert metadata["confidence"] in ["High", "Medium", "Low"]
        assert metadata["company"] is not None
        assert metadata["role_title"] is not None