// CodeInspector — modal overlay showing raw file content fetched from /api/file.
// Closes on backdrop click or the ✕ button. Renders nothing when no file is open.

interface Props {
  file: string | null;
  content: string;
  onClose: () => void;
}

export default function CodeInspector({ file, content, onClose }: Props) {
  if (!file) return null;
  return (
    <div className="viewer-overlay" onClick={onClose}>
      <div className="viewer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="viewer-header">
          <span>{file}</span>
          <button className="icon-btn" onClick={onClose}>
            ✕
          </button>
        </div>
        <pre className="viewer-content">{content}</pre>
      </div>
    </div>
  );
}
