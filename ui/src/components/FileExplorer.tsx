// FileExplorer — static workspace tree on the left. Clicking a source file opens
// it in the Code Inspector via the supplied callback (paths are /api/file-relative).

interface Props {
  onFileClick: (apiPath: string) => void;
}

const SOURCE_FILES: Array<[string, string]> = [
  ["polygons.py", "broken-python/polygons/polygons.py"],
  ["mathsquiz.py", "broken-python/mathsquiz/mathsquiz.py"],
  ["mathsquiz-step1.py", "broken-python/mathsquiz/mathsquiz-step1.py"],
  ["mathsquiz-step2.py", "broken-python/mathsquiz/mathsquiz-step2.py"],
  ["mathsquiz-step3.py", "broken-python/mathsquiz/mathsquiz-step3.py"],
];

export default function FileExplorer({ onFileClick }: Props) {
  return (
    <aside className="sidebar-left">
      <p className="panel-title">Workspace</p>
      <ul className="file-tree">
        <li>workspace/</li>
        <li className="i1">vault/</li>
        <li className="i2">graph.json</li>
        <li className="i2">hot.md</li>
        <li className="i1">target/</li>
        <li className="i2">broken-python/</li>
        {SOURCE_FILES.map(([label, path]) => (
          <li
            key={path}
            className="i3 file-item"
            onClick={() => onFileClick(path)}
          >
            {label}
          </li>
        ))}
        <li className="i1">root_cause_report.json</li>
        <li className="i1">token_efficiency_report.md</li>
      </ul>
    </aside>
  );
}
