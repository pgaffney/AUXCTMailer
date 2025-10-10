"""Template context processing functions."""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pandas as pd

from auxctmailer.logger import get_logger

logger = get_logger(__name__)


def normalize_keys(data: Dict) -> Dict:
    """Normalize dictionary keys to be template-friendly.

    Converts keys like "First Name" to "first_name" and "Member #" to "member_num".

    Args:
        data: Dictionary with potentially problematic keys

    Returns:
        Dictionary with normalized keys (also keeps original keys)
    """
    normalized = dict(data)  # Keep original keys

    for key, value in data.items():
        # Create a normalized version of the key
        normalized_key = key.lower().replace(' ', '_').replace('#', 'num').replace('?', '').replace('/', '_')
        # Remove any other special characters
        normalized_key = re.sub(r'[^\w_]', '', normalized_key)
        normalized[normalized_key] = value

    return normalized


def add_date_context(data: Dict, extraction_date: Optional[str] = None) -> Dict:
    """Add date-related context variables.

    Args:
        data: Dictionary to add date context to
        extraction_date: Optional extraction date string (MM/DD/YYYY)

    Returns:
        Dictionary with added date context
    """
    # Determine the reference date for days_until_due calculations
    if extraction_date:
        try:
            reference_date = datetime.strptime(extraction_date, "%m/%d/%Y")
        except ValueError:
            logger.warning(f"Invalid extraction date format: {extraction_date}. Using today.")
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    # Add current year information for template logic
    now = datetime.now()
    data['current_year'] = now.year
    data['current_year_start'] = f"1/1/{now.year}"
    data['current_year_end'] = f"12/31/{now.year}"

    # Add extraction date to context
    data['extraction_date'] = extraction_date if extraction_date else reference_date.strftime("%m/%d/%Y")

    # Calculate 365 days after extraction date for "no courses due" message
    extraction_plus_365 = reference_date + timedelta(days=365)
    data['extraction_plus_365'] = extraction_plus_365.strftime("%m/%d/%Y")

    return data


def process_name_formatting(data: Dict) -> Dict:
    """Process name formatting for friendlier display.

    Args:
        data: Dictionary with name fields

    Returns:
        Dictionary with formatted name fields added
    """
    # Create title case version of first name for friendlier greeting
    # Keep original first_name unchanged for member info display
    first_name = data.get('first_name') or data.get('First Name')
    if first_name and isinstance(first_name, str) and first_name.isupper():
        data['first_name_titlecase'] = first_name.title()
    else:
        data['first_name_titlecase'] = first_name

    return data


def check_uniform_inspection(data: Dict) -> Dict:
    """Check uniform inspection status and determine if renewal needed.

    Args:
        data: Dictionary with uniform inspection data

    Returns:
        Dictionary with uniform inspection status added
    """
    now = datetime.now()
    uniform_inspection = data.get('uniform_inspection') or data.get('Uniform Inspection')
    uniform_exempt = data.get('uniform_exempt') or data.get('Uniform Exempt')

    # Check if member is exempt from uniform inspections
    is_uniform_exempt = False
    if uniform_exempt is not None and str(uniform_exempt).strip() in ['1', '1.0']:
        is_uniform_exempt = True

    needs_inspection = True  # Default to needing inspection

    # If exempt, no inspection needed
    if is_uniform_exempt:
        needs_inspection = False
    # Check if uniform_inspection is NaN or empty
    elif uniform_inspection and str(uniform_inspection).strip() and str(uniform_inspection).lower() != 'nan':
        try:
            # Try to parse the date (handles formats like "2/20/2024", "2/18/2025", etc.)
            inspection_date = datetime.strptime(str(uniform_inspection).strip(), "%m/%d/%Y")
            year_start = datetime(now.year, 1, 1)
            # If inspection is this year or later, they don't need a new one
            needs_inspection = inspection_date < year_start
        except (ValueError, AttributeError):
            # If we can't parse the date, assume they need inspection
            logger.debug(f"Could not parse uniform inspection date: {uniform_inspection}")
            needs_inspection = True
            uniform_inspection = None
    else:
        # Clear NaN or empty values
        uniform_inspection = None

    # Update the data dict
    data['uniform_inspection'] = uniform_inspection
    data['uniform_exempt'] = is_uniform_exempt
    data['needs_uniform_inspection'] = needs_inspection

    return data


