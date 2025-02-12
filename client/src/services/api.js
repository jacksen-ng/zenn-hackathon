import axios from 'axios';

export const api = axios.create({
    baseURL: 'http://localhost:8080',
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use((config) => {
    const userData = JSON.parse(sessionStorage.getItem('userData'));
    if (userData?.token) {
        config.headers.Authorization = `Bearer ${userData.token}`;
    }
    return config;
});

export const login = async (email, password) => {
    try {
        const params = new URLSearchParams();
        params.append('username', email);
        params.append('password', password);

        const response = await api.post('/api/login', params.toString(), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        
        if (response.data && response.data.token) {
            const userData = {
                token: response.data.token,
                user_id: response.data.id,
                email: response.data.email,
                conversation_id: response.data.conversation_id
            };
            sessionStorage.setItem('userData', JSON.stringify(userData));
            return userData;
        } else {
            throw new Error('Invalid login response');
        }
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

export const register = async (email, password) => {
    const response = await api.post('/api/users', { email, password });
    return response.data;
};

export const logout = async () => {
    try {
        const userData = JSON.parse(sessionStorage.getItem('userData'));
        if (!userData) {
            console.warn('No user data found in session');
            return;
        }
        
        sessionStorage.clear();
        return { success: true };
        
    } catch (error) {
        console.error('Logout error:', error);
        sessionStorage.clear();
        throw error;
    }
};

export const sendMessage = async (text, conversationId, useRAG = false, documentId = null) => {
    try {
        const response = await api.post('/api/chat', { 
            text, 
            conversation_id: conversationId, 
            use_rag: useRAG, 
            document_id: documentId 
        });
        
        if (response.data && response.data.success) {
            return {
                data: {
                    response: response.data.response
                }
            };
        } else {
            throw new Error(response.data?.detail || 'Failed to get response');
        }
    } catch (error) {
        console.error('Error in sendMessage:', error);
        throw error;
    }
};

export const getMessages = async (conversationId) => {
    try {
        console.log('Fetching messages for conversation:', conversationId);
        const response = await api.get(`/api/conversations/${conversationId}/messages`);
        console.log('Messages response:', response.data);
        
        if (response.data && Array.isArray(response.data.messages)) {
            const messages = [];
            response.data.messages.forEach(msg => {
                if (msg.question) {
                    messages.push({
                        text: msg.question,
                        type: 'user',
                        timestamp: new Date(msg.created_at)
                    });
                }
                if (msg.response) {
                    messages.push({
                        text: msg.response,
                        type: 'bot',
                        timestamp: new Date(msg.created_at)
                    });
                }
            });
            return { messages };
        }
        console.warn('Unexpected messages format:', response.data);
        return { messages: [] };
    } catch (error) {
        console.error('Error fetching messages:', error);
        throw error;
    }
};

export const uploadDocument = async (file, ownerId) => {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('owner_id', ownerId);

        const response = await api.post('/api/upload-document', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        
        if (response.data) {
            return response.data;
        } else {
            throw new Error('Invalid upload response');
        }
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
};

export default api;