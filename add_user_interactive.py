#!/usr/bin/env python3
"""Interactive CLI script to add users to the tracker system.

This script provides a user-friendly interface for adding people to the database
with interactive prompts and validation.
"""

import getpass
import platform
import re
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from tracker.db.connect import get_session
from tracker.tables.people_table import Person_Usernames

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


class UserValidationModel(BaseModel):
    """Pydantic model for validating user input before database insertion."""

    full_name: str
    preferred_name: str | None = None
    computer_user: str | None = None
    github_user: str | None = None
    jira_user: str | None = None
    gcal_user: EmailStr | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name format."""
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be empty")
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Full name must be less than 100 characters")
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Full name can only contain letters, spaces, hyphens, apostrophes, and dots")
        return v

    @field_validator("preferred_name")
    @classmethod
    def validate_preferred_name(cls, v: str | None) -> str | None:
        """Validate preferred name format."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 50:
            raise ValueError("Preferred name must be less than 50 characters")
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Preferred name can only contain letters, spaces, hyphens, apostrophes, and dots")
        return v

    @field_validator("computer_user")
    @classmethod
    def validate_computer_user(cls, v: str | None) -> str | None:
        """Validate computer username format."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 32:
            raise ValueError("Computer username must be less than 32 characters")
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("Computer username can only contain letters, numbers, underscores, hyphens, and dots")
        return v.lower()  # Normalize to lowercase

    @field_validator("github_user")
    @classmethod
    def validate_github_user(cls, v: str | None) -> str | None:
        """Validate GitHub username format."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 39:  # GitHub's max username length
            raise ValueError("GitHub username must be less than 39 characters")
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("GitHub username can only contain letters, numbers, and hyphens")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("GitHub username cannot start or end with a hyphen")
        return v

    @field_validator("jira_user")
    @classmethod
    def validate_jira_user(cls, v: str | None) -> str | None:
        """Validate Jira username format."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 50:
            raise ValueError("Jira username must be less than 50 characters")
        # Jira usernames are typically email-like or simple alphanumeric
        if not re.match(r"^[a-zA-Z0-9._@\-]+$", v):
            raise ValueError("Jira username can only contain letters, numbers, dots, underscores, @ symbols, and hyphens")
        return v


def print_header():
    """Print the application header."""
    print("=" * 60)
    print("🚀 Tracker User Management - Add New User")
    print("=" * 60)
    print()


def print_instructions():
    """Print helpful instructions."""
    print("📝 Instructions:")
    print("• Press Enter to skip optional fields")
    print("• Type 'quit' or 'exit' at any time to cancel")
    print("• All usernames must be unique in the system")
    print()


def get_input(prompt: str, required: bool = False, field_type: str = "text", field_name: str = "") -> Optional[str]:
    """Get user input with validation and exit handling.

    Args:
        prompt: The prompt message to display
        required: Whether the field is required
        field_type: Type of field for validation hints
        field_name: Field name for validation error context

    Returns:
        User input or None if skipped
    """
    while True:
        try:
            if required:
                value = input(f"✅ {prompt} (required): ").strip()
            else:
                value = input(f"📝 {prompt} (optional, press Enter to skip): ").strip()

            # Handle exit commands
            if value.lower() in ["quit", "exit", "q"]:
                print("\n❌ Operation cancelled by user")
                sys.exit(0)

            # Handle empty input
            if not value:
                if required:
                    print("⚠️  This field is required. Please enter a value.")
                    continue
                return None

            # Apply Pydantic validation if field_name is provided
            if field_name and value:
                try:
                    # Create a temporary model to validate just this field
                    temp_data = {field_name: value}
                    # Add required full_name if we're validating other fields
                    if field_name != "full_name":
                        temp_data["full_name"] = "Temp Name"
                    UserValidationModel(**temp_data)
                except ValidationError as e:
                    for error in e.errors():
                        if error["loc"][0] == field_name:
                            error_msg = error["msg"]
                            print(f"❌ Validation error: {error_msg}")
                            print("   Please try again with a valid value.")
                            break
                    continue

            return value

        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled by user")
            sys.exit(0)
        except EOFError:
            print("\n\n❌ Operation cancelled")
            sys.exit(0)


def show_existing_users():
    """Show existing users in the system."""
    try:
        with get_session() as session:
            users = session.exec(select(Person_Usernames)).all()

        if not users:
            print("📋 No users currently in the system")
            return

        print("📋 Current users in the system:")
        print("-" * 40)
        for user in users:
            preferred = f" ({user.preferred_name})" if user.preferred_name else ""
            computer = f" [Computer: {user.computer_user}]" if user.computer_user else ""
            print(f"• {user.full_name}{preferred}{computer}")
        print()

    except Exception as e:
        logger.error(f"Failed to fetch existing users: {e}")
        print("⚠️  Could not fetch existing users")


def collect_user_data() -> dict:
    """Collect user data through interactive prompts.

    Returns:
        Dictionary containing user data
    """
    print("Please provide the following information:")
    print()

    data = {}

    # Required fields
    data["full_name"] = get_input("Full legal name (e.g., 'John Michael Smith')", required=True, field_name="full_name")

    # Optional fields
    data["preferred_name"] = get_input("Preferred name/nickname (e.g., 'Mike')", field_name="preferred_name")

    # Handle computer username with smart default and system info
    current_user = getpass.getuser()
    system_name = platform.node()
    system_os = platform.system()

    print("💻 Computer Information:")
    print(f"   System: {system_name} ({system_os})")
    print(f"   Current user: {current_user}")
    print()
    computer_choice = input(f"   Use '{current_user}' as computer username? (Y/n) or enter different: ").strip()

    if computer_choice.lower() in ["", "y", "yes"]:
        # Validate the current user before using it
        try:
            temp_data = {"full_name": "Temp Name", "computer_user": current_user}
            validated_model = UserValidationModel(**temp_data)
            data["computer_user"] = validated_model.computer_user
            print(f"   ✅ Using: {validated_model.computer_user}")
        except ValidationError as e:
            for error in e.errors():
                if error["loc"][0] == "computer_user":
                    print(f"⚠️ Current username '{current_user}' is invalid: {error['msg']}")
                    data["computer_user"] = get_input("Enter valid computer username", field_name="computer_user")
                    break
    elif computer_choice.lower() in ["n", "no"]:
        data["computer_user"] = get_input("Enter custom computer username", field_name="computer_user")
    elif computer_choice.lower() in ["quit", "exit", "q"]:
        print("\n❌ Operation cancelled by user")
        sys.exit(0)
    else:
        # User entered a custom username directly - validate it
        try:
            # Validate the directly entered username
            temp_data = {"full_name": "Temp Name", "computer_user": computer_choice}
            UserValidationModel(**temp_data)
            data["computer_user"] = computer_choice
            print(f"   ✅ Using: {computer_choice}")
        except ValidationError as e:
            for error in e.errors():
                if error["loc"][0] == "computer_user":
                    print(f"❌ Invalid computer username: {error['msg']}")
                    data["computer_user"] = get_input("Enter valid computer username", field_name="computer_user")
                    break
    print()

    data["github_user"] = get_input("GitHub username (e.g., 'johnsmith')", field_name="github_user")

    data["jira_user"] = get_input("Jira username", field_name="jira_user")

    data["gcal_user"] = get_input("Google Calendar email (e.g., 'john@company.com')", field_name="gcal_user")

    # Remove None values
    return {k: v for k, v in data.items() if v is not None}


def confirm_user_data(data: dict) -> bool:
    """Display user data for confirmation.

    Args:
        data: User data dictionary

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "=" * 50)
    print("📋 Please review the user information:")
    print("=" * 50)

    print(f"Full Name:        {data.get('full_name', 'Not provided')}")
    print(f"Preferred Name:   {data.get('preferred_name', 'Not provided')}")

    # Show computer user with system context
    computer_user = data.get("computer_user", "Not provided")
    current_user = getpass.getuser()
    if computer_user == current_user:
        print(f"Computer User:    {computer_user} ✅ (matches current system user)")
    else:
        print(f"Computer User:    {computer_user} ⚠️  (different from current: {current_user})")

    print(f"GitHub User:      {data.get('github_user', 'Not provided')}")
    print(f"Jira User:        {data.get('jira_user', 'Not provided')}")
    print(f"Google Cal Email: {data.get('gcal_user', 'Not provided')}")

    print("-" * 50)

    while True:
        try:
            confirm = input("✅ Is this information correct? (y/N): ").strip().lower()
            if confirm in ["y", "yes"]:
                return True
            elif confirm in ["n", "no", ""]:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no")
        except (KeyboardInterrupt, EOFError):
            return False


