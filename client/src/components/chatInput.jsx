import { useState, useRef } from 'react';

export default function ChatInput({ 
    onSend, 
    isLoading, 
    onToggleRAG,
    useRAG,
    hasDocument
}) {
    const [message, setMessage] = useState('');
    const textareaRef = useRef(null);

    const handleSend = () => {
    if (message.trim() && !isLoading) {
        onSend(message);
        setMessage('');
        if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        handleSend();
    }
    };

    const autoResize = () => {
    const textarea = textareaRef.current;
    if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
    };

    return (
    <div className="input-wrapper">
        <div className="input-container">
            <button 
            className={`mode-toggle ${useRAG ? 'active' : ''}`} 
            onClick={onToggleRAG}
            disabled={!hasDocument}
            title={!hasDocument ? "ドキュメントをアップロードしてください" : ""}
            >
            RAG
            </button>
            <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
                setMessage(e.target.value);
                autoResize();
            }}
            onKeyDown={handleKeyPress}
            placeholder="メッセージを入力..."
            disabled={isLoading}
            rows={1}
            />
            <button 
            className="send-button"
            onClick={handleSend}
            disabled={isLoading || !message.trim()}
            >
            送信
            </button>
        </div>
        </div>
    );
}