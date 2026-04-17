# Manifest Schema

## Required Columns

- `image_path`: path relative to the manifest file location, never a machine-specific absolute path
- `source`
- `original_label`
- `mapped_label`
- `split`
- `is_target_domain`

## Recommended Columns

- `capture_condition`
- `container_type`
- `notes`

## Allowed Split Values

- `train`
- `val`
- `test`
