import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/auth';
import {
  LayoutDashboard, PenTool, History, BarChart3, LogOut,
  Menu, X, Zap, User
} from 'lucide-react';
import { useState } from 'react';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
    { path: '/editor', label: '新建内容', icon: PenTool },
    { path: '/history', label: '历史记录', icon: History },
    { path: '/analytics', label: '数据分析', icon: BarChart3 },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const NavLink = ({ item }: { item: typeof navItems[0] }) => {
    const isActive = location.pathname === item.path;
    return (
      <Link
        to={item.path}
        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
          isActive
            ? 'bg-[#ff2442] text-white shadow-lg shadow-red-200'
            : 'text-slate-600 hover:bg-slate-100'
        }`}
      >
        <item.icon className="w-5 h-5" />
        <span className="font-medium">{item.label}</span>
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-slate-200 z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#ff2442] rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white fill-current" />
          </div>
          <span className="font-bold text-slate-800">NoteTrial</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </header>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-30 bg-black/50" onClick={() => setMobileMenuOpen(false)}>
          <div className="absolute top-16 left-0 right-0 bg-white border-b border-slate-200 p-4 space-y-2" onClick={(e) => e.stopPropagation()}>
            {navItems.map((item) => (
              <NavLink key={item.path} item={item} />
            ))}
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-4 py-3 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium">退出登录</span>
            </button>
          </div>
        </div>
      )}

      <div className="hidden lg:flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
          {/* Logo */}
          <div className="h-16 flex items-center px-6 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#ff2442] rounded-xl flex items-center justify-center shadow-lg shadow-red-200">
                <Zap className="w-6 h-6 text-white fill-current" />
              </div>
              <div>
                <h1 className="font-bold text-slate-800">NoteTrial</h1>
                <p className="text-xs text-slate-400">内容 A/B 测试</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navItems.map((item) => (
              <NavLink key={item.path} item={item} />
            ))}
          </nav>

          {/* User */}
          <div className="p-4 border-t border-slate-100">
            <div className="flex items-center gap-3 mb-4 px-2">
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
                <User className="w-5 h-5 text-slate-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-slate-800 truncate">{user?.username || '用户'}</p>
                <p className="text-xs text-slate-400 truncate">{user?.email || ''}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 w-full px-3 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors text-sm"
            >
              <LogOut className="w-4 h-4" />
              退出登录
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 lg:p-8 pt-20 lg:pt-8">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile Content Area */}
      <main className="lg:hidden min-h-screen pt-16">
        <div className="p-4">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
