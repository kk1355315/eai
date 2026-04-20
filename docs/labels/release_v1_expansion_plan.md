# Release V1 Expansion Plan

## Goal

Lock a small first training set for V1, then add more labels in controlled waves instead of widening the class list all at once.

## Current V1 Selection

The current V1 release file enables these 12 labels:

- `apple`
- `banana`
- `cabbage`
- `carrots`
- `cucumber`
- `mushroom`
- `onion`
- `bell_pepper`
- `potato`
- `zucchini`
- `packaged_dairy_milk`
- `dairy_yoghurt`

## Why These 12 Go First

- They are common fridge items rather than edge-case pantry products.
- Their FoodKeeper anchors are straightforward enough for a first release.
- Their visual boundaries are more stable than broader grouped categories.
- They align reasonably well with the existing GroceryStoreDataset-first discovery path.
- They keep V1 focused on produce plus a small dairy baseline instead of mixing too many product forms.

## Expansion Wave 2

These are good next additions once V1 training and error analysis are in place:

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

Reasons:

- The FoodKeeper linkage is already present in the discovery catalog.
- These classes still fit the fridge-recognition direction.
- They are somewhat narrower, less frequent, or more packaging-sensitive than the V1 core set.

## Expansion Wave 3

These can be reconsidered after Wave 2, especially if more target-domain fridge images are collected:

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
- `red_grapefruit`
- `satsuma`
- `red_beet`

Reasons:

- Several are less central to the initial fridge use case.
- Some are long-tail produce labels that are easier to add after the first release baseline is stable.
- Some grouped fruit labels will benefit from later target-domain validation before release.

## Hold Out Of The Fridge-First Mainline For Now

These should stay out of the first main training line unless the product scope explicitly expands toward pantry and packaged grocery recognition:

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

Reasons:

- They skew toward pantry or packaged-grocery recognition rather than fresh fridge ingredients.
- Mixing them into the first release would broaden the product scope too early.
- They remain valid discovery assets and can be activated later if the roadmap expands.

## Known Missing Labels

The current discovery catalog still does not cover some important fridge items such as:

- `egg`
- `cheese`
- `tofu`
- `broccoli`
- `shrimp`
- `raw_meat`
- `raw_poultry`

These should be handled as a separate discovery and data-mapping task rather than being forced into the current release set.
