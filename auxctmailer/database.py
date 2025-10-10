"""Database operations for member records."""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional


class MemberDatabase:
    """Manages member records from CSV files with optional join on Member ID."""

    def __init__(self, training_csv: str, email_csv: Optional[str] = None, units_csv: Optional[str] = None):
        """Initialize database with CSV file paths.

        Args:
            training_csv: Path to CSV file containing training/competency records
            email_csv: Optional path to CSV file containing member emails
            units_csv: Optional path to CSV file containing unit details
        """
        self.training_csv = Path(training_csv)
        self.email_csv = Path(email_csv) if email_csv else None
        self.units_csv = Path(units_csv) if units_csv else None
        self.members_df: Optional[pd.DataFrame] = None
        self.units_df: Optional[pd.DataFrame] = None

    def _extract_unit_number(self, unit_field: str) -> Optional[str]:
        """Extract unit number from Unit/Member/Competency/Status field.

        Args:
            unit_field: String like "Unit: 0131102 | GAFFNEY. PAUL 5008388 | AUXCT - CORE TRAINING (Certified)"

        Returns:
            Unit number string (e.g., "0131102") or None if not found
        """
        if pd.isna(unit_field) or not isinstance(unit_field, str):
            return None

        # Extract unit number from "Unit: 0131102 | ..." format
        match = re.search(r'Unit:\s*(\d+)', unit_field, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _prettify_unit_name(self, raw_name: str) -> str:
        """Convert raw unit name to pretty format.

        Converts to Title Case and ensures it ends with "Flotilla".

        Args:
            raw_name: Raw unit name from CSV (e.g., "WOODS HOLE FLOTILLA", "CASCO BAY", "BANGOR FLOT")

        Returns:
            Pretty unit name (e.g., "Woods Hole Flotilla", "Casco Bay Flotilla", "Bangor Flotilla")
        """
        if pd.isna(raw_name) or not isinstance(raw_name, str):
            return None

        # Convert to title case
        pretty = raw_name.strip().title()

        # Remove common flotilla abbreviations from the end
        flotilla_abbrevs = [' Flotilla', ' Flot', ' Flot.', ' Flt', ' Flt.']
        for abbrev in flotilla_abbrevs:
            if pretty.endswith(abbrev):
                # Remove the abbreviation (we'll add "Flotilla" back)
                pretty = pretty[:-len(abbrev)].strip()
                break

        # Always ensure it ends with "Flotilla"
        if not pretty.endswith('Flotilla'):
            pretty = pretty + ' Flotilla'

        return pretty

    def _prettify_unit_number(self, unit_number: str) -> Optional[str]:
        """Convert unit number to pretty format DDD-VV-UU.

        Args:
            unit_number: 7-digit unit number string (e.g., "0131102")

        Returns:
            Pretty unit number (e.g., "013-11-02") or None if invalid format
        """
        if pd.isna(unit_number) or not isinstance(unit_number, str):
            return None

        # Strip whitespace and ensure it's exactly 7 digits
        unit_number = unit_number.strip()
        if len(unit_number) != 7 or not unit_number.isdigit():
            return None

        # Format as DDD-VV-UU
        district = unit_number[0:3]  # First 3 digits
        division = unit_number[3:5]  # Digits 4-5
        unit = unit_number[5:7]      # Digits 6-7

        return f"{district}-{division}-{unit}"

    def _prettify_fso_name(self, name: str) -> Optional[str]:
        """Convert FSO name to Title Case.

        Args:
            name: FSO name in ALL CAPS (e.g., "PAUL JAMES GAFFNEY")

        Returns:
            Pretty FSO name in Title Case (e.g., "Paul James Gaffney")
        """
        if pd.isna(name) or not isinstance(name, str):
            return None

        # Convert to title case
        return name.strip().title()

    def _create_fso_display_name(self, name: str) -> Optional[str]:
        """Create simplified FSO display name (First Last only).

        Args:
            name: FSO full name (e.g., "PAUL JAMES GAFFNEY" or "DANIEL J FARREN JR.")

        Returns:
            Display name with only first and last name (e.g., "Paul Gaffney", "Daniel Farren")
        """
        if pd.isna(name) or not isinstance(name, str):
            return None

        # Parse the name
        name_parts = name.strip().split()
        if len(name_parts) < 2:
            return None

        # Common suffixes to ignore
        suffixes = ['JR', 'JR.', 'SR', 'SR.', 'II', 'III', 'IV', 'V']

        # Remove suffix from end if present
        if name_parts[-1].upper().rstrip('.') in suffixes:
            name_parts = name_parts[:-1]

        if len(name_parts) < 2:
            return None

        # First name is always first part
        first_name = name_parts[0]

        # Last name is the last part (after removing suffix)
        last_name = name_parts[-1]

        # Return "First Last" in Title Case
        return f"{first_name.title()} {last_name.title()}"

    def _lookup_fso_email(self, fso_name: str, email_df: pd.DataFrame) -> Optional[str]:
        """Look up FSO email address by matching name in email database.

        Args:
            fso_name: FSO full name (e.g., "PAUL JAMES GAFFNEY" or "DANIEL J FARREN JR.")
            email_df: DataFrame with member email information

        Returns:
            Email address if found, None otherwise
        """
        if pd.isna(fso_name) or not isinstance(fso_name, str):
            return None

        # Parse the FSO name (format: "FIRST MIDDLE LAST" or "FIRST MIDDLE LAST SUFFIX")
        name_parts = fso_name.strip().split()
        if len(name_parts) < 2:
            return None

        # Common suffixes to ignore
        suffixes = ['JR', 'JR.', 'SR', 'SR.', 'II', 'III', 'IV', 'V']

        # Remove suffix from end if present
        if name_parts[-1].upper().rstrip('.') in suffixes:
            name_parts = name_parts[:-1]

        if len(name_parts) < 2:
            return None

        # First name is always first part
        first_name = name_parts[0]

        # Last name is the last part (after removing suffix)
        last_name = name_parts[-1]

        # Try to find matching member in email database
        # Match on Last Name and First Name (case-insensitive)
        matches = email_df[
            (email_df['Last Name'].str.upper() == last_name.upper()) &
            (email_df['First Name'].str.upper() == first_name.upper())
        ]

        if not matches.empty:
            email = matches.iloc[0]['Email']
            if pd.notna(email):
                return str(email).strip()

        return None

    def load(self) -> pd.DataFrame:
        """Load and join member records from CSV files.

        Returns:
            DataFrame containing joined member records

        Raises:
            FileNotFoundError: If CSV files don't exist
        """
        if not self.training_csv.exists():
            raise FileNotFoundError(f"Training database not found: {self.training_csv}")

        # Load training data
        training_df = pd.read_csv(self.training_csv)

        # Clean up Member # column (strip whitespace)
        if 'Member #' in training_df.columns:
            training_df['Member #'] = training_df['Member #'].astype(str).str.strip()

        # Extract Unit Number from Unit/Member/Competency/Status field
        # Handle various column name variations (with/without arrow, with/without trailing spaces)
        unit_field_col = None
        for col in training_df.columns:
            if 'Unit/Member/Competency/Status' in col:
                unit_field_col = col
                break

        if unit_field_col:
            training_df['Unit Number'] = training_df[unit_field_col].apply(self._extract_unit_number)

        # Create pretty version of unit number (DDD-VV-UU format)
        if 'Unit Number' in training_df.columns:
            training_df['Unit Number Pretty'] = training_df['Unit Number'].apply(self._prettify_unit_number)

        # Load email data first (needed for FSO email lookup)
        email_df = None
        if self.email_csv and self.email_csv.exists():
            email_df = pd.read_csv(self.email_csv)
            # Clean up Member ID column
            if 'Member ID' in email_df.columns:
                email_df['Member ID'] = email_df['Member ID'].astype(str).str.strip()

        # Load units data if provided
        if self.units_csv and self.units_csv.exists():
            # Read with dtype=str to prevent numeric conversion issues
            self.units_df = pd.read_csv(self.units_csv, dtype={'Unit Number': str})

            # Clean up Unit Number column in units CSV
            # Replace 'nan' strings (from empty values) with actual NaN
            if 'Unit Number' in self.units_df.columns:
                self.units_df['Unit Number'] = self.units_df['Unit Number'].str.strip()
                self.units_df.loc[self.units_df['Unit Number'] == 'nan', 'Unit Number'] = pd.NA

            # Create pretty version of unit names
            if 'Unit Name' in self.units_df.columns:
                self.units_df['Unit Name Pretty'] = self.units_df['Unit Name'].apply(self._prettify_unit_name)

            # Create pretty versions of FSO names, display names, and look up emails
            if 'FSO-IS' in self.units_df.columns:
                self.units_df['FSO-IS Pretty'] = self.units_df['FSO-IS'].apply(self._prettify_fso_name)
                self.units_df['FSO-IS Display'] = self.units_df['FSO-IS'].apply(self._create_fso_display_name)
                if email_df is not None:
                    self.units_df['FSO-IS Email'] = self.units_df['FSO-IS'].apply(
                        lambda name: self._lookup_fso_email(name, email_df)
                    )
            if 'FSO-MT' in self.units_df.columns:
                self.units_df['FSO-MT Pretty'] = self.units_df['FSO-MT'].apply(self._prettify_fso_name)
                self.units_df['FSO-MT Display'] = self.units_df['FSO-MT'].apply(self._create_fso_display_name)
                if email_df is not None:
                    self.units_df['FSO-MT Email'] = self.units_df['FSO-MT'].apply(
                        lambda name: self._lookup_fso_email(name, email_df)
                    )

            # Join units data to get unit names (both raw and pretty) and FSO contacts
            if 'Unit Number' in training_df.columns:
                # Select columns that exist in units_df
                cols_to_merge = ['Unit Number', 'Unit Name', 'Unit Name Pretty']
                if 'FSO-IS' in self.units_df.columns:
                    cols_to_merge.append('FSO-IS')
                    cols_to_merge.append('FSO-IS Pretty')
                    if 'FSO-IS Display' in self.units_df.columns:
                        cols_to_merge.append('FSO-IS Display')
                    if 'FSO-IS Email' in self.units_df.columns:
                        cols_to_merge.append('FSO-IS Email')
                if 'FSO-MT' in self.units_df.columns:
                    cols_to_merge.append('FSO-MT')
                    cols_to_merge.append('FSO-MT Pretty')
                    if 'FSO-MT Display' in self.units_df.columns:
                        cols_to_merge.append('FSO-MT Display')
                    if 'FSO-MT Email' in self.units_df.columns:
                        cols_to_merge.append('FSO-MT Email')

                training_df = training_df.merge(
                    self.units_df[cols_to_merge],
                    on='Unit Number',
                    how='left'
                )

        # If email CSV provided, join the tables (reuse email_df if already loaded)
        if self.email_csv and self.email_csv.exists():
            if email_df is None:
                email_df = pd.read_csv(self.email_csv)
                # Clean up Member ID column
                if 'Member ID' in email_df.columns:
                    email_df['Member ID'] = email_df['Member ID'].astype(str).str.strip()

            # Join on Member # / Member ID
            self.members_df = training_df.merge(
                email_df,
                left_on='Member #',
                right_on='Member ID',
                how='left'
            )
        else:
            self.members_df = training_df

        return self.members_df

    def get_all_members(self) -> List[Dict]:
        """Get all member records as list of dictionaries.

        Returns:
            List of member record dictionaries
        """
        if self.members_df is None:
            self.load()

        return self.members_df.to_dict('records')

    def filter_members(self, **criteria) -> List[Dict]:
        """Filter members based on column criteria.

        Args:
            **criteria: Column name and value pairs to filter by

        Returns:
            List of filtered member record dictionaries

        Example:
            filter_members(status='active', region='Northeast')
        """
        if self.members_df is None:
            self.load()

        filtered_df = self.members_df

        for column, value in criteria.items():
            if column in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[column] == value]

        return filtered_df.to_dict('records')

    def get_member_by_id(self, member_id: str) -> Optional[Dict]:
        """Get a single member by ID.

        Args:
            member_id: Member identifier

        Returns:
            Member record dictionary or None if not found
        """
        if self.members_df is None:
            self.load()

        # Assumes 'id' column exists - adjust as needed
        matches = self.members_df[self.members_df['id'] == member_id]

        if matches.empty:
            return None

        return matches.iloc[0].to_dict()
