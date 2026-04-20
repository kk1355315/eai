# Release V2 Selection Rationale

## Purpose

Release V2 extends the V1 12-label core with the next wave of fridge-compatible labels that were already shortlisted in the expansion plan.

## Selection Logic

V2 keeps all V1 labels and adds:

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

These labels were chosen because:

- they already exist in the current discovery catalog
- they still fit the fridge-first product direction
- they do not force the scope into pantry-heavy packaged grocery recognition
- they are a cleaner next step than the longer-tail produce classes reserved for later waves

## Why These Were Added Before Wave 3

- They are more central to everyday fridge recognition than the long-tail fruit set.
- Several are common consumer items with direct FoodKeeper anchors and straightforward semantics.
- `soy_milk` and `packaged_juice` add realistic packaged fridge items without expanding all the way into pantry recognition.
- `lemon`, `lime`, and `orange` are still narrow enough to add before broader fruit expansion.

## What Still Stays Out

V2 still leaves out:

- pantry-heavy packaged labels such as `canned_beans`, `white_flour`, `dry_rice`, and `soda`
- long-tail produce labels planned for later expansion waves
- missing labels such as `egg`, `cheese`, `tofu`, `broccoli`, `shrimp`, `raw_meat`, and `raw_poultry`

## Training Policy

The first V2 run should reuse the best-performing V1 setup:

- `MobileNetV2`
- `ImageNet` pretrained weights
- `learning_rate=3e-4`
- `epochs=8`

That keeps the comparison between V1 and V2 focused on label-set expansion rather than mixed training changes.
