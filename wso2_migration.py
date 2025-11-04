#!/usr/bin/env python3
"""
Corrected WSO2 API Manager deployment.toml Migration Tool

This version correctly handles properties within sections, ensuring:
properties."moesifKey" stays within [apim.analytics] section
"""

import argparse
import sys
import shutil
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import toml


# Configuration constants
DEFAULT_IGNORE_PATTERNS = {
    'server.hostname': 'localhost',
    'super_admin.username': 'admin',
    'super_admin.password': 'admin',
}

REQUIRED_SECTIONS = ['server', 'super_admin']
DEFAULT_CONFIG_FILE = 'custom_migration_rules.json'


class CorrectedTomlMigrator:
    """Corrected migrator that keeps properties within their parent sections."""

    def __init__(self, source_file: str, target_file: str, output_file: str = None, config_file: str = None):
        self.source_file = Path(source_file)
        self.target_file = Path(target_file)
        self.output_file = Path(output_file) if output_file else self.target_file.with_suffix('.migrated.toml')
        self.applied_changes = []
        self.config = self._load_config(config_file or DEFAULT_CONFIG_FILE)
        self.ordering_rules = self.config.get('section_ordering', {})
        self.array_tables = set(self.ordering_rules.get('array_tables', []))
        self.ignore_patterns = self._parse_ignore_patterns(self.config.get('ignore_patterns', []))

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"Warning: Config file {config_file} not found, using defaults")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading config file {config_file}: {e}")
            return {}

    def _parse_ignore_patterns(self, patterns: List[str]) -> Dict[str, str]:
        """
        Parse ignore patterns from config file format to internal format.

        Converts from:
            ["server.hostname:localhost", "super_admin.username:admin"]
        To:
            {"server.hostname": "localhost", "super_admin.username": "admin"}

        Supports wildcards like "keystore.*.alias:wso2carbon"
        """
        parsed = {}
        for pattern in patterns:
            if ':' in pattern:
                key, value = pattern.split(':', 1)
                parsed[key] = value
            else:
                print(f"Warning: Invalid ignore pattern '{pattern}' - expected 'key:value' format")

        # If no patterns in config, use defaults
        if not parsed:
            return DEFAULT_IGNORE_PATTERNS.copy()

        return parsed

    def _matches_ignore_pattern(self, full_key: str, value: Any) -> bool:
        """
        Check if a key-value pair matches any ignore pattern.

        Supports wildcards in patterns:
        - "keystore.*.alias:wso2carbon" matches "keystore.tls.alias:wso2carbon"
        - "database.*.type:h2" matches "database.shared_db.type:h2"
        """
        value_str = str(value)

        for pattern_key, pattern_value in self.ignore_patterns.items():
            # Check if value matches
            if value_str != pattern_value:
                continue

            # Check if key matches (with wildcard support)
            if '*' in pattern_key:
                # Convert pattern to regex
                pattern_regex = pattern_key.replace('.', r'\.').replace('*', r'[^.]+')
                if re.match(f'^{pattern_regex}$', full_key):
                    return True
            elif full_key == pattern_key:
                return True

        return False

    def parse_toml_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse TOML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            sys.exit(1)

    def read_file_as_lines(self, file_path: Path) -> List[str]:
        """Read file as list of lines."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def extract_section_with_properties(self, lines: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract sections with their properties, including quoted properties."""
        sections = {}
        current_section = None

        for line in lines:
            stripped = line.strip()

            # Section headers
            if stripped.startswith('[') and stripped.endswith(']') and not stripped.startswith('#'):
                is_array_table = False
                if stripped.startswith('[[') and stripped.endswith(']]'):
                    current_section = stripped[2:-2].strip()
                    is_array_table = True
                else:
                    current_section = stripped[1:-1].strip()
                    # Check config to see if this should be an array table
                    is_array_table = current_section in self.array_tables

                if current_section not in sections:
                    sections[current_section] = {'regular_props': {}, 'quoted_props': [], 'is_array_table': is_array_table}

            # Key-value pairs
            elif '=' in stripped and not stripped.startswith('#') and current_section:
                key_part, value_part = stripped.split('=', 1)
                key = key_part.strip()
                value = value_part.strip()

                # Check if this is a quoted property
                if key.startswith('properties."') and key.endswith('"'):
                    # This is a quoted property like properties."moesifKey"
                    sections[current_section]['quoted_props'].append({
                        'line': stripped,
                        'key': key,
                        'value': self.clean_toml_value(value)
                    })
                else:
                    # Regular property
                    sections[current_section]['regular_props'][key] = self.clean_toml_value(value)

        return sections

    def clean_toml_value(self, value_str: str) -> Any:
        """Clean and parse a TOML value string."""
        value_str = value_str.strip()

        # Remove trailing comments
        if '#' in value_str:
            value_str = value_str.split('#')[0].strip()

        # Handle arrays
        if value_str.startswith('[') and value_str.endswith(']'):
            try:
                test_toml = f"test = {value_str}"
                parsed = toml.loads(test_toml)
                return parsed['test']
            except (toml.TomlDecodeError, ValueError, KeyError):
                # If parsing fails, return as string
                return value_str

        # Handle quoted strings
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]

        # Handle booleans
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False

        # Handle numbers
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        return value_str

    def find_customizations(self, source_sections: Dict[str, Dict[str, Any]],
                          target_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Find customizations by comparing source sections with target config."""
        customizations = {}
        target_flat = self.flatten_config(target_config)

        for section_name, section_data in source_sections.items():
            section_customizations = {'regular_props': {}, 'quoted_props': [], 'is_array_table': section_data.get('is_array_table', False)}

            # Check regular properties
            for key, value in section_data['regular_props'].items():
                full_key = f"{section_name}.{key}"

                # Skip values matching ignore patterns (including wildcards)
                if self._matches_ignore_pattern(full_key, value):
                    continue

                # Check if different from target
                if full_key not in target_flat or str(target_flat[full_key]) != str(value):
                    section_customizations['regular_props'][key] = value

            # Always include quoted properties (they're usually customizations)
            section_customizations['quoted_props'] = section_data['quoted_props']

            # Only include section if it has customizations
            if section_customizations['regular_props'] or section_customizations['quoted_props']:
                customizations[section_name] = section_customizations

        return customizations

    def flatten_config(self, config: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested configuration."""
        items = []
        for k, v in config.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_config(v, new_key, sep=sep).items())
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                for i, item in enumerate(v):
                    items.extend(self.flatten_config(item, f"{new_key}[{i}]", sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _extract_section_name(self, line: str, include_commented: bool = False) -> Optional[Tuple[str, bool]]:
        """Extract section name from a line, return None if not a section. Returns (name, is_array_table)."""
        stripped = line.strip()

        # Check for commented sections if requested
        if include_commented and stripped.startswith('#['):
            stripped = stripped[1:].strip()  # Remove leading #

        if not (stripped.startswith('[') and stripped.endswith(']')):
            return None

        if stripped.startswith('[[') and stripped.endswith(']]'):
            return (stripped[2:-2].strip(), True)
        else:
            return (stripped[1:-1].strip(), False)

    def _process_section_customization(self, target_lines: List[str], start_idx: int,
                                     section_name: str, section_custom: Dict[str, Any]) -> Tuple[List[str], int]:
        """Process customizations for a single section."""
        applied_regular_props = set()
        section_lines = []
        last_property_index = -1
        i = start_idx

        # Process lines within this section
        while i < len(target_lines):
            line = target_lines[i]
            stripped = line.strip()

            # Stop if we hit another section (including commented ones)
            section_info = self._extract_section_name(line, include_commented=True)
            if section_info:
                break

            # Handle key-value pairs (both active and commented)
            if '=' in stripped:
                # Check if it's a commented property
                is_commented = stripped.startswith('#')
                line_to_parse = stripped[1:].strip() if is_commented else stripped

                if '=' in line_to_parse:
                    key_part, value_part = line_to_parse.split('=', 1)
                    key = key_part.strip()

                    # Check if we have a customization for this key
                    if key in section_custom['regular_props']:
                        # Uncomment and replace with customized value
                        indent = len(line) - len(line.lstrip())
                        custom_value = section_custom['regular_props'][key]
                        formatted_value = self.format_toml_value(custom_value)
                        section_lines.append(' ' * indent + f"{key} = {formatted_value}\n")
                        self.applied_changes.append(f"{'Uncommented and modified' if is_commented else 'Modified'}: {section_name}.{key}")
                        applied_regular_props.add(key)
                        last_property_index = len(section_lines) - 1
                    else:
                        # Keep original line (commented or not)
                        section_lines.append(line)
                        if not is_commented:
                            last_property_index = len(section_lines) - 1
                else:
                    section_lines.append(line)
            else:
                # Keep comments, empty lines, etc.
                section_lines.append(line)

            i += 1

        # Add missing properties
        missing_props = self._build_missing_properties(section_name, section_custom, applied_regular_props)

        # Insert missing properties after the last property
        if missing_props:
            if last_property_index >= 0:
                for j, prop in enumerate(missing_props):
                    section_lines.insert(last_property_index + 1 + j, prop)
            else:
                section_lines = missing_props + section_lines

        return section_lines, i

    def _build_missing_properties(self, section_name: str, section_custom: Dict[str, Any],
                                applied_regular_props: set) -> List[str]:
        """Build list of missing properties to add."""
        missing_props = []

        # Add missing regular properties
        for key, value in section_custom['regular_props'].items():
            if key not in applied_regular_props:
                formatted_value = self.format_toml_value(value)
                missing_props.append(f"{key} = {formatted_value}\n")
                self.applied_changes.append(f"Added: {section_name}.{key}")

        # Add quoted properties
        for quoted_prop in section_custom['quoted_props']:
            missing_props.append(quoted_prop['line'] + '\n')
            self.applied_changes.append(f"Added: {section_name}.{quoted_prop['key']}")

        return missing_props

    def _get_target_sections(self, target_lines: List[str], include_commented: bool = False) -> set:
        """Extract all section names from target file."""
        target_sections = set()
        for line in target_lines:
            section_info = self._extract_section_name(line, include_commented=include_commented)
            if section_info:
                section_name, _ = section_info
                target_sections.add(section_name)
        return target_sections

    def _get_parent_for_section(self, section_name: str) -> Optional[str]:
        """Get the parent section for a given section based on ordering rules."""
        for rule in self.ordering_rules.get('rules', []):
            if 'child_sections' in rule:
                if section_name in rule['child_sections']:
                    return rule['parent']
        return None

    def _get_children_for_parent(self, parent_name: str) -> List[str]:
        """Get ordered list of children for a parent section."""
        for rule in self.ordering_rules.get('rules', []):
            if rule.get('parent') == parent_name and 'child_sections' in rule:
                return rule['child_sections']
        return []

    def _should_children_follow_parent(self, parent_name: str) -> bool:
        """Check if children must follow parent immediately."""
        for rule in self.ordering_rules.get('rules', []):
            if rule.get('parent') == parent_name:
                return rule.get('children_must_follow', False)
        return False

    def _add_source_only_sections(self, result_lines: List[str], customizations: Dict[str, Dict[str, Any]],
                                target_sections: set, processed_sections: set = None) -> None:
        """Add sections that exist in source but not in target."""
        if processed_sections is None:
            processed_sections = set()

        source_only_sections = set(customizations.keys()) - target_sections - processed_sections

        if source_only_sections:
            result_lines.append("\n# Additional sections from source file\n")

            # Group sections by parent for proper ordering
            sections_by_parent = {}
            orphan_sections = []

            for section_name in source_only_sections:
                parent = self._get_parent_for_section(section_name)
                if parent:
                    if parent not in sections_by_parent:
                        sections_by_parent[parent] = []
                    sections_by_parent[parent].append(section_name)
                else:
                    orphan_sections.append(section_name)

            # Add orphan sections first (those without explicit parent rules)
            for section_name in sorted(orphan_sections):
                self._add_section_to_output(result_lines, section_name, customizations[section_name])

                # Check if this section has children that should follow
                if self._should_children_follow_parent(section_name):
                    children = self._get_children_for_parent(section_name)
                    for child in children:
                        if child in source_only_sections and child in sections_by_parent.get(section_name, []):
                            self._add_section_to_output(result_lines, child, customizations[child])

    def _add_section_to_output(self, result_lines: List[str], section_name: str, section_custom: Dict[str, Any]) -> None:
        """Add a single section to the output."""
        # Add section header - check if it's an array table
        if section_custom.get('is_array_table', False):
            result_lines.append(f"\n[[{section_name}]]\n")
        else:
            result_lines.append(f"\n[{section_name}]\n")

        # Add regular properties
        for key, value in section_custom['regular_props'].items():
            formatted_value = self.format_toml_value(value)
            result_lines.append(f"{key} = {formatted_value}\n")
            self.applied_changes.append(f"Added section: {section_name}.{key}")

        # Add quoted properties
        for quoted_prop in section_custom['quoted_props']:
            result_lines.append(quoted_prop['line'] + '\n')
            self.applied_changes.append(f"Added section: {section_name}.{quoted_prop['key']}")

    def apply_customizations_to_target(self, target_lines: List[str],
                                     customizations: Dict[str, Dict[str, Any]]) -> List[str]:
        """Apply customizations to target file while preserving structure."""
        result_lines = []
        i = 0
        # Get both active and commented sections from target
        target_sections = self._get_target_sections(target_lines, include_commented=True)
        processed_sections = set()  # Track which sections we've processed

        while i < len(target_lines):
            line = target_lines[i]
            section_info = self._extract_section_name(line)

            # Also check for commented sections
            commented_section_info = self._extract_section_name(line, include_commented=True)

            if section_info:
                section_name, _ = section_info
                result_lines.append(line)

                # Check if this section has customizations
                if section_name in customizations:
                    section_custom = customizations[section_name]
                    section_lines, next_i = self._process_section_customization(
                        target_lines, i + 1, section_name, section_custom)
                    result_lines.extend(section_lines)
                    i = next_i
                    processed_sections.add(section_name)

                    # After processing a parent section, add any child sections that should follow
                    if self._should_children_follow_parent(section_name):
                        children = self._get_children_for_parent(section_name)
                        for child in children:
                            # Add child if it's in customizations but not in target
                            if child in customizations and child not in target_sections and child not in processed_sections:
                                self._add_section_to_output(result_lines, child, customizations[child])
                                processed_sections.add(child)

                    continue
            elif commented_section_info and not section_info:
                # This is a commented section
                section_name, is_array_table = commented_section_info

                # Check if we have customizations for this commented section
                if section_name in customizations and section_name not in processed_sections:
                    section_custom = customizations[section_name]

                    # Uncomment the section header
                    if section_custom.get('is_array_table', False) or is_array_table:
                        result_lines.append(f"[[{section_name}]]\n")
                    else:
                        result_lines.append(f"[{section_name}]\n")

                    self.applied_changes.append(f"Uncommented section: {section_name}")

                    # Process the section content
                    section_lines, next_i = self._process_section_customization(
                        target_lines, i + 1, section_name, section_custom)
                    result_lines.extend(section_lines)
                    i = next_i
                    processed_sections.add(section_name)

                    # After processing a parent section, add any child sections that should follow
                    if self._should_children_follow_parent(section_name):
                        children = self._get_children_for_parent(section_name)
                        for child in children:
                            if child in customizations and child not in target_sections and child not in processed_sections:
                                self._add_section_to_output(result_lines, child, customizations[child])
                                processed_sections.add(child)

                    continue
                else:
                    result_lines.append(line)
            else:
                result_lines.append(line)

            i += 1

        # Add sections that exist in source but not in target (and haven't been processed)
        self._add_source_only_sections(result_lines, customizations, target_sections, processed_sections)

        return result_lines

    def format_toml_value(self, value: Any) -> str:
        """Format a Python value as TOML string."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # Handle arrays properly without extra quotes
            if all(isinstance(item, str) for item in value):
                formatted_items = [f'"{item.replace(chr(34), chr(92) + chr(34))}"' for item in value]
                return '[' + ', '.join(formatted_items) + ']'
            else:
                # For mixed types, convert each item properly
                formatted_items = []
                for item in value:
                    if isinstance(item, str):
                        formatted_items.append(f'"{item}"')
                    elif isinstance(item, bool):
                        formatted_items.append('true' if item else 'false')
                    else:
                        formatted_items.append(str(item))
                return '[' + ', '.join(formatted_items) + ']'
        else:
            return f'"{str(value)}"'

    def migrate(self, create_backup: bool = True, dry_run: bool = False) -> bool:
        """Perform the migration."""
        print(f"Corrected migration preserving section structure: {self.source_file} → {self.target_file}")

        # Parse target config for comparison
        target_config = self.parse_toml_file(self.target_file)

        # Extract source sections with properties
        source_lines = self.read_file_as_lines(self.source_file)
        source_sections = self.extract_section_with_properties(source_lines)

        # Find customizations
        customizations = self.find_customizations(source_sections, target_config)
        print(f"Found customizations in {len(customizations)} sections")

        if dry_run:
            print("\n=== DRY RUN - Customizations to apply ===")
            for section, custom_data in customizations.items():
                print(f"\n[{section}]")
                for key, value in custom_data['regular_props'].items():
                    print(f"  {key} = {value}")
                for quoted_prop in custom_data['quoted_props']:
                    print(f"  {quoted_prop['line']} (quoted property)")
            return True

        # Read target file as lines
        target_lines = self.read_file_as_lines(self.target_file)

        # Apply customizations
        result_lines = self.apply_customizations_to_target(target_lines, customizations)

        # Create backup
        if create_backup and self.target_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.target_file.with_suffix(f'.backup_{timestamp}.toml')
            shutil.copy2(self.target_file, backup_file)
            print(f"Backup created: {backup_file}")

        # Write result
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.writelines(result_lines)

        print(f"Migration completed: {self.output_file}")
        print(f"Applied {len(self.applied_changes)} changes")
        print("✓ Section structure preserved")
        print("✓ Quoted properties kept within parent sections")

        return True

    def validate(self) -> bool:
        """Validate the migrated configuration."""
        if not self.output_file.exists():
            print("Error: Output file not found")
            return False

        try:
            migrated_config = self.parse_toml_file(self.output_file)
            print("✓ Valid TOML syntax")

            # Check required sections
            missing_sections = [s for s in REQUIRED_SECTIONS if s not in migrated_config]

            if missing_sections:
                print(f"⚠ Missing required sections: {missing_sections}")
                return False

            print(f"✓ All required sections present")

            # Check apim.analytics structure
            if 'apim' in migrated_config and 'analytics' in migrated_config['apim']:
                analytics = migrated_config['apim']['analytics']
                print(f"✓ apim.analytics section: enable={analytics.get('enable')}, type={analytics.get('type')}")

                if 'properties' in analytics:
                    properties = analytics['properties']
                    print(f"✓ apim.analytics.properties found with {len(properties)} properties")
                    if 'moesifKey' in properties:
                        print("✓ moesifKey preserved in properties")
                else:
                    print("⚠ apim.analytics.properties not found")

            return True

        except (toml.TomlDecodeError, IOError, KeyError) as e:
            print(f"✗ Validation failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Corrected WSO2 deployment.toml migration preserving section structure"
    )
    parser.add_argument('source', help='Source deployment.toml (with customizations)')
    parser.add_argument('target', help='Target deployment.toml (new version template)')
    parser.add_argument('-o', '--output', help='Output file (default: target.migrated.toml)')
    parser.add_argument('-c', '--config', help=f'Config file (default: {DEFAULT_CONFIG_FILE})', default=DEFAULT_CONFIG_FILE)
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--validate', action='store_true', help='Validate migrated config')

    args = parser.parse_args()

    # Validate input files
    for file_path in [args.source, args.target]:
        if not Path(file_path).exists():
            print(f"Error: File {file_path} not found")
            sys.exit(1)

    # Create corrected migrator
    migrator = CorrectedTomlMigrator(args.source, args.target, args.output, args.config)

    # Perform migration
    success = migrator.migrate(
        create_backup=not args.no_backup,
        dry_run=args.dry_run
    )

    if not success:
        sys.exit(1)

    # Validate if requested
    if args.validate and not args.dry_run:
        if not migrator.validate():
            sys.exit(1)


if __name__ == '__main__':
    main()