import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const api = {
    // Job operations
    spawnJob: async (task, projectPath) => {
        const response = await apiClient.post('/jobs/spawn', {
            task,
            project_path: projectPath,
            phase: 'I',
        });
        return response.data;
    },

    listJobs: async (limit = 50, status = null) => {
        const params = { limit };
        if (status) params.status = status;
        const response = await apiClient.get('/jobs', { params });
        return response.data;
    },

    getJobStatus: async (jobId) => {
        const response = await apiClient.get(`/jobs/${jobId}/status`);
        return response.data;
    },

    getJobTelemetry: async (jobId) => {
        const response = await apiClient.get(`/jobs/${jobId}/telemetry`);
        return response.data;
    },

    getAuditReport: async (jobId) => {
        const response = await apiClient.get(`/jobs/${jobId}/audit`);
        return response.data;
    },

    approveJob: async (jobId, comment = null) => {
        const response = await apiClient.post(`/jobs/${jobId}/approve`, {
            approved: true,
            comment,
        });
        return response.data;
    },

    rejectJob: async (jobId, comment) => {
        const response = await apiClient.post(`/jobs/${jobId}/approve`, {
            approved: false,
            comment,
        });
        return response.data;
    },

    // WebSocket for live streaming
    createWebSocket: (jobId) => {
        const wsUrl = API_BASE_URL.replace('http', 'ws');
        return new WebSocket(`${wsUrl}/jobs/${jobId}/stream`);
    },
};
