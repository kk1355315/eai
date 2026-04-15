# Fridge Main Object Classifier V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable V1 single-main-object classifier for refrigerator foods and ingredients, trained on mixed public datasets plus target-domain fridge images, and exported through the Sony Aitrios MobileNetV2 classifier workflow.

**Architecture:** Use a product-owned taxonomy instead of raw dataset labels. Train in two stages: public-data pretraining, then target-domain fridge fine-tuning. Keep the pipeline versioned by taxonomy, manifest, checkpoint, and exported model so new classes can be added later without redesigning the whole system.

**Tech Stack:** Python, CSV/JSON manifests, Jupyter Notebook or Python scripts, Sony Aitrios AI model training tutorials, MobileNetV2 classifier, Model Compression Toolkit, Raspberry Pi AI Camera / Aitrios deployment flow

---

## Summary
- V1 is a `single main object classification` system, not multi-object detection.
- V1 starts with `28-36` high-value, visually stable classes and expands by versioned retraining.
- Training is fixed to two stages:
  - `Stage A`: public dataset pretraining
  - `Stage B`: real fridge image fine-tuning and acceptance testing
- Deployment follows the Sony official `MobileNetV2 classifier` path to reduce export and quantization risk.

## Public Artifacts
- `docs/taxonomy/v1_labels.csv`
- `docs/mappings/chinesefoodnet_to_v1.csv`
- `docs/mappings/grocery_to_v1.csv`
- `data/manifests/public_stage_a.csv`
- `data/manifests/target_stage_b.csv`
- `training/aitrios_mobilenet_v1.ipynb` or `training/train_v1.py`
- `reports/v1_eval.md`
- `exports/v1/`

## Task 1: Project Bootstrap

**Files:**
- Create: `README.md`
- Create: `docs/taxonomy/README.md`
- Create: `docs/mappings/README.md`
- Create: `data/manifests/README.md`
- Create: `training/README.md`
- Create: `reports/README.md`
- Create: `exports/README.md`

- [ ] **Step 1: Create the base directory layout**

Create:
- `docs/taxonomy/`
- `docs/mappings/`
- `data/manifests/`
- `training/`
- `reports/`
- `exports/`

- [ ] **Step 2: Write a root README**

Include:
- Project goal
- Two-stage training flow
- Required public references
- Expected output artifacts

- [ ] **Step 3: Add one README per top-level working directory**

Each README must state:
- What goes in the directory
- What is generated vs source-of-truth
- Which files are versioned

- [ ] **Step 4: Verify the structure is readable**

Run: `Get-ChildItem -Recurse`

Expected:
- All working directories exist
- No ambiguous folder purpose

## Task 2: Freeze V1 Taxonomy

**Files:**
- Create: `docs/taxonomy/v1_labels.csv`
- Create: `docs/taxonomy/v1_taxonomy_notes.md`
- Test: `docs/taxonomy/v1_labels.csv`

- [ ] **Step 1: Write the V1 class list**

The CSV must include at least:
- `class_id`
- `class_name`
- `class_group`
- `status`
- `notes`

- [ ] **Step 2: Keep classes product-oriented**

Rules:
- Fresh ingredients can stay relatively specific if visually stable
- Prepared foods should use medium-granularity categories
- Low-frequency or visually ambiguous classes stay out of V1

- [ ] **Step 3: Write taxonomy notes**

Document:
- Inclusion rules
- Exclusion rules
- Expansion rule: old `class_id` values never change; new classes append

- [ ] **Step 4: Manual review**

Check:
- No duplicate semantic classes
- No class that requires smell, packaging text, or recipe knowledge to separate
- No class that is too broad to be useful

## Task 3: Map Public Datasets Into V1

**Files:**
- Create: `docs/mappings/chinesefoodnet_to_v1.csv`
- Create: `docs/mappings/grocery_to_v1.csv`
- Create: `docs/mappings/mapping_rules.md`
- Test: `docs/mappings/chinesefoodnet_to_v1.csv`
- Test: `docs/mappings/grocery_to_v1.csv`

