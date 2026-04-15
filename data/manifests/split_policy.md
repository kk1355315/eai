# Split Policy

- A single image may appear in only one split.
- Real fridge-domain images must reserve held-out `val` and `test` subsets.
- Public and target-domain manifests remain separate source files even if a later training job merges them logically.
- Split decisions should be reproducible from durable metadata, not ad-hoc notebook state.
