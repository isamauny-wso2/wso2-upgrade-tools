# WSO2 API Manager deployment.toml Migration Tool

This tool automatically migrates customizations from an older WSO2 deployment.toml file to a newer version while preserving the new version's structure and defaults.

THIS TOOL IS UNDER ACTIVE DEVELOPMENT AND WILL CONTAIN ERRORS. YOU MUST REVIEW THE OUTPUT FOR CORRECTNESS.

## Features

- **Smart Merging**: Preserves new version structure while applying customizations
- **Commented Section Handling**: Automatically uncomments and updates template sections with custom values
- **Array Table Preservation**: Correctly handles TOML array tables with `[[...]]` notation
- **Section Ordering**: Maintains hierarchical section ordering (e.g., `apim.ai.*` after `[apim.ai]`)
- **Backup Creation**: Automatically backs up target files before migration
- **Validation**: Validates migrated configuration for correctness
- **Dry Run**: Preview changes before applying them
- **Configuration-Driven**: Uses external JSON config for ordering rules and customization

## Installation

```bash
pip install toml
```

## Usage

### Basic Migration
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml
```

### Preview Changes (Dry Run)
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml --dry-run
```

### Migration with Custom Output
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml -o custom_output.toml
```

### Use Custom Configuration File
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml -c my_rules.json
```

### Skip Backup Creation
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml --no-backup
```

### Validate After Migration
```bash
python3 wso2_migration.py source_v45.toml target_v46.toml --validate
```

## Migration Strategy

The tool uses an intelligent migration strategy that:

1. **Parses both files** using proper TOML parsing
2. **Identifies customizations** by comparing against known defaults and target values
3. **Uncomments template sections** when customizations exist in source
4. **Preserves critical sections** like database configs, analytics, AI settings
5. **Maintains array table notation** using `[[...]]` for TOML array tables
6. **Orders sections hierarchically** based on parent-child relationships
7. **Merges intelligently** while maintaining the target version's structure
8. **Handles special cases** like gateway environments and nested configurations

### How Commented Sections Are Handled

When the template file has commented sections (e.g., `#[apim.devportal]`) and your source has active customizations:

**Template (before):**
```toml
#[apim.devportal]
#url = "https://localhost:${mgt.transport.https.port}/devportal"
#enable_application_sharing = false
```

**Your source:**
```toml
[apim.devportal]
url = "https://apim-next.apis.coach:${mgt.transport.https.port}/devportal"
```

**Result:**
```toml
[apim.devportal]  ← Uncommented!
url = "https://apim-next.apis.coach:${mgt.transport.https.port}/devportal"  ← Your value!
#enable_application_sharing = false  ← Others stay commented
```

### Array Table Handling

TOML array tables (sections that can appear multiple times) are preserved with double brackets:

**Correctly preserved:**
```toml
[[apim.ai.guardrail_provider]]  ← Double brackets maintained
type = "azure-contentsafety"

[[apim.gateway.environment]]  ← Can have multiple instances
name = "Production"
```

### Sections Always Preserved
- Database configurations (`database.*`)
- Analytics settings (`apim.analytics`)
- AI configurations (`apim.ai.*`)
- Keystore settings (`keystore.*`)
- Gateway environments (`apim.gateway.environment`)

### Default Values Ignored
- `server.hostname = "localhost"`
- `super_admin.username = "admin"`
- `super_admin.password = "admin"`
- Default H2 database configurations

## Example

Use the default deployment.toml delivered with the product as template. The script identifies missing sections and adds them to the target file.

```bash
# Upgrade from 4.5 to 4.6 with validation
python3 wso2_migration.py \
    current_deployment_45.toml \
    new_deployment_46_template.toml \
    --validate \
    -o deployment_46_migrated.toml
```

## Output Files

- **Backup**: `target.backup_YYYYMMDD_HHMMSS.toml`
- **Migrated**: `target.migrated.toml` (or custom output file)

## Validation

The tool validates:
- ✅ Valid TOML syntax
- ✅ Required sections present (`server`, `super_admin`, `database`)
- ✅ No syntax errors in merged configuration

## Known Issues

You will need to update this entry to add all the GW types you want to work with: 

```
[apim]
gateway_type = "Regular,APK,AWS,Azure,Kong,Envoy"
```

## Common Migration Scenarios

### Database Configuration
- PostgreSQL → H2: Preserves PostgreSQL settings
- H2 → PostgreSQL: Applies new PostgreSQL configuration
- Custom connection pools and validation queries are preserved

### Gateway Environments
- Merges by environment name
- Preserves custom endpoints and URLs
- Maintains backward compatibility

### Analytics & AI
- Preserves Moesif configurations
- Maintains AI guardrail settings
- Keeps custom embedding providers

## Troubleshooting

### Common Issues

1. **File not found**: Ensure both source and target files exist
2. **Invalid TOML**: Check file syntax before migration
3. **Permission errors**: Ensure write permissions for output directory

### Debug Mode
Add print statements or use `--dry-run` to see what changes would be applied.

## Best Practices

### Before Migration

1. **Always use `--dry-run` first** to preview changes:
   ```bash
   python3 wso2_migration.py source.toml template.toml --dry-run
   ```

2. **Keep the default template** - Use the official WSO2 deployment.toml template for your target version as the template file

3. **Backup your source** - Even though the tool backs up the target, keep your source safe

4. **Review custom sections** - Check if you have any custom sections that need special ordering rules

### After Migration

1. **Validate the output**:
   ```bash
   python3 wso2_migration.py source.toml template.toml --validate
   ```

2. **Test the configuration** in a non-production environment first

