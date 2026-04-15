# Tools

This directory holds lightweight utilities used by the project.

Utilities here should:
- work from normalized manifests and taxonomy files
- avoid framework-heavy dependencies unless justified
- be covered by automated tests when they implement reusable behavior

Current utilities include:
- `validate_manifest.py`: checks schema labels image existence and split leakage
- `build_public_manifest.py`: builds `data/manifests/public_stage_a.csv` from local public datasets and versioned mapping tables
