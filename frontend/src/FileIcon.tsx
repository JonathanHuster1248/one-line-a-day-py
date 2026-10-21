// Generic document icon, used wherever a file can't be shown as an image
// (PDFs, failed thumbnails, previews the browser can't render such as HEIC).
export function FileIcon() {
    return (
        <svg className="file-icon" viewBox="0 0 24 24" width="32" height="32" aria-hidden="true" focusable="false">
            <path
                d="M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm7 1.5V9h5.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
            />
        </svg>
    );
}