3. **Review uncommented sections** - Sections that were commented in the template will be uncommented if you have custom values

4. **Check array tables** - Verify that sections like `[[apim.gateway.environment]]` have double brackets

### Customizing for Your Needs

If you have custom sections or specific ordering requirements:

1. Edit `custom_migration_rules.json`
2. Add your sections to `array_tables` if they can appear multiple times
3. Define parent-child relationships in `section_ordering.rules`
4. Add patterns to `ignore_patterns` for default values you don't want migrated

## Advanced Usage

### Custom Migration Rules

The migration tool can be customized using the `custom_migration_rules.json` file, which provides fine-grained control over migration behavior.

#### Rules File Structure

```json
{
  "auto_detect_strategy": true,
  "preserve_user_values": true,
  "conflict_resolution": "source_wins",
  "ignore_patterns": [
    "server.hostname:localhost",
    "super_admin.username:admin",
    "database.*.type:h2"
  ],
  "force_preserve": [
    "database.*",
    "keystore.*",
    "apim.analytics.*"
  ]
}
```

#### Configuration Options

**Basic Behavior:**
- `auto_detect_strategy`: Automatically detect customizations vs defaults
- `preserve_user_values`: Prioritize source values over target defaults
- `conflict_resolution`: How to handle conflicts (`source_wins`, `target_wins`, `merge`)

**Section Ordering Rules:**
Define hierarchical ordering to ensure child sections appear after their parents:
```json
"section_ordering": {
  "rules": [
    {
      "parent": "apim.ai",
      "children_must_follow": true,
      "child_sections": [
        "apim.ai.embedding_provider",
        "apim.ai.embedding_provider.properties",
        "apim.ai.vector_db_provider",
        "apim.ai.vector_db_provider.properties",
        "apim.ai.guardrail_provider",
        "apim.ai.guardrail_provider.properties"
      ]
    }
  ],
  "array_tables": [
    "apim.gateway.environment",
    "apim.ai.guardrail_provider",
    "event_handler",
    "event_listener"
  ]
}
```

**Ordering Rules Explained:**
- `parent`: The parent section name
- `children_must_follow`: If `true`, child sections appear immediately after parent
- `child_sections`: Ordered list of child sections
- `array_tables`: Sections that should use `[[...]]` notation (can appear multiple times)

**Ignore Patterns:**
Values matching these patterns are considered defaults and won't be migrated:
```json
"ignore_patterns": [
  "server.hostname:localhost",
  "super_admin.username:admin",
  "super_admin.password:admin",
  "keystore.*.alias:wso2carbon",
  "database.*.type:h2"
]
```

**Force Preserve Sections:**
These sections are always migrated regardless of other rules:
```json
"force_preserve": [
  "database.*",
  "keystore.*",
  "apim.analytics.*",
  "apim.ai.*",
  "apim.gateway.environment.*"
]
```

**Version-Specific Handling:**
```json
"version_specific_handling": {
  "v4.5_to_v4.6": {
    "deprecated_keys": ["apim.cache.gateway_token"],
    "new_keys": ["oauth.token_cleanup"],
    "renamed_keys": {}
  }
}
```

**Environment Profiles:**
Different rules for different deployment environments:
```json
"environment_profiles": {
  "production": {
    "extra_preserve": ["transport.receiver.*"],
    "extra_ignore": ["apim.cache.*"]
  },
  "development": {
    "extra_preserve": ["apim.ai.*"]
  }
}
```

#### Using Custom Rules

1. **Edit the rules file:**
   ```bash
   vim custom_migration_rules.json
   ```

2. **Add new ignore patterns:**
   ```json
   "ignore_patterns": [
     "your.custom.pattern:default_value"
   ]
   ```

3. **Add sections to always preserve:**
   ```json
   "force_preserve": [
     "your.custom.section.*"
   ]
   ```

#### Pattern Syntax

- **Exact match**: `"server.hostname:localhost"`
- **Wildcard sections**: `"database.*"` (matches all database subsections)
- **Wildcard values**: `"keystore.*.alias:wso2carbon"` (any keystore alias with default value)

### Legacy Customization

If not using the rules file, you can still customize behavior by editing the script directly:

**Custom Ignore Rules:**
Edit the `ignore_defaults` dictionary in the script to customize which default values to ignore during migration.

**Custom Preserve Sections:**
Modify the `preserve_sections` set to add additional sections that should always be preserved.

## Quick Reference

### Command Line Options

| Option | Description |
|--------|-------------|
| `source` | Source deployment.toml with your customizations (required) |
| `target` | Target deployment.toml template for new version (required) |
| `-o, --output` | Output file path (default: `target.migrated.toml`) |
| `-c, --config` | Custom rules JSON file (default: `custom_migration_rules.json`) |
| `--no-backup` | Skip creating backup of target file |
| `--dry-run` | Preview changes without applying them |
| `--validate` | Validate migrated configuration after migration |

### What Gets Migrated

✅ **Always Migrated:**
- Database configurations with custom values
- Custom gateway environments
- Analytics and AI configurations
- Custom keystore settings
- Transport and security settings
- Custom properties with quoted names (e.g., `properties."moesifKey"`)

❌ **Never Migrated (Defaults):**
- `server.hostname = "localhost"`
- `super_admin.username = "admin"`
- `super_admin.password = "admin"`
- Default H2 database types
- Default keystore aliases

### File Locations

```
project/
├── wso2_migration.py              # Main migration script
├── custom_migration_rules.json    # Configuration file
├── source_deployment.toml         # Your current config
├── target_template.toml           # WSO2 template for new version
└── output/
    ├── deployment.migrated.toml   # Result
    └── target.backup_*.toml       # Auto-backup
```

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.