def save_user(data: dict) -> bool:
    """Save user to database.

    Args:
        data: User data dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        # Final validation using Pydantic model
        try:
            validated_user = UserValidationModel(**data)
            # Convert back to dict with validated values
            validated_data = validated_user.model_dump(exclude_none=True)
        except ValidationError as e:
            print("\n❌ Final validation failed:")
            for error in e.errors():
                field = error["loc"][0]
                message = error["msg"]
                print(f"   • {field}: {message}")
            return False

        person = Person_Usernames(**validated_data)

        with get_session() as session:
            session.add(person)
            session.commit()
            session.refresh(person)

        print("\n✅ Successfully added user!")
        print(f"   ID: {person.person_id}")
        print(f"   Name: {person.full_name}")
        if person.preferred_name:
            print(f"   Preferred: {person.preferred_name}")
        if person.computer_user:
            print(f"   Computer: {person.computer_user}")

        return True

    except IntegrityError as e:
        print("\n❌ Failed to add user - Username already exists!")
        print("   Please check the following usernames are unique:")
        if data.get("github_user"):
            print(f"   • GitHub: {data['github_user']}")
        if data.get("jira_user"):
            print(f"   • Jira: {data['jira_user']}")
        if data.get("gcal_user"):
            print(f"   • Google Calendar: {data['gcal_user']}")
        if data.get("computer_user"):
            print(f"   • Computer: {data['computer_user']}")
        logger.error(f"Integrity error adding user: {e}")
        return False

    except Exception as e:
        print(f"\n❌ Failed to add user: {e}")
        logger.error(f"Error adding user: {e}")
        return False


def main():
    """Main application function."""
    try:
        print_header()
        print_instructions()

        # Show existing users
        show_list = input("📋 Show existing users? (y/N): ").strip().lower()
        if show_list in ["y", "yes"]:
            print()
            show_existing_users()
            print()

        # Collect user data
        while True:
            print("🚀 Adding new user...")
            print()

            user_data = collect_user_data()

            if not user_data.get("full_name"):
                print("❌ Full name is required!")
                continue

            # Confirm data
            if confirm_user_data(user_data):
                # Save user
                if save_user(user_data):
                    break
                else:
                    retry = input("\n🔄 Try again with different information? (y/N): ").strip().lower()
                    if retry not in ["y", "yes"]:
                        break
                    print()
            else:
                retry = input("\n🔄 Re-enter user information? (y/N): ").strip().lower()
                if retry not in ["y", "yes"]:
                    print("❌ Operation cancelled")
                    break
                print()

        # Ask if they want to add another user
        while True:
            another = input("\n➕ Add another user? (y/N): ").strip().lower()
            if another in ["y", "yes"]:
                print("\n" + "=" * 60)
                main()  # Recursive call for another user
                break
            elif another in ["n", "no", ""]:
                break
            else:
                print("Please enter 'y' for yes or 'n' for no")

        print("\n🎉 User management completed!")

    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
