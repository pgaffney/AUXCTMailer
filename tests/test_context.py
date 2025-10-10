"""Tests for context module."""

import pytest
from datetime import datetime
from auxctmailer.context import (
    normalize_keys,
    add_date_context,
    process_name_formatting,
    check_uniform_inspection,
    process_course_warnings,
    normalize_template_context,
)


class TestNormalizeKeys:
    """Tests for normalize_keys function."""

    def test_normalize_simple_keys(self):
        """Test normalizing simple dictionary keys."""
        data = {'First Name': 'John', 'Last Name': 'Doe'}
        result = normalize_keys(data)
        assert result['first_name'] == 'John'
        assert result['last_name'] == 'Doe'
        # Original keys preserved
        assert result['First Name'] == 'John'

    def test_normalize_special_characters(self):
        """Test normalizing keys with special characters."""
        data = {'Member #': '12345', 'Email?': 'test@example.com'}
        result = normalize_keys(data)
        assert result['member_num'] == '12345'
        assert result['email'] == 'test@example.com'

    def test_normalize_slashes(self):
        """Test normalizing keys with slashes."""
        data = {'Date/Time': '2025-01-01'}
        result = normalize_keys(data)
        assert result['date_time'] == '2025-01-01'


class TestAddDateContext:
    """Tests for add_date_context function."""

    def test_add_date_context_with_extraction_date(self):
        """Test adding date context with extraction date."""
        data = {}
        result = add_date_context(data, extraction_date='10/01/2025')
        assert result['extraction_date'] == '10/01/2025'
        assert result['current_year'] == datetime.now().year
        assert 'extraction_plus_365' in result

    def test_add_date_context_without_extraction_date(self):
        """Test adding date context without extraction date."""
        data = {}
        result = add_date_context(data)
        assert 'extraction_date' in result
        assert 'current_year' in result
        assert 'current_year_start' in result
        assert 'current_year_end' in result

    def test_invalid_extraction_date_falls_back(self):
        """Test invalid extraction date falls back to today."""
        data = {}
        result = add_date_context(data, extraction_date='invalid-date')
        # Should not crash, should use today instead
        assert 'extraction_date' in result


class TestProcessNameFormatting:
    """Tests for process_name_formatting function."""

    def test_uppercase_name_to_titlecase(self):
        """Test converting uppercase name to title case."""
        data = {'first_name': 'JOHN'}
        result = process_name_formatting(data)
        assert result['first_name_titlecase'] == 'John'

    def test_already_titlecase_name(self):
        """Test name already in title case."""
        data = {'first_name': 'John'}
        result = process_name_formatting(data)
        assert result['first_name_titlecase'] == 'John'

    def test_missing_first_name(self):
        """Test handling missing first name."""
        data = {}
        result = process_name_formatting(data)
        assert result['first_name_titlecase'] is None


class TestCheckUniformInspection:
    """Tests for check_uniform_inspection function."""

    def test_uniform_exempt_member(self):
        """Test member exempt from uniform inspections."""
        data = {'uniform_exempt': 1}
        result = check_uniform_inspection(data)
        assert result['uniform_exempt'] is True
        assert result['needs_uniform_inspection'] is False

    def test_uniform_inspection_current_year(self):
        """Test member with current year inspection."""
        current_year = datetime.now().year
        data = {'uniform_inspection': f'2/20/{current_year}', 'uniform_exempt': 0}
        result = check_uniform_inspection(data)
        assert result['needs_uniform_inspection'] is False

    def test_uniform_inspection_last_year(self):
        """Test member with last year inspection."""
        last_year = datetime.now().year - 1
        data = {'uniform_inspection': f'12/15/{last_year}', 'uniform_exempt': 0}
        result = check_uniform_inspection(data)
        assert result['needs_uniform_inspection'] is True

    def test_missing_uniform_inspection(self):
        """Test member with no inspection record."""
        data = {'uniform_exempt': 0}
        result = check_uniform_inspection(data)
        assert result['needs_uniform_inspection'] is True
        assert result['uniform_inspection'] is None


class TestProcessCourseWarnings:
    """Tests for process_course_warnings function."""

    def test_overdue_course(self, sample_courses_csv):
        """Test course that is overdue."""
        data = {'PAWR_810015': -10}  # 10 days overdue
        result = process_course_warnings(data, sample_courses_csv, '10/01/2025')
        assert result['has_overdue_courses'] is True
        assert len(result['courses_overdue']) > 0
        # Find the specific course
        pawr_course = next((c for c in result['courses_overdue'] if c['code'] == 'PAWR_810015'), None)
        assert pawr_course is not None

    def test_due_soon_course(self, sample_courses_csv):
        """Test course due within 365 days."""
        data = {'PAWR_810015': 100}  # Due in 100 days from extraction date
        result = process_course_warnings(data, sample_courses_csv, '10/01/2025')
        assert result['has_due_soon_courses'] is True
        assert len(result['courses_due_soon']) > 0

    def test_no_warnings_for_distant_courses(self, sample_courses_csv):
        """Test no warnings for courses due >365 days."""
        data = {'PAWR_810015': 400}  # Due in 400 days
        result = process_course_warnings(data, sample_courses_csv, '10/01/2025')
        assert result['has_overdue_courses'] is False
        assert result['has_due_soon_courses'] is False

    def test_special_courses_with_zero_days(self, sample_courses_csv):
        """Test special handling for SP, CRA, SAPRR courses with 0 days."""
        data = {'SP_100643': 0, 'CRA_502319': 0, 'SAPRR_502379': 0}
        result = process_course_warnings(data, sample_courses_csv, '10/01/2025')
        # These should all be in due_soon with 12/31 deadline
        assert result['has_due_soon_courses'] is True
        assert len(result['courses_due_soon']) == 3
        for course in result['courses_due_soon']:
            assert '12/31' in course['due_date']

    def test_no_courses_csv(self):
        """Test handling when courses CSV is missing."""
        data = {'PAWR_810015': -10}
        result = process_course_warnings(data, None, '10/01/2025')
        assert result['has_overdue_courses'] is False
        assert result['has_due_soon_courses'] is False


class TestNormalizeTemplateContext:
    """Tests for normalize_template_context integration."""

    def test_full_context_processing(self, sample_courses_csv):
        """Test full context processing pipeline."""
        data = {
            'Member #': '1000001',
            'First Name': 'JOHN',
            'Last Name': 'DOE',
            'Uniform Inspection': '2/20/2025',
            'Uniform Exempt': 0,
            'PAWR_810015': 100,
        }
        result = normalize_template_context(data, sample_courses_csv, '10/01/2025')

        # Check normalized keys
        assert result['member_num'] == '1000001'
        assert result['first_name'] == 'JOHN'

        # Check name formatting
        assert result['first_name_titlecase'] == 'John'

        # Check date context
        assert 'current_year' in result
        assert 'extraction_date' in result

        # Check uniform inspection
        assert 'needs_uniform_inspection' in result

        # Check course warnings
        assert 'courses_overdue' in result
        assert 'courses_due_soon' in result
        assert 'has_overdue_courses' in result
        assert 'has_due_soon_courses' in result

    def test_minimal_data(self):
        """Test with minimal data (no courses)."""
        data = {'First Name': 'JANE', 'Last Name': 'SMITH'}
        result = normalize_template_context(data)

        # Should still have all context fields
        assert result['first_name_titlecase'] == 'Jane'
        assert 'current_year' in result
        assert result['has_overdue_courses'] is False
        assert result['has_due_soon_courses'] is False
