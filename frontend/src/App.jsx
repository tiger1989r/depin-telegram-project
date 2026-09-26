import React, { useState, useEffect } from 'react';

// 🌐 تم ربط السيرفر السحابي الحقيقي الخاص بك على Render مباشرة
const BACKEND_URL = "https://depin-telegram-project.onrender.com"; 

function App() {
  const [isMining, setIsMining] = useState(false);
  const [balance, setBalance] = useState(0.00);
  const [telegramUser, setTelegramUser] = useState(null);

  useEffect(() => {
    // 🤖 قراءة بيانات مستخدم التلجرام الحقيقية فور فتح الـ Mini App
    if (window.Telegram && window.Telegram.WebApp) {
      const webApp = window.Telegram.WebApp;
      webApp.ready();
      webApp.expand(); // تمديد الشاشة بالكامل داخل الهاتف
      
      if (webApp.initDataUnsafe && webApp.initDataUnsafe.user) {
        setTelegramUser(webApp.initDataUnsafe.user);
        
        // جلب الرصيد الحقيقي المحفوظ للمستخدم من قاعدة البيانات فور فتح التطبيق
        fetch(`${BACKEND_URL}/api/ping-mining`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ telegram_id: webApp.initDataUnsafe.user.id })
        })
        .then(res => res.json())
        .then(data => { if(data.new_balance) setBalance(data.new_balance); })
        .catch(err => console.error("Error fetching initial balance:", err));
      }
    }
  }, []);

  // 🔄 الاتصال الحقيقي بالسيرفر لإرسال نبضات التعدين وحصد السنتات الفعّلة
  useEffect(() => {
    let interval = null;
    if (isMining && telegramUser) {
      interval = setInterval(() => {
        fetch(`${BACKEND_URL}/api/ping-mining`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ telegram_id: telegramUser.id })
        })
        .then(res => res.json())
        .then(data => {
          if (data.success && data.new_balance) {
            setBalance(data.new_balance); // تحديث الرصيد الفعلي القادم من السيرفر
          }
        })
        .catch(err => console.error("خطأ في الاتصال بالسيرفر:", err));
      }, 4000); // إرسال نبضة كل 4 ثوانٍ لحماية حزمة البيانات وهاتف المستخدم
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isMining, telegramUser]);

  const toggleMining = () => {
    setIsMining(!isMining);
  };

  return (
    <div style={{
      fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
      backgroundColor: '#17212b', // متوافق مع ثيم تلجرام المظلم
      color: '#fff', minHeight: '100vh',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '20px', textAlign: 'center'
    }}>
      <h2>شبكة التشغيل التشاركية السورية 🚀</h2>
      
      {telegramUser ? (
        <p style={{ color: '#64b5f6' }}>أهلاً بك، {telegramUser.first_name}</p>
      ) : (
        <p style={{ color: '#e57373' }}>⚠️ يرجى الفتح من داخل بوت التلجرام لتفعيل الحساب حياً</p>
      )}

      <div style={{
        backgroundColor: '#242f3d', borderRadius: '15px', padding: '30px',
        margin: '20px 0', width: '85%', boxShadow: '0 4px 15px rgba(0,0,0,0.3)'
      }}>
        <p style={{ fontSize: '18px', color: '#aaaaaa', margin: '0' }}>💰 رصيدك الحقيقي المحفوظ:</p>
        <h1 style={{ fontSize: '42px', color: '#4caf50', margin: '10px 0' }}>
          \${balance.toFixed(4)}
        </h1>
        <p style={{ fontSize: '14px', color: isMining ? '#4caf50' : '#e57373' }}>
          ● {isMining ? "جهازك متصل بالشبكة ويحقق أرباحاً فعلية..." : "التعدين متوقف حالياً"}
        </p>
      </div>

      <button 
        onClick={toggleMining}
        disabled={!telegramUser} // تعطيل الزر إذا تم الفتح خارج التلجرام لحماية السيرفر
        style={{
          backgroundColor: !telegramUser ? '#555' : isMining ? '#f44336' : '#2196f3',
          color: '#fff', border: 'none', borderRadius: '12px', padding: '15px 30px',
          fontSize: '18px', fontWeight: 'bold', cursor: telegramUser ? 'pointer' : 'not-allowed', width: '85%',
          boxShadow: '0 4px 10px rgba(0,0,0,0.2)'
        }}
      >
        {!telegramUser ? "افتح البوت أولاً" : isMining ? "🛑 إيقاف مشاركة البيانات" : "⚡ بدء التعدين ومشاركة الإنترنت"}
      </button>

      <p style={{ fontSize: '12px', color: '#707e8b', marginTop: '30px', width: '80%' }}>
        * بالتفعيل، أنت توافق صراحة على مشاركة جزء ضئيل جداً وآمن من حركة مرور الإنترنت الفائضة لديك مقابل نقاط مالية تُسجل مباشرة في محفظتك الخاصة.
      </p>
    </div>
  );
}

export default App;
