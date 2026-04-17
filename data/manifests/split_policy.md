# Split Policy

- A single image may appear in only one split.
- A normalized manifest should keep only one row per source image inside a split, even if an upstream dataset ships duplicate split entries.
- Real fridge-domain images must reserve held-out `val` and `test` subsets.
- Public and target-domain manifests remain separate source files even if a later training job merges them logically.
- Split decisions should be reproducible from durable metadata, not ad-hoc notebook state.
- If Stage A public data does not cover a released V1 class, the gap must be documented and closed with Stage B fridge images or a newly mapped public dataset before any V1 release claim.
