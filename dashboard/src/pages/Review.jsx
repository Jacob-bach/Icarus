import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import DiffViewer from '../components/DiffViewer'
import './Review.css'

function Review() {
    const { jobId } = useParams()
    const navigate = useNavigate()
    const [job, setJob] = useState(null)
    const [auditReport, setAuditReport] = useState(null)
    const [comment, setComment] = useState('')
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        loadReviewData()
    }, [jobId])

    const loadReviewData = async () => {
        try {
            const [jobData, auditData] = await Promise.all([
                api.getJobStatus(jobId),
                api.getAuditReport(jobId).catch(() => null),
            ])
            setJob(jobData)
            setAuditReport(auditData)
            setLoading(false)
        } catch (err) {
            console.error('Failed to load review data:', err)
            setLoading(false)
        }
    }

    const handleApprove = async () => {
        if (!confirm('Are you sure you want to approve this job?')) return

        setSubmitting(true)
        try {
            await api.approveJob(jobId, comment || null)
            alert('Job approved! Changes will be committed to Git.')
            navigate('/')
        } catch (err) {
            alert('Failed to approve job: ' + err.message)
            setSubmitting(false)
        }
    }

    const handleReject = async () => {
        if (!confirm('Are you sure you want to reject this job? This will clean up all changes.')) return

        setSubmitting(true)
        try {
            await api.rejectJob(jobId, comment || 'Rejected by user')
            alert('Job rejected and cleaned up.')
            navigate('/')
        } catch (err) {
            alert('Failed to reject job: ' + err.message)
            setSubmitting(false)
        }
    }

    if (loading) {
        return <div className="loading">Loading review data...</div>
    }

    if (!job) {
        return <div className="error">Job not found</div>
    }

    return (
        <div className="review-container">
            <div className="review-header">
                <h2>Code Review</h2>
                <p className="job-id">Job ID: {jobId}</p>
            </div>

            <div className="task-info card">
                <h3>Original Task</h3>
                <p>{job.task}</p>
            </div>

            {auditReport && (
                <div className="audit-report card">
                    <h3>📋 Audit Report</h3>
                    <div className="audit-summary">
                        <p className="summary-text">{auditReport.audit_report.summary}</p>
                    </div>

                    {auditReport.audit_report.static_analysis && (
                        <div className="audit-section">
                            <h4>Static Analysis</h4>
                            <pre>{JSON.stringify(auditReport.audit_report.static_analysis, null, 2)}</pre>
                        </div>
                    )}

                    {auditReport.audit_report.security_scan && (
                        <div className="audit-section">
                            <h4>Security Scan</h4>
                            <pre>{JSON.stringify(auditReport.audit_report.security_scan, null, 2)}</pre>
                        </div>
                    )}

                    {auditReport.audit_report.logic_verification && (
                        <div className="audit-section">
                            <h4>Logic Verification</h4>
                            <p>Files created: {auditReport.audit_report.logic_verification.files_created}</p>
                            <ul>
                                {auditReport.audit_report.logic_verification.file_list?.map((file, idx) => (
                                    <li key={idx}>{file}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            <div className="diff-section">
                <DiffViewer jobId={jobId} />
            </div>

            <div className="review-actions card">
                <h3>Decision</h3>
                <div className="form-group">
                    <label>Comment (optional)</label>
                    <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Add any comments about your decision..."
                        rows={3}
                    />
                </div>

                <div className="action-buttons">
                    <button
                        className="btn btn-success"
                        onClick={handleApprove}
                        disabled={submitting}
                    >
                        ✅ Approve & Commit
                    </button>
                    <button
                        className="btn btn-danger"
                        onClick={handleReject}
                        disabled={submitting}
                    >
                        ❌ Reject & Cleanup
                    </button>
                </div>
            </div>
        </div>
    )
}

export default Review
