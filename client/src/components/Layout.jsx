import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';

export default function Layout() {
    const navigate = useNavigate();
    const location = useLocation();
    const token = localStorage.getItem('token');
    const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('conversationId');
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-gray-50">
        {!isAuthPage && (
            <nav className="bg-white shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                <div className="flex">
                    <div className="flex-shrink-0 flex items-center">
                    <Link to="/" className="text-xl font-bold text-indigo-600">
                        AI Chat
                    </Link>
                    </div>
                </div>
                <div className="flex items-center">
                    {token ? (
                    <button
                        onClick={handleLogout}
                        className="ml-4 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                    >
                        ログアウト
                    </button>
                    ) : (
                    <>
                        <Link
                        to="/login"
                        className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                        >
                        ログイン
                        </Link>
                        <Link
                        to="/register"
                        className="ml-4 px-4 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-900"
                        >
                        登録
                        </Link>
                    </>
                    )}
                </div>
                </div>
            </div>
            </nav>
        )}
        <main>
            <Outlet />
        </main>
        </div>
    );
} 