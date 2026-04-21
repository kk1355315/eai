# Release V3 Selection Rationale

## Purpose

Release V3 extends the current V2 set with the planned Wave 3 long-tail produce labels while keeping the same fridge-first scope.

## What V3 Adds

On top of the V2 22-label set, V3 adds:

- `ginger`
- `garlic`
- `leek`
- `melon`
- `mango`
- `nectarine`
- `papaya`
- `passion_fruit`
- `peach`
- `pear`
- `pineapple`
- `plum`
- `pomegranate`
- `red_beet`
- `red_grapefruit`
- `satsuma`

## Why These Labels Are In V3 Instead Of V2

- They are valid discovered labels with direct FoodKeeper anchors.
- They still fit the produce-heavy fridge-recognition direction.
- They are more long-tail, less central, or more specialized than the Wave 2 additions.
- They are better treated as a second expansion wave rather than part of the first widening step.

## Why They Are Included Now

- The V1 and V2 label pipelines are already in place.
- The project now has a stable way to compare wider label sets under the same training setup.
- Adding these labels lets us measure how much long-tail produce expansion costs in accuracy before touching pantry-heavy classes.

## What Still Remains Out Of Scope

V3 still does not include:

- pantry-heavy packaged labels such as `canned_beans`, `white_flour`, `dry_rice`, and `soda`
- labels still missing from the discovery catalog such as `egg`, `cheese`, `tofu`, `broccoli`, `shrimp`, `raw_meat`, and `raw_poultry`

## Training Policy

The first V3 run should keep the same best-performing baseline used for V2:

- `MobileNetV2`
- `ImageNet` pretrained weights
- `learning_rate=3e-4`
- `epochs=8`

That keeps V2-to-V3 comparisons attributable to label-set growth rather than mixed hyperparameter changes.
