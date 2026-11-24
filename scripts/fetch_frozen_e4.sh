#!/usr/bin/env bash
# Fetch the frozen E4 checkpoint from its permanent home.
#
# The frozen E4 checkpoint was first kept as GitHub Actions artifact
# 12183110279, which expired on 2026-11-18. The identical archive (same
# SHA-256 digest) is preserved in the evidence-package-40061151659 release.
# This script downloads that release, checks both pinned digests, and writes:
#   OUTPUT_DIR/e4-checkpoint.zip           byte-identical to the original artifact
#   OUTPUT_DIR/e4-artifact-metadata.json   the artifact metadata recorded at freeze
#                                          time, plus where it was retrieved from
#
# Usage: scripts/fetch_frozen_e4.sh OUTPUT_DIR
# Needs: gh (with GH_TOKEN), sha256sum, tar, python3.
set -euo pipefail

out="${1:?usage: fetch_frozen_e4.sh OUTPUT_DIR}"
repo="${GITHUB_REPOSITORY:-BurhanAbdullah/BioNuclei-DomainRobust}"
tag="evidence-package-40061151659"
package="BioNuclei-evidence-package-40061151659.tar.gz"
package_sha256="aef466d4d1a9c76d5378b519243641e7d160a5506aa94073fe760d130651a0f9"
e4_sha256="89e66617e272d30ec46471c8403950c404c772780ad778dd6f0e992fc795df0d"

if [ -n "${EXPECTED_E4_DIGEST:-}" ] && [ "${EXPECTED_E4_DIGEST}" != "sha256:${e4_sha256}" ]; then
  echo "EXPECTED_E4_DIGEST (${EXPECTED_E4_DIGEST}) does not match the preserved checkpoint sha256:${e4_sha256}" >&2
  exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
asset_id="$(gh api "repos/${repo}/releases/tags/${tag}" --jq ".assets[] | select(.name == \"${package}\") | .id")"
test -n "$asset_id" || { echo "Release ${tag} has no asset ${package}" >&2; exit 1; }
gh api -H "Accept: application/octet-stream" "repos/${repo}/releases/assets/${asset_id}" > "${work}/${package}"
echo "${package_sha256}  ${work}/${package}" | sha256sum --check --strict -
tar -xzf "${work}/${package}" -C "$work" \
  package/evidence/e4-frozen-checkpoint.zip \
  package/evidence/e4-frozen-checkpoint.metadata.json
echo "${e4_sha256}  ${work}/package/evidence/e4-frozen-checkpoint.zip" | sha256sum --check --strict -

mkdir -p "$out"
cp "${work}/package/evidence/e4-frozen-checkpoint.zip" "${out}/e4-checkpoint.zip"
python3 - "${work}/package/evidence/e4-frozen-checkpoint.metadata.json" "${out}/e4-artifact-metadata.json" "$tag" "$package" "$package_sha256" <<'PY'
import json, sys
src, dst, tag, package, package_sha = sys.argv[1:]
meta = json.loads(open(src).read())
assert meta["id"] == 12183110279
assert meta["digest"] == "sha256:89e66617e272d30ec46471c8403950c404c772780ad778dd6f0e992fc795df0d"
meta["retrieved_from"] = {
    "release_tag": tag,
    "release_asset": package,
    "release_asset_sha256": package_sha,
    "member": "package/evidence/e4-frozen-checkpoint.zip",
    "note": "Actions artifact expired 2026-11-18; this archive is byte-identical (same digest).",
}
open(dst, "w").write(json.dumps(meta, indent=2) + "\n")
PY
echo "Frozen E4 checkpoint verified: artifact 12183110279 / sha256:${e4_sha256} (from release ${tag})"