def process_course_warnings(
    data: Dict,
    courses_csv: Optional[str] = None,
    extraction_date: Optional[str] = None
) -> Dict:
    """Process course requirements and generate warnings.

    Args:
        data: Dictionary with member and course data
        courses_csv: Optional path to courses CSV file
        extraction_date: Optional extraction date (MM/DD/YYYY)

    Returns:
        Dictionary with course warning lists added
    """
    # Determine reference date
    if extraction_date:
        try:
            reference_date = datetime.strptime(extraction_date, "%m/%d/%Y")
        except ValueError:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    now = datetime.now()
    courses_overdue: List[Dict] = []
    courses_due_soon: List[Dict] = []

    if courses_csv and os.path.exists(courses_csv):
        try:
            courses_df = pd.read_csv(courses_csv)

            for _, course in courses_df.iterrows():
                code = str(course['Code']).strip()
                title = course['Title']
                url = course['URL']
                enrollment_code = course.get('EnrollmentCode', '')

                # Get days until due from the member's record
                days_until_due = data.get(code)

                if days_until_due is not None and pd.notna(days_until_due):
                    try:
                        days = int(float(days_until_due))

                        # Calculate the actual due date from extraction date + days
                        actual_due_date = reference_date + timedelta(days=days)

                        # Calculate days from TODAY to the due date
                        days_from_today = (actual_due_date - now).days

                        # Special case: Certain courses with days=0 are due 12/31 of current year
                        # SP_100643: Suicide Prevention
                        # CRA_502319: Civil Rights Awareness
                        # SAPRR_502379: Sexual Assault Prevention, Response, and Recovery
                        if code in ['SP_100643', 'CRA_502319', 'SAPRR_502379'] and days == 0:
                            year_end = datetime(now.year, 12, 31)
                            courses_due_soon.append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_until_due': (year_end - now).days,
                                'due_date': year_end.strftime("%m/%d/%Y")
                            })
                        elif days_from_today < 0:
                            # Course is overdue (due date has passed)
                            courses_overdue.append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_overdue': abs(days_from_today)
                            })
                        elif 0 <= days_from_today <= 365:
                            # Course is due soon (within next 365 days)
                            courses_due_soon.append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_until_due': days_from_today,
                                'due_date': actual_due_date.strftime("%m/%d/%Y")
                            })
                        # If days_from_today > 365, don't add any warning
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse days_until_due for course {code}: {days_until_due}")
                        pass
        except Exception as e:
            # If we can't load courses, just continue without course warnings
            logger.warning(f"Failed to load courses CSV: {e}")
            pass

    data['courses_overdue'] = courses_overdue
    data['courses_due_soon'] = courses_due_soon
    data['has_overdue_courses'] = len(courses_overdue) > 0
    data['has_due_soon_courses'] = len(courses_due_soon) > 0

    return data


def normalize_template_context(
    data: Dict,
    courses_csv: Optional[str] = None,
    extraction_date: Optional[str] = None
) -> Dict:
    """Normalize dictionary keys and add template context.

    This is the main entry point that coordinates all context processing.

    Args:
        data: Dictionary with potentially problematic keys
        courses_csv: Optional path to courses CSV file
        extraction_date: Optional extraction date string (MM/DD/YYYY)

    Returns:
        Dictionary with normalized keys and full template context
    """
    # Start with key normalization
    result = normalize_keys(data)

    # Add date context
    result = add_date_context(result, extraction_date)

    # Process name formatting
    result = process_name_formatting(result)

    # Check uniform inspection status
    result = check_uniform_inspection(result)

    # Process course warnings
    result = process_course_warnings(result, courses_csv, extraction_date)

    return result
