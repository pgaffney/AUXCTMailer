"""Load and process member task data from xlsx exports."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from auxctmailer.exceptions import MemberDataError
from auxctmailer.logger import get_logger

logger = get_logger(__name__)

# Task urgency thresholds (in days)
URGENT_THRESHOLD_DAYS = 30  # Red: due within 30 days or overdue
# Note: Yellow threshold is now dynamic based on end of current calendar year


class TaskRecord:
    """Represents a single task for a member."""

    def __init__(
        self,
        competency_type: str,
        competency_status: str,
        task_type: str,
        task_next_due: Optional[datetime],
        task_last_completed: Optional[datetime],
        cycle_requirement: Optional[float],
        currency_units: Optional[float],
    ):
        self.competency_type = competency_type
        self.competency_status = competency_status
        self.task_type = task_type
        self.task_next_due = task_next_due
        self.task_last_completed = task_last_completed
        self.cycle_requirement = cycle_requirement
        self.currency_units = currency_units

    def get_status_bucket(self) -> str:
        """Categorize task by competency status bucket.

        Returns:
            'certified', 'trainee', or 'lapsed'
        """
        status = self.competency_status.lower() if self.competency_status else ''

        if 'trainee' in status or 'not certified' in status:
            return 'trainee'
        elif 'reyr' in status or 'rewk' in status:
            return 'lapsed'
        else:
            # Certified or unknown defaults to certified
            return 'certified'

    def get_urgency(self, reference_date: Optional[datetime] = None) -> str:
        """Determine task urgency based on due date.

        Urgency levels:
        - Red: Overdue or due within 30 days
        - Yellow: Due within current calendar year (after 30-day window)
        - Green: Not due until next calendar year or later

        Args:
            reference_date: Date to calculate from (defaults to today)

        Returns:
            'red', 'yellow', or 'green'
        """
        if reference_date is None:
            reference_date = datetime.now()

        if self.task_next_due is None:
            # No due date - check if it's a requirement that needs completion
            # Tasks without due dates that have never been completed need attention
            if self.task_last_completed is None and self.cycle_requirement:
                return 'yellow'
            return 'green'

        days_until_due = (self.task_next_due - reference_date).days

        if days_until_due < 0:
            # Overdue
            return 'red'
        elif days_until_due <= URGENT_THRESHOLD_DAYS:
            # Due within 30 days
            return 'red'
        else:
            # Check if due within current calendar year
            end_of_year = datetime(reference_date.year, 12, 31)
            if self.task_next_due <= end_of_year:
                return 'yellow'
            else:
                return 'green'

    def to_dict(self, reference_date: Optional[datetime] = None) -> Dict:
        """Convert to dictionary for template rendering."""
        if reference_date is None:
            reference_date = datetime.now()

        days_until_due = None
        days_overdue = None
        due_date_str = None

        if self.task_next_due:
            days_until_due = (self.task_next_due - reference_date).days
            due_date_str = self.task_next_due.strftime("%m/%d/%Y")
            if days_until_due < 0:
                days_overdue = abs(days_until_due)
                days_until_due = None

        last_completed_str = None
        if self.task_last_completed:
            last_completed_str = self.task_last_completed.strftime("%m/%d/%Y")

        return {
            'competency_type': self.competency_type,
            'competency_status': self.competency_status,
            'status_bucket': self.get_status_bucket(),
            'task_type': self.task_type,
            'task_next_due': due_date_str,
            'task_last_completed': last_completed_str,
            'days_until_due': days_until_due,
            'days_overdue': days_overdue,
            'cycle_requirement': self.cycle_requirement,
            'currency_units': self.currency_units,
            'urgency': self.get_urgency(reference_date),
        }


class Competency:
    """Represents a member's competency with status information."""

    # Sort order for status buckets
    STATUS_SORT_ORDER = {'trainee': 1, 'certified': 2, 'lapsed': 3}

    def __init__(
        self,
        competency_type: str,
        competency_status: str,
        status_date: Optional[datetime] = None,
    ):
        self.competency_type = competency_type
        self.competency_status = competency_status
        self.status_date = status_date
        self.tasks: List[TaskRecord] = []

    def get_status_bucket(self) -> str:
        """Categorize competency by status bucket."""
        status = self.competency_status.lower() if self.competency_status else ''
        if 'trainee' in status or 'not certified' in status:
            return 'trainee'
        elif 'reyr' in status or 'rewk' in status:
            return 'lapsed'
        else:
            return 'certified'

    def is_auxct(self) -> bool:
        """Check if this is the AUX Core Training competency."""
        return 'AUXCT' in self.competency_type.upper() or 'CORE TRAINING' in self.competency_type.upper()

    def get_sort_key(self) -> Tuple:
        """Get sort key for ordering competencies.

        Sort order:
        1. AUXCT - Core Training first
        2. Trainee competencies alphabetically
        3. Certified competencies alphabetically
        4. REYR/REWK competencies alphabetically
        """
        is_auxct = 0 if self.is_auxct() else 1
        status_order = self.STATUS_SORT_ORDER.get(self.get_status_bucket(), 99)
        return (is_auxct, status_order, self.competency_type.upper())

    def get_overall_urgency(self, reference_date: Optional[datetime] = None) -> str:
        """Get the most urgent status across all tasks in this competency.

        Returns 'red' if any task is red, 'yellow' if any task is yellow, else 'green'.
        """
        if reference_date is None:
            reference_date = datetime.now()

        urgencies = [task.get_urgency(reference_date) for task in self.tasks]
        if 'red' in urgencies:
            return 'red'
        elif 'yellow' in urgencies:
            return 'yellow'
        return 'green'

    def to_dict(self, reference_date: Optional[datetime] = None) -> Dict:
        """Convert to dictionary for template rendering."""
        if reference_date is None:
            reference_date = datetime.now()

        status_date_str = None
        if self.status_date:
            status_date_str = self.status_date.strftime("%m/%d/%Y")

        # Group tasks by urgency
        tasks_by_urgency = {'red': [], 'yellow': [], 'green': []}
        for task in self.tasks:
            task_dict = task.to_dict(reference_date)
            urgency = task_dict['urgency']
            tasks_by_urgency[urgency].append(task_dict)

        # Sort tasks within each urgency by due date
        for urgency in tasks_by_urgency:
            tasks_by_urgency[urgency].sort(
                key=lambda t: (t['task_next_due'] is None, t['task_next_due'] or '9999-99-99')
            )

        return {
            'competency_type': self.competency_type,
            'competency_status': self.competency_status,
            'status_bucket': self.get_status_bucket(),
            'status_date': status_date_str,
            'is_auxct': self.is_auxct(),
            'is_lapsed': self.get_status_bucket() == 'lapsed',
            'overall_urgency': self.get_overall_urgency(reference_date),
            'tasks': [task.to_dict(reference_date) for task in self.tasks],
            'tasks_red': tasks_by_urgency['red'],
            'tasks_yellow': tasks_by_urgency['yellow'],
            'tasks_green': tasks_by_urgency['green'],
            'has_red': len(tasks_by_urgency['red']) > 0,
            'has_yellow': len(tasks_by_urgency['yellow']) > 0,
            'has_green': len(tasks_by_urgency['green']) > 0,
        }


