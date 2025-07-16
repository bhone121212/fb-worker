#!/bin/bash
set -euo pipefail

# === CONFIG ===
IMAGE_NAME="localhost/bhonebhone/fb-worker"
KEEP_COUNT=3

echo "🧹 Cleaning up old images for $IMAGE_NAME, keeping only the latest $KEEP_COUNT"

# === Step 1: Get all buildah images (as root) ===
echo "🔍 Available Buildah images (sudo):"
sudo buildah images

# === Step 2: Filter and sort matching images ===
mapfile -t IMAGE_LIST < <(
  sudo buildah images --format '{{.Created}} {{.ID}} {{.Name}}:{{.Tag}}' |
  grep -F "$IMAGE_NAME" |
  sort -r
)

if [[ "${#IMAGE_LIST[@]}" -eq 0 ]]; then
  echo "⚠️ No matching images found for $IMAGE_NAME. Nothing to clean up."
  exit 0
fi

# === Step 3: Split into KEEP and DELETE lists ===
WORK_DIR=$(mktemp -d -t buildah-cleanup-XXXXXXXX)
KEEP_FILE="$WORK_DIR/keep_ids.txt"
DELETE_FILE="$WORK_DIR/delete_ids.txt"

> "$KEEP_FILE"
> "$DELETE_FILE"

for i in "${!IMAGE_LIST[@]}"; do
  id=$(echo "${IMAGE_LIST[$i]}" | awk '{print $2}')
  if [ "$i" -lt "$KEEP_COUNT" ]; then
    echo "$id" >> "$KEEP_FILE"
  else
    echo "$id" >> "$DELETE_FILE"
  fi
done

echo "🆕 Keeping these image IDs:"
cat "$KEEP_FILE"

echo "🗑️ Deleting these image IDs:"
cat "$DELETE_FILE"

# === Step 4: Delete old images with sudo ===
if [[ -s "$DELETE_FILE" ]]; then
  while read -r id; do
    if [ -n "$id" ]; then
      echo "🗑️ Deleting image: $id"
      sudo buildah rmi -f "$id" || echo "⚠️ Failed to delete image $id"
    fi
  done < "$DELETE_FILE"
else
  echo "✅ No old images to delete."
fi

# === Step 5: Cleanup ===
rm -rf "$WORK_DIR"
echo "✅ Image cleanup complete."





# #!/bin/bash
# set -euo pipefail
# export BUILDAH_ISOLATION=chroot

# IMAGE_NAME="localhost/bhonebhone/fb-api"
# KEEP_COUNT=5

# echo "🧹 Cleaning up old images for $IMAGE_NAME, keeping only the latest $KEEP_COUNT"

# # Step 1: Get list of images sorted by created time (newest first)
# mapfile -t IMAGE_LIST < <(
#   buildah images --format '{{.Created}} {{.ID}} {{.Name}}:{{.Tag}}' |
#   grep "$IMAGE_NAME" |
#   sort -r
# )

# # Step 2: Split into IDs and manage keep/delete sets
# mkdir -p /tmp/buildah-cleanup
# KEEP_FILE="/tmp/buildah-cleanup/keep_ids.txt"
# DELETE_FILE="/tmp/buildah-cleanup/delete_ids.txt"

# > "$KEEP_FILE"
# > "$DELETE_FILE"

# for i in "${!IMAGE_LIST[@]}"; do
#   id=$(echo "${IMAGE_LIST[$i]}" | awk '{print $2}')
#   if [ "$i" -lt "$KEEP_COUNT" ]; then
#     echo "$id" >> "$KEEP_FILE"
#   else
#     echo "$id" >> "$DELETE_FILE"
#   fi
# done

# echo "🆕 Keeping these image IDs:"
# cat "$KEEP_FILE"

# echo "🗑️ Deleting these image IDs:"
# cat "$DELETE_FILE"

# # Step 3: Delete old image IDs
# if [[ -s "$DELETE_FILE" ]]; then
#   while read -r id; do
#     if [ -n "$id" ]; then
#       echo "🗑️ Deleting image: $id"
#       buildah rmi -f "$id" || echo "⚠️ Failed to delete image $id"
#     fi
#   done < "$DELETE_FILE"
# else
#   echo "✅ No old images to delete."
# fi

# # Step 4: Cleanup
# rm -rf /tmp/buildah-cleanup

# echo "✅ Image cleanup complete."
