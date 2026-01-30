"""
Tests for deduplication and merging
"""

import pytest
from datetime import datetime, timedelta
from database import (
    init_database, generate_application_id, insert_application,
    get_application, get_connection
)
from deduplicator import find_matching_application, merge_application_data
from config import MERGE_WINDOW_DAYS


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create temporary test database"""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr('database.DATABASE_PATH', db_path)
    init_database()
    yield db_path
    # Cleanup handled by tmp_path


class TestApplicationID:
    """Test application ID generation"""
    
    def test_stable_id_generation(self):
        """Same inputs should produce same ID"""
        id1 = generate_application_id("TechCorp", "Software Engineer", "https://jobs.example.com/123", "2024-01-15")
        id2 = generate_application_id("TechCorp", "Software Engineer", "https://jobs.example.com/123", "2024-01-15")
        
        assert id1 == id2
    
    def test_different_company_different_id(self):
        """Different company should produce different ID"""
        id1 = generate_application_id("TechCorp", "Engineer", "", "2024-01-15")
        id2 = generate_application_id("OtherCorp", "Engineer", "", "2024-01-15")
        
        assert id1 != id2
    
    def test_different_role_different_id(self):
        """Different role should produce different ID"""
        id1 = generate_application_id("TechCorp", "Engineer", "", "2024-01-15")
        id2 = generate_application_id("TechCorp", "Manager", "", "2024-01-15")
        
        assert id1 != id2
    
    def test_normalized_inputs(self):
        """Case and whitespace variations should produce same ID"""
        id1 = generate_application_id("TechCorp", "Software Engineer", "", "2024-01-15")
        id2 = generate_application_id("techcorp", "software engineer", "", "2024-01-15")
        id3 = generate_application_id("  TechCorp  ", "  Software Engineer  ", "", "2024-01-15")
        
        assert id1 == id2 == id3


class TestDeduplication:
    """Test deduplication logic"""
    
    def test_find_by_url(self, test_db):
        """Should find application by exact URL match"""
        app_id = generate_application_id("TechCorp", "Engineer", "https://jobs.example.com/123", "2024-01-15")
        insert_application(
            application_id=app_id,
            source="manual",
            company="TechCorp",
            role_title="Engineer",
            location=None,
            job_url="https://jobs.example.com/123",
            status="Applied",
            status_confidence="High",
            applied_date="2024-01-15"
        )
        
        found_id = find_matching_application(
            company="Different Corp",  # Different company
            role_title="Different Role",  # Different role
            job_url="https://jobs.example.com/123",  # Same URL
            applied_date="2024-01-20"
        )
        
        assert found_id == app_id
    
    def test_find_by_company_role_date_within_window(self, test_db):
        """Should find application by company+role within merge window"""
        applied_date = "2024-01-15T10:00:00+01:00"
        app_id = generate_application_id("TechCorp", "Software Engineer", "", applied_date)
        insert_application(
            application_id=app_id,
            source="manual",
            company="TechCorp",
            role_title="Software Engineer",
            location=None,
            job_url=None,
            status="Applied",
            status_confidence="High",
            applied_date=applied_date
        )
        
        # Within window (7 days later, default window is 14)
        search_date = "2024-01-22T10:00:00+01:00"
        found_id = find_matching_application(
            company="TechCorp",
            role_title="Software Engineer",
            job_url=None,
            applied_date=search_date
        )
        
        assert found_id == app_id
    
    def test_not_find_outside_window(self, test_db):
        """Should NOT find application outside merge window"""
        applied_date = "2024-01-15T10:00:00+01:00"
        app_id = generate_application_id("TechCorp", "Software Engineer", "", applied_date)
        insert_application(
            application_id=app_id,
            source="manual",
            company="TechCorp",
            role_title="Software Engineer",
            location=None,
            job_url=None,
            status="Applied",
            status_confidence="High",
            applied_date=applied_date
        )
        
        # Outside window (20 days later, default window is 14)
        search_date = "2024-02-05T10:00:00+01:00"
        found_id = find_matching_application(
            company="TechCorp",
            role_title="Software Engineer",
            job_url=None,
            applied_date=search_date
        )
        
        assert found_id is None


class TestMerging:
    """Test data merging"""
    
    def test_merge_fills_blanks(self, test_db):
        """Should fill in blank fields but not overwrite existing"""
        app_id = generate_application_id("TechCorp", "", "", "2024-01-15")
        insert_application(
            application_id=app_id,
            source="email",
            company="TechCorp",
            role_title=None,  # Blank
            location=None,  # Blank
            job_url=None,  # Blank
            status="Applied",
            status_confidence="Medium",
            applied_date="2024-01-15"
        )
        
        # Merge new data
        merge_application_data(
            app_id,
            new_company="Different Corp",  # Should NOT overwrite
            new_role="Software Engineer",  # Should fill
            new_location="Berlin",  # Should fill
            new_job_url="https://jobs.example.com/123"  # Should fill
        )
        
        app = get_application(app_id)
        
        assert app["company"] == "TechCorp"  # Original preserved
        assert app["role_title"] == "Software Engineer"  # Filled
        assert app["location"] == "Berlin"  # Filled
        assert app["job_url"] == "https://jobs.example.com/123"  # Filled
    
    def test_merge_appends_notes(self, test_db):
        """Should append notes rather than overwrite"""
        app_id = generate_application_id("TechCorp", "Engineer", "", "2024-01-15")
        insert_application(
            application_id=app_id,
            source="manual",
            company="TechCorp",
            role_title="Engineer",
            location=None,
            job_url=None,
            status="Applied",
            status_confidence="High",
            applied_date="2024-01-15",
            notes="First note"
        )
        
        merge_application_data(
            app_id,
            new_company=None,
            new_role=None,
            new_location=None,
            new_job_url=None,
            new_notes="Second note"
        )
        
        app = get_application(app_id)
        
        assert "First note" in app["notes"]
        assert "Second note" in app["notes"]