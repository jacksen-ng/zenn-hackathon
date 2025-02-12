import { api, sendMessage, getMessages } from './api';

export const chatService = {
    // Now no longer sending user_id in body. The backend derives the user from the token.
    async createConversation() {
        return await api.post('/api/conversations');
    },

    async sendMessage(text, conversationId, useRAG = false, documentId = null) {
        return await sendMessage(text, conversationId, useRAG, documentId);
    },

    async getConversations(userId) {
        const token = JSON.parse(sessionStorage.getItem('userData'))?.token;
        return await api.get(`/api/users/${userId}/conversations`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
    },

    async getMessages(conversationId) {
        return await getMessages(conversationId);
    }
};