class MemberRecord:
    """Represents a member with all their tasks."""

    def __init__(
        self,
        unit_number: str,
        last_name: str,
        first_name: str,
        member_id: str,
    ):
        self.unit_number = unit_number
        self.last_name = last_name
        self.first_name = first_name
        self.member_id = member_id
        self.tasks: List[TaskRecord] = []
        self.competencies: Dict[str, Competency] = {}  # keyed by competency_type
        self.email: Optional[str] = None

    def add_task(self, task: TaskRecord) -> None:
        """Add a task to this member's record and its competency."""
        self.tasks.append(task)

        # Also add to the competency
        comp_type = task.competency_type
        if comp_type not in self.competencies:
            self.competencies[comp_type] = Competency(
                competency_type=comp_type,
                competency_status=task.competency_status,
            )
        self.competencies[comp_type].tasks.append(task)

    def get_sorted_competencies(self) -> List[Competency]:
        """Get competencies sorted by the defined order.

        Sort order:
        1. AUXCT - Core Training first
        2. Trainee competencies alphabetically
        3. Certified competencies alphabetically
        4. REYR/REWK competencies alphabetically
        """
        return sorted(self.competencies.values(), key=lambda c: c.get_sort_key())

    def get_tasks_by_urgency(self, reference_date: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """Get tasks grouped by urgency level.

        Returns:
            Dictionary with 'red', 'yellow', 'green' keys containing task lists
        """
        if reference_date is None:
            reference_date = datetime.now()

        result = {'red': [], 'yellow': [], 'green': []}

        for task in self.tasks:
            task_dict = task.to_dict(reference_date)
            urgency = task_dict['urgency']
            result[urgency].append(task_dict)

        # Sort each list by due date (None values at end)
        for urgency in result:
            result[urgency].sort(
                key=lambda t: (
                    t['task_next_due'] is None,
                    t['task_next_due'] or '9999-99-99'
                )
            )

        return result

    def get_tasks_by_status_bucket(self, reference_date: Optional[datetime] = None) -> Dict[str, Dict[str, List[Dict]]]:
        """Get tasks grouped by competency status bucket, then by urgency.

        Returns:
            Dictionary with 'certified', 'trainee', 'lapsed' keys,
            each containing {'red': [], 'yellow': [], 'green': []} task lists
        """
        if reference_date is None:
            reference_date = datetime.now()

        result = {
            'certified': {'red': [], 'yellow': [], 'green': []},
            'trainee': {'red': [], 'yellow': [], 'green': []},
            'lapsed': {'red': [], 'yellow': [], 'green': []},
        }

        for task in self.tasks:
            task_dict = task.to_dict(reference_date)
            bucket = task_dict['status_bucket']
            urgency = task_dict['urgency']
            result[bucket][urgency].append(task_dict)

        # Sort each list by due date (None values at end)
        for bucket in result:
            for urgency in result[bucket]:
                result[bucket][urgency].sort(
                    key=lambda t: (
                        t['task_next_due'] is None,
                        t['task_next_due'] or '9999-99-99'
                    )
                )

        return result

    def to_template_context(self, reference_date: Optional[datetime] = None) -> Dict:
        """Convert to dictionary for template rendering."""
        if reference_date is None:
            reference_date = datetime.now()

        tasks_by_urgency = self.get_tasks_by_urgency(reference_date)
        tasks_by_bucket = self.get_tasks_by_status_bucket(reference_date)

        # Helper to check if a bucket has any tasks
        def bucket_has_tasks(bucket: Dict[str, List]) -> bool:
            return any(len(bucket[u]) > 0 for u in ['red', 'yellow', 'green'])

        def bucket_has_urgency(bucket: Dict[str, List], urgency: str) -> bool:
            return len(bucket[urgency]) > 0

        # Get sorted competencies for the new template format
        sorted_competencies = self.get_sorted_competencies()
        competencies_list = [c.to_dict(reference_date) for c in sorted_competencies]

        # Check if any competency has lapsed (REYR/REWK) status
        has_lapsed_competencies = any(c.get_status_bucket() == 'lapsed' for c in sorted_competencies)

        return {
            'unit_number': self.unit_number,
            'unit_number_pretty': self._prettify_unit_number(self.unit_number),
            'last_name': self.last_name,
            'first_name': self.first_name,
            'first_name_titlecase': self.first_name.title() if self.first_name else '',
            'member_id': self.member_id,
            'member_num': self.member_id,  # Alias for compatibility
            'email': self.email,
            # Sorted competencies for new template format
            'competencies': competencies_list,
            'has_lapsed_competencies': has_lapsed_competencies,
            # Flat urgency lists (for simple template - kept for backwards compatibility)
            'tasks_red': tasks_by_urgency['red'],
            'tasks_yellow': tasks_by_urgency['yellow'],
            'tasks_green': tasks_by_urgency['green'],
            'has_red_tasks': len(tasks_by_urgency['red']) > 0,
            'has_yellow_tasks': len(tasks_by_urgency['yellow']) > 0,
            'has_green_tasks': len(tasks_by_urgency['green']) > 0,
            # Bucket-organized tasks (for organized template)
            'certified': tasks_by_bucket['certified'],
            'trainee': tasks_by_bucket['trainee'],
            'lapsed': tasks_by_bucket['lapsed'],
            'has_certified_tasks': bucket_has_tasks(tasks_by_bucket['certified']),
            'has_trainee_tasks': bucket_has_tasks(tasks_by_bucket['trainee']),
            'has_lapsed_tasks': bucket_has_tasks(tasks_by_bucket['lapsed']),
            # Per-bucket urgency flags
            'certified_has_red': bucket_has_urgency(tasks_by_bucket['certified'], 'red'),
            'certified_has_yellow': bucket_has_urgency(tasks_by_bucket['certified'], 'yellow'),
            'certified_has_green': bucket_has_urgency(tasks_by_bucket['certified'], 'green'),
            'trainee_has_red': bucket_has_urgency(tasks_by_bucket['trainee'], 'red'),
            'trainee_has_yellow': bucket_has_urgency(tasks_by_bucket['trainee'], 'yellow'),
            'trainee_has_green': bucket_has_urgency(tasks_by_bucket['trainee'], 'green'),
            'lapsed_has_red': bucket_has_urgency(tasks_by_bucket['lapsed'], 'red'),
            'lapsed_has_yellow': bucket_has_urgency(tasks_by_bucket['lapsed'], 'yellow'),
            'lapsed_has_green': bucket_has_urgency(tasks_by_bucket['lapsed'], 'green'),
            'total_tasks': len(self.tasks),
            'report_date': reference_date.strftime("%m/%d/%Y"),
        }

    def _prettify_unit_number(self, unit_number: str) -> Optional[str]:
        """Convert unit number to DDD-VV-UU format."""
        if not unit_number or len(unit_number) != 7:
            return unit_number
        return f"{unit_number[0:3]}-{unit_number[3:5]}-{unit_number[5:7]}"


class XlsxTaskLoader:
    """Loads member task data from xlsx exports."""

    def __init__(self, xlsx_path: str, email_csv: Optional[str] = None):
        """Initialize loader.

        Args:
            xlsx_path: Path to the xlsx file
            email_csv: Optional path to CSV with member emails
        """
        self.xlsx_path = Path(xlsx_path)
        self.email_csv = Path(email_csv) if email_csv else None
        self.members: Dict[str, MemberRecord] = {}

    def _find_header_row(self, df: pd.DataFrame) -> int:
        """Find the row containing column headers.

        Looks for a row containing 'Unit/Member Name/ID' or similar.
        """
        for idx in range(min(30, len(df))):
            row_values = df.iloc[idx].astype(str).tolist()
            for val in row_values:
                if 'Unit/Member' in val or 'Member Name' in val:
                    return idx
        raise MemberDataError("Could not find header row in xlsx file")

    def _parse_member_info(self, unit_member_field: str) -> Optional[Tuple[str, str, str, str]]:
        """Parse member info from 'Unit/Member Name/ID' field.

        Format: "Unit: 0131102 | LASTNAME. FIRSTNAME 1234567"

        Returns:
            Tuple of (unit_number, last_name, first_name, member_id) or None
        """
        if pd.isna(unit_member_field) or not isinstance(unit_member_field, str):
            return None

        # Extract unit number
        unit_match = re.search(r'Unit:\s*(\d+)', unit_member_field)
        if not unit_match:
            return None
        unit_number = unit_match.group(1)

        # Extract name and member ID: "LASTNAME. FIRSTNAME 1234567"
        name_match = re.search(r'\|\s*([A-Z]+)\.\s*([A-Z]+)\s+(\d+)', unit_member_field)
        if not name_match:
            return None

        last_name = name_match.group(1)
        first_name = name_match.group(2)
        member_id = name_match.group(3)

        return unit_number, last_name, first_name, member_id

    def _parse_date(self, date_val) -> Optional[datetime]:
        """Parse a date value from the xlsx file."""
        if pd.isna(date_val):
            return None

        # If it's already a datetime, use it directly
        if isinstance(date_val, datetime):
            return date_val

        # If it's a pandas Timestamp, convert
        if isinstance(date_val, pd.Timestamp):
            return date_val.to_pydatetime()

        # Try parsing as string
        date_str = str(date_val).strip()
        if not date_str or date_str.lower() == 'nan':
            return None

        # Try common date formats
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_val}")
        return None

    def load(self) -> Dict[str, MemberRecord]:
        """Load and parse the xlsx file.

        Returns:
            Dictionary mapping member_id to MemberRecord
        """
        if not self.xlsx_path.exists():
            raise MemberDataError(f"xlsx file not found: {self.xlsx_path}")

        # Read the xlsx file
        df_raw = pd.read_excel(self.xlsx_path, header=None)

        # Find header row
        header_row = self._find_header_row(df_raw)
        logger.info(f"Found header row at index {header_row}")

        # Re-read with correct header
        df = pd.read_excel(self.xlsx_path, header=header_row)

        # Clean up column names (remove arrows and extra whitespace)
        df.columns = [re.sub(r'\s*[↑↓]\s*', '', str(col)).strip() for col in df.columns]

        # Find the unit/member column
        unit_member_col = None
        for col in df.columns:
            if 'Unit/Member' in col or 'Member Name' in col:
                unit_member_col = col
                break

        if not unit_member_col:
            raise MemberDataError("Could not find Unit/Member column")

        # Track current member as we iterate through rows
        current_member: Optional[MemberRecord] = None
        current_competency_type: Optional[str] = None
        current_competency_status: Optional[str] = None

        for idx, row in df.iterrows():
            # Check if this row starts a new member
            member_info = self._parse_member_info(row.get(unit_member_col))
            if member_info:
                unit_number, last_name, first_name, member_id = member_info

                # Create or get member record
                if member_id not in self.members:
                    self.members[member_id] = MemberRecord(
                        unit_number=unit_number,
                        last_name=last_name,
                        first_name=first_name,
                        member_id=member_id,
                    )
                current_member = self.members[member_id]

            # Skip rows without a current member
            if current_member is None:
                continue

            # Update competency type/status if present in this row
            competency_type_col = None
            for col in df.columns:
                if 'Competency Type' in col:
                    competency_type_col = col
                    break

            if competency_type_col and pd.notna(row.get(competency_type_col)):
                current_competency_type = str(row.get(competency_type_col))

            competency_status = row.get('Competency Status')
            if pd.notna(competency_status) and str(competency_status).strip():
                # Filter out numeric values (like 339) that appear in the data
                status_str = str(competency_status).strip()
                if not status_str.isdigit():
                    current_competency_status = status_str

            # Get task info
            task_type = row.get('Task Type')
            if pd.isna(task_type) or not str(task_type).strip():
                continue

            # Parse dates and numeric values
            task_next_due = self._parse_date(row.get('Task Next Due'))
            task_last_completed = self._parse_date(row.get('Task Last Completed'))

            cycle_req = row.get('Cycle Requirement')
            cycle_requirement = float(cycle_req) if pd.notna(cycle_req) else None

            currency = row.get('Currency Units')
            currency_units = float(currency) if pd.notna(currency) else None

            # Create task record
            task = TaskRecord(
                competency_type=current_competency_type or 'Unknown',
                competency_status=current_competency_status or 'Unknown',
                task_type=str(task_type),
                task_next_due=task_next_due,
                task_last_completed=task_last_completed,
                cycle_requirement=cycle_requirement,
                currency_units=currency_units,
            )
            current_member.add_task(task)

        logger.info(f"Loaded {len(self.members)} members with tasks")

        # Load email data if provided
        if self.email_csv and self.email_csv.exists():
            self._load_emails()

        return self.members

    def _load_emails(self) -> None:
        """Load email addresses from CSV and match to members."""
        if not self.email_csv or not self.email_csv.exists():
            return

        email_df = pd.read_csv(self.email_csv)

        # Clean up Member ID column
        if 'Member ID' in email_df.columns:
            email_df['Member ID'] = email_df['Member ID'].astype(str).str.strip()

        # Match emails to members
        for member_id, member in self.members.items():
            matches = email_df[email_df['Member ID'] == member_id]
            if not matches.empty:
                email = matches.iloc[0].get('Email')
                if pd.notna(email):
                    member.email = str(email).strip()

        # Log email match stats
        with_email = sum(1 for m in self.members.values() if m.email)
        logger.info(f"Matched emails for {with_email}/{len(self.members)} members")

    def get_members_with_email(self) -> List[MemberRecord]:
        """Get all members that have an email address."""
        return [m for m in self.members.values() if m.email]

    def get_all_members(self) -> List[MemberRecord]:
        """Get all members."""
        return list(self.members.values())


