export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Keep in sync with the backend: MAX_ATTACHMENTS_PER_ENTRY in
// one_line_day_py/src/data/db.py and MAX_FILE_BYTES in
// one_line_day_py/src/services/attachments.py. The backend enforces both;
// these only let the UI reject early with a clearer message.
export const MAX_ATTACHMENTS_PER_ENTRY = 5;
export const MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024;
