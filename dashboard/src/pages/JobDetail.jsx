import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import Telemetry from '../components/Telemetry'
import Terminal from '../components/Terminal'
import './JobDetail.css'

function JobDetail() {
    const { jobId } = useParams()
    const [job, setJob] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadJobDetails()
        const interval = setInterval(loadJobDetails, 2000)
        return () => clearInterval(interval)
    }, [jobId])

    const loadJobDetails = async () => {
        try {
            const data = await api.getJobStatus(jobId)
            setJob(data)
            setLoading(false)
        } catch (err) {
            console.error('Failed to load job:', err)
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="loading">Loading job details...</div>
    }

    if (!job) {
        return <div className="error">Job not found</div>
    }

    return (
        <div className="job-detail-container">
            <div className="job-detail-header">
                <div>
                    <Link to="/" className="back-link">← Back to Jobs</Link>
                    <h2>Job Details</h2>
                    <p className="job-id">ID: {jobId}</p>
                </div>
                <span className={`status-badge status-${job.status}`}>
                    {job.status.replace('_', ' ')}
                </span>
            </div>

            <div className="job-info card">
                <h3>Task</h3>
                <p>{job.task}</p>
                <div className="job-meta">
                    <span>Created: {new Date(job.created_at).toLocaleString()}</span>
                    {job.completed_at && (
                        <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>
                    )}
                </div>
            </div>

            {job.status === 'awaiting_approval' && (
                <div className="review-alert card">
                    <h3>⏳ Ready for Review</h3>
                    <p>The Builder and Checker agents have completed their work. Please review the changes before approving.</p>
                    <Link to={`/jobs/${jobId}/review`} className="btn btn-primary">
                        Go to Review →
                    </Link>
                </div>
            )}

            <div className="telemetry-section">
                <Telemetry jobId={jobId} />
            </div>

            <div className="terminal-section">
                <Terminal jobId={jobId} />
            </div>

            {job.error_message && (
                <div className="error-section card">
                    <h3>❌ Error</h3>
                    <pre>{job.error_message}</pre>
                </div>
            )}
        </div>
    )
}

export default JobDetail
