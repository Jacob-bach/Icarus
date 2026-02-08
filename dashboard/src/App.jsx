import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import JobList from './pages/JobList'
import JobDetail from './pages/JobDetail'
import Review from './pages/Review'
import './App.css'

function App() {
    return (
        <Router>
            <div className="app">
                <nav className="navbar">
                    <div className="navbar-brand">
                        <h1>🚀 ICARUS</h1>
                        <p className="subtitle">Autonomous Development Environment</p>
                    </div>
                    <ul className="nav-links">
                        <li><Link to="/">Jobs</Link></li>
                    </ul>
                </nav>

                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<JobList />} />
                        <Route path="/jobs/:jobId" element={<JobDetail />} />
                        <Route path="/jobs/:jobId/review" element={<Review />} />
                    </Routes>
                </main>

                <footer className="footer">
                    <p>ICARUS Phase I - The Speedster | v1.0.0</p>
                </footer>
            </div>
        </Router>
    )
}

export default App