- [ ] **Step 1: Enumerate source labels from GroceryStoreDataset**

Capture:
- Original fine class
- Original coarse class if present
- Proposed V1 mapped label
- Keep/drop decision

- [ ] **Step 2: Enumerate source labels from ChineseFoodNet**

Capture:
- Original class name
- Proposed V1 mapped label
- Keep/drop decision

- [ ] **Step 3: Write mapping rules**

Rules must be explicit:
- One source label maps to exactly one V1 label or `DROP`
- If a source class is visually unstable or overlaps multiple V1 classes, mark `DROP`
- Do not force coverage for every public class

- [ ] **Step 4: Validate mapping tables**

Check:
- No source label maps to multiple V1 labels
- Every kept mapping points to an existing V1 class
- Drop reasons are recorded for discarded classes

## Task 4: Build Unified Manifests

**Files:**
- Create: `data/manifests/public_stage_a.csv`
- Create: `data/manifests/target_stage_b.csv`
- Create: `data/manifests/manifest_schema.md`
- Create: `data/manifests/split_policy.md`
- Test: `data/manifests/public_stage_a.csv`
- Test: `data/manifests/target_stage_b.csv`

- [ ] **Step 1: Define the manifest schema**

Required columns:
- `image_path`
- `source`
- `original_label`
- `mapped_label`
- `split`
- `is_target_domain`

Recommended extra columns:
- `capture_condition`
- `container_type`
- `notes`

- [ ] **Step 2: Build the public manifest**

Rules:
- Include only mapped labels retained in V1
- Keep dataset provenance
- Split into train/val/test without leakage

- [ ] **Step 3: Build the target-domain manifest**

Rules:
- At least `20-50` fridge images per V1 class if feasible
- Cover common deployment conditions: containers, bags, fridge light, angle changes, partial occlusion
- Keep a held-out validation/test subset from the target domain

- [ ] **Step 4: Validate both manifests**

Check:
- Every `image_path` exists
- Every `mapped_label` exists in `v1_labels.csv`
- No image appears in more than one split
- Target-domain rows are correctly flagged

## Task 5: Stage A Public Pretraining

**Files:**
- Create: `training/aitrios_mobilenet_v1.ipynb` or `training/train_v1.py`
- Create: `training/config_stage_a.md`
- Create: `reports/stage_a_training_log.md`
- Test: `training/aitrios_mobilenet_v1.ipynb` or `training/train_v1.py`

- [ ] **Step 1: Reproduce the Sony classifier training environment**

Use:
- Official Sony Aitrios AI model training tutorial repo
- Official MobileNetV2 classifier flow

- [ ] **Step 2: Adapt the training entrypoint to the V1 manifests**

The entrypoint must consume:
- Unified manifest
- V1 label map
- Output directory for checkpoints and logs

- [ ] **Step 3: Train Stage A**

Input:
- `public_stage_a.csv`

Output:
- Base checkpoint
- Training metrics
- Validation metrics

- [ ] **Step 4: Record Stage A findings**

Document:
- Overall validation accuracy
- Per-class weaknesses
- Obvious class confusions

## Task 6: Stage B Target-Domain Fine-Tuning

**Files:**
- Modify: `training/aitrios_mobilenet_v1.ipynb` or `training/train_v1.py`
- Create: `training/config_stage_b.md`
- Create: `reports/stage_b_training_log.md`
- Test: `reports/stage_b_training_log.md`

- [ ] **Step 1: Load the Stage A checkpoint**

Requirement:
- Reuse the same V1 class order
- Do not change old `class_id` assignments

- [ ] **Step 2: Fine-tune with target-domain data**

Input:
- `target_stage_b.csv`
- Optional mix of Stage A public data if needed to preserve generalization

Priority:
- Optimize for fridge-domain usefulness, not public benchmark vanity

- [ ] **Step 3: Monitor class confusion**

