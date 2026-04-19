#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/data/external_datasets"

GROCERY_REPO_URL="https://github.com/marcusklasson/GroceryStoreDataset.git"
FREIBURG_ARCHIVE_URL="http://aisdatasets.informatik.uni-freiburg.de/freiburg_groceries_dataset/freiburg_groceries_dataset.tar.gz"

sync_grocery() {
  local target_dir="$DATA_DIR/GroceryStoreDataset"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[grocery] updating existing checkout: $target_dir"
    git -C "$target_dir" fetch --depth 1 origin
    git -C "$target_dir" reset --hard origin/HEAD
  elif [[ -d "$target_dir" ]]; then
    echo "[grocery] target exists but is not a git repo: $target_dir" >&2
    echo "[grocery] remove it manually if you want to re-clone" >&2
    return 1
  else
    echo "[grocery] cloning official repository into $target_dir"
    git clone --depth 1 "$GROCERY_REPO_URL" "$target_dir"
  fi
}

sync_freiburg() {
  local target_dir="$DATA_DIR/freiburg_groceries_dataset"
  local archive_path="$DATA_DIR/freiburg_groceries_dataset.tar.gz"
  local tmp_extract_dir="$DATA_DIR/.freiburg_extract_tmp"

  if [[ -d "$target_dir/.git" ]]; then
    echo "[freiburg] updating official repository checkout: $target_dir"
    git -C "$target_dir" fetch --depth 1 origin
    git -C "$target_dir" reset --hard origin/HEAD
  elif [[ -d "$target_dir" && -n "$(find "$target_dir" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
    echo "[freiburg] target exists but is not a git repo: $target_dir" >&2
    echo "[freiburg] remove it manually if you want to re-clone" >&2
    return 1
  else
    echo "[freiburg] cloning official repository into $target_dir"
    git clone --depth 1 https://github.com/PhilJd/freiburg_groceries_dataset.git "$target_dir"
  fi

  if [[ -d "$target_dir/images" && -n "$(find "$target_dir/images" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
    echo "[freiburg] images already present under $target_dir/images"
    return 0
  fi

  rm -rf "$tmp_extract_dir"
  mkdir -p "$tmp_extract_dir"

  echo "[freiburg] downloading archive from official source"
  curl -L --fail --retry 3 --output "$archive_path" "$FREIBURG_ARCHIVE_URL"

  echo "[freiburg] extracting archive"
  tar -xf "$archive_path" -C "$tmp_extract_dir"

  if [[ ! -d "$tmp_extract_dir/images" ]]; then
    echo "[freiburg] failed to detect extracted images directory" >&2
    rm -f "$archive_path"
    rm -rf "$tmp_extract_dir"
    return 1
  fi

  rm -rf "$target_dir/images"
  mv "$tmp_extract_dir/images" "$target_dir/images"

  rm -f "$archive_path"
  rm -rf "$tmp_extract_dir"
}

main() {
  mkdir -p "$DATA_DIR"

  local mode="${1:-all}"
  case "$mode" in
    all)
      sync_grocery
      sync_freiburg
      ;;
    grocery)
      sync_grocery
      ;;
    freiburg)
      sync_freiburg
      ;;
    *)
      echo "usage: $0 [all|grocery|freiburg]" >&2
      return 1
      ;;
  esac

  echo
  echo "done. datasets directory:"
  find "$DATA_DIR" -maxdepth 2 -type d | sort
}

main "$@"