def competency_sort_key(comp: Dict) -> Tuple:
    """Get sort key for ordering competencies.

    Sort order:
    1. AUXCT - Core Training first
    2. Trainee competencies alphabetically
    3. Certified competencies alphabetically
    4. REYR/REWK competencies alphabetically

    Args:
        comp: Competency dict with 'competency_type', 'is_auxct', 'status_bucket'

    Returns:
        Tuple for sorting
    """
    comp_type = comp.get('competency_type', '')
    is_auxct = comp.get('is_auxct')
    if is_auxct is None:
        is_auxct = 'AUXCT' in comp_type.upper() or 'CORE TRAINING' in comp_type.upper()

    bucket_order = {'trainee': 1, 'certified': 2, 'lapsed': 3}
    status_bucket = comp.get('status_bucket', 'certified')
    status_order = bucket_order.get(status_bucket, 99)

    return (0 if is_auxct else 1, status_order, comp_type.upper())


def load_competency_summary(competencies_xlsx: str) -> Dict[str, List[Dict]]:
    """Load competency data from Unit Summary xlsx.

    Args:
        competencies_xlsx: Path to the Unit Summary - Competencies xlsx file

    Returns:
        Dict mapping member_id -> list of competency dicts with:
            - competency_type, competency_status, status_date
    """
    members = {}
    xlsx_path = Path(competencies_xlsx)

    if not xlsx_path.exists():
        logger.warning(f"Competencies xlsx not found: {competencies_xlsx}")
        return members

    try:
        # Read xlsx and find header row
        df_raw = pd.read_excel(xlsx_path, header=None)

        # Find header row containing 'Original Certification Date'
        header_row = None
        for idx in range(min(30, len(df_raw))):
            row_values = df_raw.iloc[idx].astype(str).tolist()
            for val in row_values:
                if 'Original Certification' in val or 'Certification Date' in val:
                    header_row = idx
                    break
            if header_row is not None:
                break

        if header_row is None:
            logger.warning("Could not find header row in competencies xlsx")
            return members

        # Re-read with correct header
        df = pd.read_excel(xlsx_path, header=header_row)
        df.columns = [re.sub(r'\s*[↑↓]\s*', '', str(col)).strip() for col in df.columns]

        # Find the relevant columns
        unit_member_col = None
        for col in df.columns:
            if 'Unit/Member' in col:
                unit_member_col = col
                break

        cert_date_col = None
        for col in df.columns:
            if 'Original Certification' in col or 'Certification Date' in col:
                cert_date_col = col
                break

        if not unit_member_col or not cert_date_col:
            logger.warning("Missing required columns in competencies xlsx")
            return members

        # Parse the data
        current_member_id = None
        for idx, row in df.iterrows():
            # Check for new member
            unit_member = str(row.get(unit_member_col, ''))
            if 'Unit:' in unit_member:
                match = re.search(r'(\d{7})$', unit_member)
                if match:
                    current_member_id = match.group(1)
                    if current_member_id not in members:
                        members[current_member_id] = []

            if current_member_id is None:
                continue

            # Skip subtotal rows and invalid entries
            comp_type = row.get('Competency Type')
            if pd.isna(comp_type):
                continue
            comp_type = str(comp_type).strip()
            if comp_type.lower() in ['subtotal', 'count', ''] or comp_type.isdigit():
                continue

            status = row.get('Status', '')
            cert_date = row.get(cert_date_col)

            # Format date
            date_str = None
            if pd.notna(cert_date):
                if isinstance(cert_date, str):
                    date_str = cert_date
                else:
                    try:
                        date_str = pd.to_datetime(cert_date).strftime('%m/%d/%Y')
                    except Exception:
                        date_str = str(cert_date)

            members[current_member_id].append({
                'competency_type': comp_type,
                'competency_status': str(status) if pd.notna(status) else 'Unknown',
                'status_date': date_str,
            })

        total_comps = sum(len(v) for v in members.values())
        logger.info(f"Loaded {total_comps} competencies for {len(members)} members from summary")

    except Exception as e:
        logger.warning(f"Could not load competency data: {e}")

    return members


