import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { register } from '../services/api';
import '../styles/main.css';

export default function Register() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        
        try {
            await register(email, password);
            // Registration successful, redirect to login
            navigate('/login');
        } catch (err) {
            console.error('Registration error:', err);
            const detail =
                typeof err.response?.data?.detail === 'object'
                    ? JSON.stringify(err.response.data.detail)
                    : err.response?.data?.detail;
            setError(detail || 'Registration failed. Please try again.');
        }
    };

    return (
        <div className="register-container">
            <div className="register-box">
                {/* 上部の説明 */}
                <div className="register-header">
                    <h1 className="auth-title">Join Us Today!</h1>
                    <p className="auth-description">
                        Create your account and start your journey with us!
                    </p>
                </div>

                {/* 新規登録フォーム */}
                <div className="register-content">
                    <h2 className="auth-header">Sign Up</h2>
                    <form className="auth-form" onSubmit={handleSubmit}>
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
                            SIGN UP
                        </button>
                    </form>
                    {/* "Already have an account? Sign in here." を Sign Up の下に配置 */}
                    <p className="no-account">
                        Already have an account?{" "}
                        <span className="signup-link" onClick={() => navigate('/login')}>
                            Sign in here.
                        </span>
                    </p>
                </div>
            </div>
        </div>
    );
}