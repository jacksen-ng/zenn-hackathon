import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatService } from '../services/chatService';
import ChatInput from '../components/chatInput';
import '../styles/chat.css';
import { api, logout, uploadDocument } from '../services/api';

export default function Chat() {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [chatHistory, setChatHistory] = useState([]);
    const [currentChatIndex, setCurrentChatIndex] = useState(0);
    const [isEditingName, setIsEditingName] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [useRAG, setUseRAG] = useState(false);
    const [currentDocumentId, setCurrentDocumentId] = useState(null);
    const [documents, setDocuments] = useState([]);
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();
    
    const userData = JSON.parse(sessionStorage.getItem('userData'));
    
    useEffect(() => {
        if (!userData?.token) {
        navigate('/login');
        return;
        }
        loadConversations();
        loadUserDocuments();
    }, []);
    
    const loadConversations = async () => {
        try {
        if (!userData?.userId) {
            throw new Error('User ID not found');
        }
        const response = await chatService.getConversations(userData.userId);
        if (response.data?.conversations) {
            const sortedConversations = response.data.conversations
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map(conv => ({
                name: conv.title,
                id: conv.id,
                messages: [],
                created_at: conv.created_at
            }));
            setChatHistory(sortedConversations);
            if (sortedConversations.length > 0) {
            setCurrentChatIndex(0);
            await loadConversationHistory(sortedConversations[0].id);
            }
        }
        } catch (error) {
        console.error('Error loading conversations:', error);
        if (error.response?.status === 401) {
            navigate('/login');
        }
        }
    };
    
    const loadConversationHistory = async (conversationId) => {
        try {
        const response = await chatService.getMessages(conversationId);
        if (response?.messages && Array.isArray(response.messages)) {
            setMessages(response.messages);
            scrollToBottom();
        } else {
            setMessages([]);
        }
        } catch (error) {
        console.error('Error loading messages:', error);
        setMessages([{
            text: 'メッセージの読み込みに失敗しました',
            type: 'error',
            timestamp: new Date()
        }]);
        }
    };
    
    const handleNewChat = async () => {
        try {
        const response = await chatService.createConversation();
        if (response.data?.id) {
            const newChat = {
            name: `新しいチャット ${new Date().toLocaleString('ja-JP')}`,
            id: response.data.id,
            messages: [],
            created_at: new Date()
            };
            setChatHistory(prev => [newChat, ...prev]);
            setCurrentChatIndex(0);
            setMessages([]);
        }
        } catch (error) {
        console.error('Error creating new chat:', error);
        if (error.response?.status === 401) {
            navigate('/login');
        }
        }
    };
    
    const handleChatClick = async (index) => {
        setCurrentChatIndex(index);
        await loadConversationHistory(chatHistory[index].id);
    };
    
    const handleRightClick = (e, index) => {
        e.preventDefault();
        setIsEditingName(index);
    };
    
    const handleNameChange = (index, newName) => {
        setChatHistory(prev => {
        const updated = [...prev];
        updated[index].name = newName;
        return updated;
        });
    };
    
    const handleNameConfirm = (index, e) => {
        if (e.key === "Enter" || e.type === "blur") {
        setIsEditingName(null);
        }
    };
    
    const toggleModal = () => {
        setIsModalOpen(!isModalOpen);
    };
    
    const handleToggleRAG = () => {
        setUseRAG(prev => !prev);
    };
    
    const handlePDFInsert = () => {
        document.getElementById('file-upload').click();
    };
    
    const loadUserDocuments = async () => {
        try {
        const response = await fetch(`/api/documents/${userData.userId}`, {
            headers: {
            'Authorization': `Bearer ${userData.token}`
            }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.documents && data.documents.length > 0) {
            setDocuments(data.documents);
            setCurrentDocumentId(data.documents[0].id);
            }
        }
        } catch (error) {
        console.error('Error loading documents:', error);
        }
    };
    
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        // 检查文件大小（2MB限制）
        if (file.size > 2 * 1024 * 1024) {
            alert('ファイルサイズが大きすぎます。2MB以下のファイルを選択してください。');
            return;
        }

        // 检查文件类型
        const allowedTypes = ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
            alert('サポートされていないファイル形式です。PDF、TXT、DOC、DOCXファイルのみ対応しています。');
            return;
        }

        try {
            const response = await uploadDocument(file, userData.userId);
            if (response.id) {
                setCurrentDocumentId(response.id);
                setDocuments(prev => [...prev, {
                    id: response.id,
                    name: file.name
                }]);
                setUseRAG(true);
                alert("アップロード成功しました");
            } else {
                throw new Error("ドキュメントの処理に失敗しました");
            }
        } catch (error) {
            console.error("Upload error:", error);
            alert(`アップロード失敗: ${error.response?.data?.detail || error.message}`);
        } finally {
            // リセットファイル入力
            event.target.value = '';
        }
    };
    
    const sendMessageHandler = async (text) => {
        if (!text.trim()) return;
        setIsLoading(true);
        try {
        const newMessage = { text, type: 'user', timestamp: new Date() };
        setMessages(prev => [...prev, newMessage]);
        
        const response = await chatService.sendMessage(
            text, 
            chatHistory[currentChatIndex].id, 
            useRAG, 
            currentDocumentId
        );
        
        if (response?.data?.response) {
            setMessages(prev => [...prev, {
            text: response.data.response,
            type: 'bot',
            timestamp: new Date()
            }]);
        } else {
            setMessages(prev => [...prev, {
            text: "エラーが発生しました。もう一度お試しください。",
            type: 'error',
            timestamp: new Date()
            }]);
        }
        } catch (error) {
        console.error('Error sending message:', error);
        setMessages(prev => [...prev, {
            text: `エラー: ${error.message || 'メッセージの送信に失敗しました'}`,
            type: 'error',
            timestamp: new Date()
        }]);
        } finally {
        setIsLoading(false);
        scrollToBottom();
        }
    };
    
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleLogout = async () => {
        try {
        await logout();
        sessionStorage.clear();
        navigate('/login', { replace: true });
        } catch (error) {
        console.error('Logout error:', error);
        sessionStorage.clear();
        navigate('/login', { replace: true });
        }
    };

    const handleDeleteChat = async (chatId, e) => {
        e.stopPropagation();
        try {
        const response = await fetch(`/api/conversations/${chatId}`, {
            method: 'DELETE',
            headers: {
            'Authorization': `Bearer ${userData.token}`
            }
        });
        
        if (response.ok) {
            setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
            if (currentChatIndex === chatHistory.findIndex(chat => chat.id === chatId)) {
            setCurrentChatIndex(0);
            setMessages([]);
            }
        }
        } catch (error) {
        console.error('Error deleting chat:', error);
        }
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
        }).replace(/\//g, '-');
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    return (
        <>
        <div className="chatbot-wrapper">
            <div className="chatbot-container">
            <div className="chatbot-sidebar">
                <h2>新木場PJ</h2>
                <button className="new-chat-button" onClick={handleNewChat}>
                新規チャット
                </button>
                <ul className="chat-history">
                {chatHistory.map((chat, index) => (
                    <li
                    key={index}
                    onClick={() => handleChatClick(index)}
                    onContextMenu={(e) => handleRightClick(e, index)}
                    className={index === currentChatIndex ? "active" : ""}
                    >
                    {isEditingName === index ? (
                        <input
                        type="text"
                        value={chat.name}
                        onChange={(e) => handleNameChange(index, e.target.value)}
                        onBlur={(e) => handleNameConfirm(index, e)}
                        onKeyDown={(e) => handleNameConfirm(index, e)}
                        autoFocus
                        />
                    ) : (
                        <>
                        <span className="chat-title">
                            {chat.name}
                        </span>
                        <button
                            className="delete-btn"
                            onClick={(e) => handleDeleteChat(chat.id, e)}
                        >
                            削除
                        </button>
                        </>
                    )}
                    </li>
                ))}
                </ul>
                <button className="logout-btn" onClick={handleLogout}>
                ログアウト
                </button>
            </div>

            <div className="chatbot-main">
                <div className="chatbot-header">
                {chatHistory[currentChatIndex]?.name} {chatHistory[currentChatIndex]?.created_at ? formatTimestamp(chatHistory[currentChatIndex].created_at) : ''}
                <div className="rag-toggle">
                    <label className="rag-switch">
                    <input
                        type="checkbox"
                        checked={useRAG}
                        onChange={handleToggleRAG}
                    />
                    <span className="rag-slider"></span>
                    </label>
                    <span className="rag-label">
                    RAGモード {useRAG ? 'ON' : 'OFF'}
                    </span>
                </div>
                </div>
                
                {useRAG && (
                <div className="rag-mode-badge">
                    <span className="rag-icon"></span>
                    RAGモード有効
                </div>
                )}
                
                <div className="chatbot-messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`message-row ${msg.type === 'user' ? 'user-message' : 'bot-message'}`}>
                    <div className={`message ${msg.type === 'user' ? 'user-message' : 'bot-message'}`}>
                        {msg.text}
                    </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
                </div>
                <div className="chatbot-input">
                <ChatInput 
                    onSend={sendMessageHandler} 
                    isLoading={isLoading}
                    onToggleRAG={handleToggleRAG}
                    useRAG={useRAG}
                />
                </div>
            </div>
            </div>
        </div>

        <div className="floating-action-button" onClick={toggleModal}>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
        </div>

        {isModalOpen && (
            <div className="modal">
            <div className="modal-content">
                <div className="modal-header">
                <h2>ユーザー設定</h2>
                </div>
                
                <div className="user-info-section">
                <div className="user-info-item">
                    <span className="user-info-label">ユーザー名</span>
                    <span className="user-info-value">{userData?.username}</span>
                </div>
                <div className="user-info-item">
                    <span className="user-info-label">メールアドレス</span>
                    <span className="user-info-value">{userData?.email}</span>
                </div>
                </div>

                <div className="pdf-section">
                <div className="pdf-section-header">
                    <h3>PDFアップロード</h3>
                    <button className="upload-button" onClick={handlePDFInsert}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 5v14M5 12h14" strokeLinecap="round"/>
                    </svg>
                    PDFをアップロード
                    </button>
                </div>
                <div className="documents-list">
                    <h4>アップロード済みの文書</h4>
                    {documents.length > 0 ? (
                    documents.map((doc, index) => (
                        <div key={index} className="document-item">
                        <span>{doc.name}</span>
                        <button 
                            className={`select-document-btn ${currentDocumentId === doc.id ? 'active' : ''}`}
                            onClick={() => setCurrentDocumentId(doc.id)}
                        >
                            選択
                        </button>
                        </div>
                    ))
                    ) : (
                    <p>アップロードされた文書はありません</p>
                    )}
                </div>
                </div>

                <button className="close-modal" onClick={toggleModal}>
                閉じる
                </button>
            </div>
            </div>
        )}

        <input
            type="file"
            id="file-upload"
            onChange={handleFileUpload}
            accept=".pdf,.txt,.doc,.docx"
            style={{ display: 'none' }}
        />
        </>
    );
}