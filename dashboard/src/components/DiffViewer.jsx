import './DiffViewer.css'

function DiffViewer({ jobId }) {
    return (
        <div className="diff-viewer-container card">
            <h3>📝 Code Diff</h3>
            <div className="diff-placeholder">
                <p>File diffs will be displayed here.</p>
                <p className="note">
                    Note: In the current implementation, you would need to integrate with the
                    workspace volume to fetch and compare files. For Phase I, you can access
                    the workspace volume directly on the host machine to review changes.
                </p>
                <code className="volume-path">
                    Volume: icarus_workspace_{jobId}
                </code>
            </div>
        </div>
    )
}

export default DiffViewer
