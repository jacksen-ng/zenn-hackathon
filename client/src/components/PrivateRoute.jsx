import { Navigate } from 'react-router-dom';

export default function PrivateRoute({ children }) {
    const userData = JSON.parse(sessionStorage.getItem('userData'));

    if (!userData?.token) {
        return <Navigate to="/login" replace />;
    }

    return children;
} 