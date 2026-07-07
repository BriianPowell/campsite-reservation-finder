#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
search_dir="${SEARCH_DIR:-${project_root}/searches}"

shopt -s nullglob
configs=("${search_dir}"/*.yaml "${search_dir}"/*.yml)

ran_search=0
email_subject_prefix="${EMAIL_SUBJECT_LINE:-Camply}"

for config in "${configs[@]}"; do
  name="$(basename "${config}")"
  search_name="${name%.*}"

  case "${name}" in
    example.yaml|example.yml|*.disabled.yaml|*.disabled.yml)
      echo "Skipping template or disabled search config: ${name}"
      continue
      ;;
  esac

  subject="${email_subject_prefix}: ${search_name}"
  echo "Running Camply search config: ${name}"
  echo "Email subject: ${subject}"
  EMAIL_SUBJECT_LINE="${subject}" camply campsites --yaml-config "${config}"
  ran_search=1
done

if [[ "${ran_search}" -eq 0 ]]; then
  echo "No enabled search configs found in ${search_dir}."
  echo "Copy searches/example.yaml to a new filename and fill in real search criteria."
fi
