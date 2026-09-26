import React, { useState, useEffect } from 'react';

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || 'https://depin-telegram-project.onrender.com').replace(/\/+$/, '');
const STATUS_LABELS = {
  checking: 'جارٍ التحقق من الخدمة...',
  running: 'حاوية العميل تعمل',
  not_configured: 'رمز الوصول غير مضبوط',
  docker_unavailable: 'Docker غير متاح على الخادم',
  not_running: 'حاوية العميل متوقفة',
  error: 'تعذر تشغيل حاوية العميل',
  unavailable: 'تعذر الوصول إلى الخادم',
};

function App() {
  const [telegramUser] = useState(() => (
    typeof window === 'undefined' ? null : window.Telegram?.WebApp?.initDataUnsafe?.user ?? null
  ));
  const [serviceStatus, setServiceStatus] = useState('checking');

  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      const webApp = window.Telegram.WebApp;
      webApp.ready();
      webApp.expand();
    }
  }, []);

  useEffect(() => {
    const refreshStatus = () => {
      fetch(`${BACKEND_URL}/api/traffmonetizer/status`)
        .then((response) => {
          if (!response.ok) throw new Error('Status request failed');
          return response.json();
        })
        .then((data) => setServiceStatus(data.status))
        .catch(() => setServiceStatus('unavailable'));
    };

    refreshStatus();
    const statusInterval = window.setInterval(refreshStatus, 15000);
    return () => window.clearInterval(statusInterval);
  }, []);

  const serviceIsRunning = serviceStatus === 'running';

  return (
    <div style={{
      fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
      backgroundColor: '#17212b', color: '#fff', minHeight: '100vh',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '20px', textAlign: 'center'
    }}>
      <h2>TraffMonetizer للمشروع</h2>
      
      {telegramUser ? (
        <p style={{ color: '#64b5f6' }}>أهلاً بك، {telegramUser.first_name}</p>
      ) : (
        <p style={{ color: '#e57373' }}>⚠️ يرجى الفتح من داخل بوت التلجرام لتفعيل الحساب حياً</p>
      )}

      <div style={{
        backgroundColor: '#242f3d', borderRadius: '15px', padding: '30px',
        margin: '20px 0', width: '85%', boxShadow: '0 4px 15px rgba(0,0,0,0.3)'
      }}>
        <p style={{ fontSize: '18px', color: '#aaaaaa', margin: '0' }}>حالة خدمة الخادم:</p>
        <h1 style={{ fontSize: '30px', color: serviceIsRunning ? '#4caf50' : '#e57373', margin: '10px 0' }}>
          {STATUS_LABELS[serviceStatus] || STATUS_LABELS.unavailable}
        </h1>
        <p style={{ fontSize: '14px', color: '#aaaaaa', marginTop: '14px' }}>
          هذه خدمة مشتركة للمشروع؛ الأرباح تُسجّل في حساب TraffMonetizer المرتبط بالخادم، وليست أرصدة فردية لمستخدمي Telegram.
        </p>
      </div>

      <a
        href="https://app.traffmonetizer.com/"
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'inline-block', backgroundColor: '#2196f3', color: '#fff',
          borderRadius: '8px', padding: '13px 24px', fontSize: '16px',
          fontWeight: 'bold', textDecoration: 'none',
        }}
      >
        فتح لوحة TraffMonetizer
      </a>
    </div>
  );
}

export default App;
