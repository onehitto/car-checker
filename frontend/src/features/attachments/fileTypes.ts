/** File types accepted by the API (10 MB maximum). */
export const IMAGE_TYPES = "image/jpeg,image/png,image/webp,image/heic";
export const FILE_TYPES = `application/pdf,${IMAGE_TYPES}`;
export const MAX_FILE_SIZE = 10 * 1024 * 1024;
