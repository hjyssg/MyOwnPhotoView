/**
 * Generate thumbnail URL for a media item
 * @param {Object} item - Media item with id, filepath, thumbnail_path
 * @returns {string} URL for thumbnail or original image
 */
export function getThumbnailUrl(item) {
  if (!item) return '';
  
  return item.thumbnail_path
    ? `/api/thumbnail?filepath=${encodeURIComponent(item.filepath)}&thumbnail_path=${item.thumbnail_path}`
    : `/api/media/image/${item.id}`;
}
