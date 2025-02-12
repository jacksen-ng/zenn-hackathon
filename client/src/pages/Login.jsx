import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../services/api';
import '../styles/main.css';

export default function Login() {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const data = await login(email, password);
            
            if (data && data.token) {
                // Store complete user data
                const userData = {
                    token: data.token,
                    userId: data.user_id,
                    email: data.email,
                    conversationId: data.conversation_id
                };
                
                // Store in sessionStorage
                sessionStorage.setItem('userData', JSON.stringify(userData));
                
                // Navigate to chat
                navigate('/chat', { replace: true });
            } else {
                setError('ログインに失敗しました');
            }
        } catch (err) {
            console.error('Login error:', err);
            // Convert error detail to a string if it is an object (e.g. validation error)
            const detail =
                typeof err.response?.data?.detail === 'object'
                    ? JSON.stringify(err.response.data.detail)
                    : err.response?.data?.detail;
            setError(detail || 'メールアドレスまたはパスワードが正しくありません');
        }
    };

    return (
        <div className="auth-container">
            {/* Left side: App description */}
            <div className="auth-info">
                <h1 className="auth-title">Welcome to 新木場PJ</h1>
                <p className="auth-description">
                    新木場PJ uses an interactive chat user interface to interact with AI and help you efficiently explore documents.
                </p>
            </div>

            {/* Right side: Login Form */}
            <div className="auth-login">
                <h2 className="auth-header">Login</h2>
                <form className="auth-form" onSubmit={handleLogin}>
                    <input
                        type="email"
                        placeholder="Email"
                        className="auth-input"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        className="auth-input"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    {error && <p className="error-text">{error}</p>}
                    <button type="submit" className="auth-btn">
                        SIGN IN
                    </button>
                </form>
                <p className="no-account">
                    Don't have an account?{" "}
                    <span className="signup-link" onClick={() => navigate('/register')}>
                        Create one here.
                    </span>
                </p>
            </div>
        </div>
    );
}
