"""Database operations for member records."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional


class MemberDatabase:
    """Manages member records from CSV files with optional join on Member ID."""

    def __init__(self, training_csv: str, email_csv: Optional[str] = None):
        """Initialize database with CSV file paths.

        Args:
            training_csv: Path to CSV file containing training/competency records
            email_csv: Optional path to CSV file containing member emails
        """
        self.training_csv = Path(training_csv)
        self.email_csv = Path(email_csv) if email_csv else None
        self.members_df: Optional[pd.DataFrame] = None

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

        # If email CSV provided, join the tables
        if self.email_csv and self.email_csv.exists():
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
