# Release V1 Selection Rationale

## Purpose

This document explains why the current V1 release keeps a 12-label training set instead of activating every discovered label at once.

It should be read together with:

- `specs/labels/discovered_label_catalog.json`
- `specs/labels/release_v1.json`
- `docs/labels/release_v1_expansion_plan.md`
- `docs/architecture/foodkeeper-first-training-architecture.md`

## Filtering Principles

The V1 label shortlist was filtered using the following rules, in order:

1. **FoodKeeper alignment comes first**
   - The label must already have a direct and defensible FoodKeeper anchor.
   - The class should not merge items whose storage guidance is meaningfully different.

2. **The class should fit a fridge-first product scope**
   - V1 should focus on common refrigerator ingredients and a small dairy baseline.
   - Pantry-heavy and packaged-grocery labels are intentionally delayed.

3. **The visual boundary should be stable enough for a first baseline**
   - Labels that are visually narrow and easier to explain are preferred over broad grouped categories.
   - The first release should avoid unnecessary ambiguity from mixed product forms.

4. **The data path should be simple enough to operationalize quickly**
   - Labels already supported by the current discovery catalog and public datasets are preferred.
   - V1 should minimize special-case data handling before the training pipeline is rebuilt.

5. **The first release should stay intentionally small**
   - A smaller class list makes early error analysis easier.
   - It reduces the chance that weak long-tail labels hide problems in the first baseline.

## Why These 12 Labels Were Chosen

### `apple`

- Common fridge item with a clean single FoodKeeper anchor.
- Strongly aligned with the expected consumer use case.
- Easy to explain and validate in a first baseline.

### `banana`

- Common consumer food with a single direct anchor.
- Narrow visual concept and low taxonomy ambiguity.
- Useful as a core fruit label without requiring grouped-fruit logic.

### `cabbage`

- Recognizable fresh produce with stable semantics.
- A better V1 vegetable candidate than more marginal or pantry-like classes.

### `carrots`

- High-value everyday fridge produce item.
- Already mapped through a defensible FoodKeeper carrots/parsnips anchor.
- Strong fit for a fridge ingredient classifier.

### `cucumber`

- Simple produce class with direct visual identity.
- Single FoodKeeper anchor and straightforward training semantics.

### `mushroom`

- Common fridge produce item with clear utility for freshness guidance.
- Visually more coherent than several long-tail fruit classes.

### `onion`

- Important real-world kitchen ingredient.
- Current discovery note already narrows it to yellow/white/red onion rather than spring onion.
- Good example of a useful ingredient-focused label with explicit scope control.

### `bell_pepper`

- The current catalog already constrains this to bell pepper color variants.
- That makes it more stable than a generic pepper class.
- Strong fridge relevance and good product value.

### `potato`

- Common kitchen staple with clear user value.
- The current discovery work already excludes sweet potato, which keeps the label boundary cleaner.

### `zucchini`

- Narrow produce class with exact anchor selection.
- Explicitly kept separate from broader squash semantics, which makes it safer for V1 than a looser grouped class.

### `packaged_dairy_milk`

- One of the two cross-dataset labels, so it has stronger data support than many single-dataset labels.
- Important dairy baseline for a fridge-first product.
- Already constrained to packaged dairy milk rather than a broad milk super-class.

### `dairy_yoghurt`

- Useful dairy baseline with clear fridge relevance.
- Explicitly limited to dairy yogurt, which avoids mixing plant-based and dairy storage semantics.
- Works well as the second dairy label beside packaged milk.

## Why Other Labels Were Not Put Into V1 Yet

### Delayed But Still Good Candidates

Examples:

- `asparagus`
- `eggplant`
- `avocado`
- `kiwi`
- `lemon`
- `lime`
- `orange`
- `watermelon`
- `soy_milk`
- `packaged_juice`

These were delayed because V1 needs to stay small and easy to debug, not because they are bad labels.

### Delayed Because They Broaden Scope Too Early

Examples:

- `canned_beans`
- `canned_corn`
- `canned_fish`
- `white_flour`
- `jam_preserves`
- `packaged_nuts`
- `edible_oil`
- `dry_rice`
- `soda`
- `canned_tomato_products`

These are valid discovered labels, but they pull the project toward pantry and packaged-grocery recognition instead of the first fridge-ingredient baseline.

### Not Yet Available In The Discovery Catalog

Important labels still missing from the current discovery layer include:

- `egg`
- `cheese`
- `tofu`
- `broccoli`
- `shrimp`
- `raw_meat`
- `raw_poultry`

These need more discovery and mapping work before they can be evaluated as release labels.

## Summary

The V1 set is not meant to be the complete taxonomy.

It is a deliberately narrow first release chosen to maximize:

- FoodKeeper correctness
- fridge-use-case relevance
- visual stability
- data simplicity
- explainability during early training and evaluation
