import { createBrowserRouter, Navigate } from 'react-router-dom';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Chat from '../pages/Chat';
import PrivateRoute from '../components/PrivateRoute';

export const router = createBrowserRouter([
    {
        path: '/',
        element: <Navigate to="/login" replace />,
    },
    {
        path: '/login',
        element: <Login />,
    },
    {
        path: '/register',
        element: <Register />,
    },
    {
        path: '/chat',
        element: <PrivateRoute><Chat /></PrivateRoute>,
    },
]); 