Check especially:
- Visually similar food pairs
- Ingredient vs prepared-food overlaps
- Container-induced failures

- [ ] **Step 4: Save the candidate V1 deployment checkpoint**

Expected:
- A checkpoint selected by target-domain validation performance

## Task 7: Evaluation And Acceptance

**Files:**
- Create: `reports/v1_eval.md`
- Create: `reports/v1_confusion_matrix.csv` or equivalent image export
- Test: `reports/v1_eval.md`

- [ ] **Step 1: Evaluate on public validation/test data**

Report:
- Overall accuracy
- Per-class recall
- Main confusion pairs

- [ ] **Step 2: Evaluate on target-domain validation/test data**

Report:
- `top-1 accuracy`
- Per-class recall
- Failure examples

- [ ] **Step 3: Apply the V1 ship criteria**

Initial acceptance targets:
- Target-domain `top-1 >= 80%`
- High-frequency classes should approach `>= 75%` recall
- No catastrophic failure on a core class

- [ ] **Step 4: Decide the next action from evidence**

If acceptance fails:
- First fix taxonomy
- Then fix data coverage
- Only then consider model tuning

## Task 8: Export And Device Validation

**Files:**
- Create: `exports/v1/README.md`
- Create: `reports/device_validation.md`
- Test: `exports/v1/`

- [ ] **Step 1: Export through the Sony-supported path**

Use:
- Official Aitrios export and quantization flow

Output:
- Deployable model artifact under `exports/v1/`

- [ ] **Step 2: Deploy to the AI camera**

Check:
- Model loads correctly
- Inference returns expected class IDs and confidences

- [ ] **Step 3: Run a fixed physical validation set**

Use:
- Real items from the target fridge environment
- Repeated shots with angle/light variation

- [ ] **Step 4: Record device behavior**

Document:
- Stable classes
- Unstable classes
- Cases that need more data or taxonomy changes

## Task 9: Expansion Policy For V2+

**Files:**
- Create: `docs/taxonomy/expansion_policy.md`
- Test: `docs/taxonomy/expansion_policy.md`

- [ ] **Step 1: Document how new classes are added**

Policy:
- Append new class IDs only
- Keep old class IDs stable
- Retrain with old+new class data together

- [ ] **Step 2: Document retraining minimums**

Include:
- Required new public mappings if relevant
- Required target-domain sample count
- Required regression test set for old classes

- [ ] **Step 3: Document release gating**

Every expansion release must include:
- Updated taxonomy
- Updated manifests
- Updated checkpoint
- Updated exported model
- Updated evaluation report

## Test Cases And Scenarios
- A fruit image from GroceryStoreDataset maps cleanly to one V1 ingredient class.
- A ChineseFoodNet dish with unstable semantics is dropped instead of forced into the taxonomy.
- A target-domain image inside a food container still maps to a valid V1 class.
- No manifest row points to a missing image.
- No image leaks across train/val/test splits.
- Stage B loads the exact Stage A class order without relabel drift.
- The exported model returns the same class IDs expected by the taxonomy CSV.
- Device validation exposes unstable classes before any V1 release claim.

## Assumptions And Defaults
- The current workspace started empty and is not a git repository.
- The user already has an AI camera, but training happens on PC first.
- V1 values deployment stability over maximum class count and over leaderboard-style accuracy.
- The project borrows the mixed-dataset idea from `Chinese-and-Western-Food-Classification` but does not copy its raw class design.
- Reference facts used for planning:
  - ChineseFoodNet paper: about `180,000+` images and `208` classes. Source: `https://arxiv.org/abs/1705.02743`
  - GroceryStoreDataset repo: `5125` natural images, `81` fine-grained classes, `42` coarse-grained classes. Source: `https://github.com/marcusklasson/GroceryStoreDataset`
  - Sony official Aitrios training repo includes a `MobileNetV2 classifier` tutorial path. Source: `https://github.com/SonySemiconductorSolutions/aitrios-rpi-tutorials-ai-model-training/tree/main`
