"""Tests for database module."""

import pytest
from auxctmailer.database import MemberDatabase
from auxctmailer.exceptions import MemberDataError


class TestMemberDatabase:
    """Tests for MemberDatabase class."""

    def test_load_training_csv(self, sample_training_csv):
        """Test loading training CSV file."""
        db = MemberDatabase(sample_training_csv)
        members = db.get_all_members()
        assert len(members) == 3
        assert members[0]['Member #'] == '1000001'
        assert members[0]['First Name'] == 'JOHN'
        assert members[0]['Last Name'] == 'DOE'

    def test_load_with_email_join(self, sample_training_csv, sample_email_csv):
        """Test loading and joining training and email CSVs."""
        db = MemberDatabase(sample_training_csv, sample_email_csv)
        members = db.get_all_members()
        assert len(members) == 3
        assert members[0]['Email'] == 'john.doe@example.com'
        assert members[1]['Email'] == 'jane.smith@example.com'

    def test_load_with_units(self, sample_training_csv, sample_email_csv, sample_units_csv):
        """Test loading with unit details."""
        db = MemberDatabase(sample_training_csv, sample_email_csv, sample_units_csv)
        members = db.get_all_members()
        assert len(members) == 3
        # Check unit extraction and join
        assert members[0]['Unit Number'] == '0131102'
        assert members[0]['Unit Name'] == 'WOODS HOLE FLOTILLA'
        assert members[0]['Unit Name Pretty'] == 'Woods Hole Flotilla'

    def test_filter_by_status(self, sample_training_csv, sample_email_csv):
        """Test filtering members by status."""
        db = MemberDatabase(sample_training_csv, sample_email_csv)
        certified = db.filter_members(Status='Certified')
        assert len(certified) == 2
        assert all(m['Status'] == 'Certified' for m in certified)

    def test_filter_by_member_number(self, sample_training_csv, sample_email_csv):
        """Test filtering by member number."""
        db = MemberDatabase(sample_training_csv, sample_email_csv)
        members = db.filter_members(**{'Member #': '1000002'})
        assert len(members) == 1
        # Note: When joining CSVs with duplicate columns, pandas adds _x and _y suffixes
        # First Name_x comes from training CSV, First Name_y from email CSV
        assert members[0]['First Name_x'] == 'JANE' or members[0]['First Name_y'] == 'JANE'

    def test_extract_unit_number(self, sample_training_csv):
        """Test unit number extraction from Unit/Member/Competency/Status field."""
        db = MemberDatabase(sample_training_csv)
        members = db.get_all_members()
        assert members[0]['Unit Number'] == '0131102'
        assert members[1]['Unit Number'] == '0131102'
        assert members[2]['Unit Number'] == '0140203'

    def test_prettify_unit_number(self, sample_training_csv):
        """Test unit number prettification."""
        db = MemberDatabase(sample_training_csv)
        members = db.get_all_members()
        assert members[0]['Unit Number Pretty'] == '013-11-02'
        assert members[2]['Unit Number Pretty'] == '014-02-03'

    def test_prettify_unit_name(self, sample_training_csv, sample_email_csv, sample_units_csv):
        """Test unit name prettification."""
        db = MemberDatabase(sample_training_csv, sample_email_csv, sample_units_csv)
        members = db.get_all_members()
        # "WOODS HOLE FLOTILLA" -> "Woods Hole Flotilla"
        assert members[0]['Unit Name Pretty'] == 'Woods Hole Flotilla'
        # "CASCO BAY FLOT" -> "Casco Bay Flotilla"
        assert members[2]['Unit Name Pretty'] == 'Casco Bay Flotilla'

    def test_uniform_exempt_flag(self, sample_training_csv, sample_email_csv):
        """Test uniform exempt flag is joined correctly."""
        db = MemberDatabase(sample_training_csv, sample_email_csv)
        members = db.get_all_members()
        assert members[0]['Uniform Exempt'] == 0
        assert members[1]['Uniform Exempt'] == 0
        assert members[2]['Uniform Exempt'] == 1

    def test_missing_training_csv_raises_error(self):
        """Test that missing training CSV raises MemberDataError."""
        db = MemberDatabase('/nonexistent/path/training.csv')
        with pytest.raises(MemberDataError, match="Training database not found"):
            db.load()

    def test_invalid_csv_raises_error(self, tmp_path):
        """Test that corrupted CSV file raises MemberDataError."""
        # Create a binary file that's not readable as CSV
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)  # PNG header + garbage
        db = MemberDatabase(str(bad_csv))
        with pytest.raises(MemberDataError, match="Failed to load training CSV"):
            db.load()