def get_status_bucket(status: str) -> str:
    """Determine status bucket from competency status string."""
    status_lower = status.lower() if status else ''
    if 'trainee' in status_lower or 'not certified' in status_lower:
        return 'trainee'
    elif 'reyr' in status_lower or 'rewk' in status_lower:
        return 'lapsed'
    return 'certified'


def merge_competency_data(
    task_competencies: List[Dict],
    summary_competencies: List[Dict],
) -> List[Dict]:
    """Merge task competencies with summary competencies.

    Summary competencies provide the complete list with status dates.
    Task competencies provide the task details for competencies with tasks.

    Args:
        task_competencies: List of competency dicts from to_template_context()
        summary_competencies: List of competency dicts from load_competency_summary()

    Returns:
        Merged and sorted list of competency dicts
    """
    # Index task competencies by type for quick lookup
    task_comps = {c['competency_type']: c for c in task_competencies}

    merged = []
    for comp_info in summary_competencies:
        comp_type = comp_info['competency_type']

        if comp_type in task_comps:
            # Competency has tasks - use task data but add status_date
            merged_comp = task_comps[comp_type].copy()
            merged_comp['status_date'] = comp_info['status_date']
        else:
            # Competency has no tasks - create entry from summary
            status = comp_info['competency_status']
            status_bucket = get_status_bucket(status)
            is_auxct = 'AUXCT' in comp_type.upper() or 'CORE TRAINING' in comp_type.upper()

            merged_comp = {
                'competency_type': comp_type,
                'competency_status': status,
                'status_bucket': status_bucket,
                'status_date': comp_info['status_date'],
                'is_auxct': is_auxct,
                'is_lapsed': status_bucket == 'lapsed',
                'overall_urgency': 'green',  # No tasks = green
                'tasks': [],
                'tasks_red': [],
                'tasks_yellow': [],
                'tasks_green': [],
                'has_red': False,
                'has_yellow': False,
                'has_green': False,
            }
        merged.append(merged_comp)

    # Sort using the standard sort key
    merged.sort(key=competency_sort_key)
    return merged
