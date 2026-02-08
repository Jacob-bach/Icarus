import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import './JobList.css'

function JobList() {
    const [jobs, setJobs] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [newTask, setNewTask] = useState('')
    const [newProjectPath, setNewProjectPath] = useState('/workspace')
    const [showCreateForm, setShowCreateForm] = useState(false)

    useEffect(() => {
        loadJobs()
        const interval = setInterval(loadJobs, 5000) // Refresh every 5 seconds
        return () => clearInterval(interval)
    }, [])

    const loadJobs = async () => {
        try {
            const data = await api.listJobs()
            setJobs(data)
            setLoading(false)
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    const handleCreateJob = async (e) => {
        e.preventDefault()
        try {
            await api.spawnJob(newTask, newProjectPath)
            setNewTask('')
            setNewProjectPath('/workspace')
            setShowCreateForm(false)
            loadJobs()
        } catch (err) {
            alert('Failed to create job: ' + err.message)
        }
    }

    if (loading) {
        return <div className="loading">Loading jobs...</div>
    }

    if (error) {
        return <div className="error">Error: {error}</div>
    }

    return (
        <div className="job-list-container">
            <div className="header-section">
                <h2>Active Jobs</h2>
                <button className="btn btn-primary" onClick={() => setShowCreateForm(!showCreateForm)}>
                    {showCreateForm ? 'Cancel' : '+ New Job'}
                </button>
            </div>

            {showCreateForm && (
                <form className="create-job-form card" onSubmit={handleCreateJob}>
                    <h3>Create New Job</h3>
                    <div className="form-group">
                        <label>Task Description</label>
                        <textarea
                            value={newTask}
                            onChange={(e) => setNewTask(e.target.value)}
                            placeholder="e.g., Create a FastAPI endpoint for user authentication"
                            rows={4}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Project Path</label>
                        <input
                            type="text"
                            value={newProjectPath}
                            onChange={(e) => setNewProjectPath(e.target.value)}
                            placeholder="/workspace"
                            required
                        />
                    </div>
                    <button type="submit" className="btn btn-success">Launch Job</button>
                </form>
            )}

            <div className="jobs-grid">
                {jobs.length === 0 ? (
                    <div className="empty-state">
                        <p>No jobs yet. Create your first autonomous coding task!</p>
                    </div>
                ) : (
                    jobs.map((job) => (
                        <Link to={`/jobs/${job.job_id}`} key={job.job_id} className="job-card card">
                            <div className="job-header">
                                <span className={`status-badge status-${job.status}`}>
                                    {job.status.replace('_', ' ')}
                                </span>
                                <span className="job-date">
                                    {new Date(job.created_at).toLocaleString()}
                                </span>
                            </div>
                            <div className="job-body">
                                <h3>{job.task}</h3>
                                <p className="job-id">Job ID: {job.job_id}</p>
                            </div>
                            {job.status === 'awaiting_approval' && (
                                <div className="job-action">
                                    <span className="review-required">👁️ Review Required</span>
                                </div>
                            )}
                        </Link>
                    ))
                )}
            </div>
        </div>
    )
}

export default JobList
