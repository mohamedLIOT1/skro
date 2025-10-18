// Show a beautiful modal notification in the center of the screen
function showModal(message, type = 'info') {
    // Remove any existing modal
    document.querySelectorAll('.modal-notification').forEach(e => e.remove());
    const modal = document.createElement('div');
    modal.className = `modal-notification modal-${type}`;
    modal.innerHTML = `
        <div class="modal-content">
            <span class="modal-close" style="position:absolute;top:10px;left:20px;cursor:pointer;font-size:1.5rem;">&times;</span>
            <div class="modal-icon" style="font-size:2.5rem;margin-bottom:10px;">${type === 'success' ? '🎉' : type === 'error' ? '❌' : 'ℹ️'}</div>
            <div class="modal-message" style="font-size:1.2rem;line-height:1.7;">${message}</div>
        </div>
    `;
    Object.assign(modal.style, {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(30,34,54,0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000
    });
    const content = modal.querySelector('.modal-content');
    Object.assign(content.style, {
        background: 'white',
        color: '#222',
        borderRadius: '18px',
        padding: '36px 32px 28px 32px',
        minWidth: '320px',
        maxWidth: '90vw',
        boxShadow: '0 8px 40px rgba(88,101,242,0.18)',
        textAlign: 'center',
        position: 'relative',
        fontFamily: 'Cairo, sans-serif',
        border: type === 'success' ? '2px solid #57f287' : type === 'error' ? '2px solid #ed4245' : '2px solid #5865f2',
    });
    modal.querySelector('.modal-close').onclick = () => modal.remove();
    modal.onclick = e => { if (e.target === modal) modal.remove(); };
    document.body.appendChild(modal);
    setTimeout(() => { if (document.body.contains(modal)) modal.remove(); }, 4000);
}
// Configuration - Replace with your bot's actual values
const BOT_CONFIG = {
    CLIENT_ID: '1424342801801416834', // Replace with your bot's client ID
    PERMISSIONS: '274877975552', // Replace with your bot's permissions
    SUPPORT_SERVER: 'https://discord.gg/uNRbkvYmPD', // Replace with your support server invite code
    TOPGG_URL: 'https://top.gg/bot/1424342801801416834' // Replace with your Top.gg page
};

// Bot invite URL generator
function generateInviteUrl() {
    const baseUrl = 'https://discord.com/api/oauth2/authorize';
    const params = new URLSearchParams({
        'client_id': BOT_CONFIG.CLIENT_ID,
        'permissions': BOT_CONFIG.PERMISSIONS,
        'scope': 'bot applications.commands'
    });
    
    return `${baseUrl}?${params.toString()}`;
}

// Support server URL generator
function generateSupportUrl() {
    return `https://discord.gg/${BOT_CONFIG.SUPPORT_SERVER}`;
}


document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Initialize the application
function initializeApp() {
    updateYear();
    setupNavigation();
    setupButtons();
    setupAnimations();
    setupScrollEffects();
    setupFAQ();
    authInit();
    
    // Update stats if needed
    updateStats();
    
    console.log('🚀 سكرو موقع جاهز!');
}

// Update current year in footer
function updateYear() {
    const yearElement = document.getElementById('currentYear');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
}

// Setup navigation functionality
function setupNavigation() {
    const navbar = document.querySelector('.navbar');
    const navLinks = document.querySelectorAll('.nav-link');
    
    // Smooth scrolling for navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href.startsWith('#')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    const headerHeight = navbar.offsetHeight;
                    const targetPosition = targetElement.offsetTop - headerHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
    
    // Navbar scroll effect
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > 100) {
            navbar.style.background = 'rgba(11, 15, 26, 0.98)';
            navbar.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        } else {
            navbar.style.background = 'rgba(11, 15, 26, 0.95)';
            navbar.style.boxShadow = 'none';
        }
        
        lastScrollY = currentScrollY;
    });
}

// Setup button click handlers
function setupButtons() {
    const inviteButtons = [
        'inviteBtn',
        'inviteMainBtn', 
        'inviteCtaBtn'
    ];
    
    const supportButtons = [
        'supportBtn',
        'supportCtaBtn'
    ];
    
    // Setup invite buttons
    inviteButtons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (BOT_CONFIG.CLIENT_ID === 'YOUR_CLIENT_ID') {
                    showConfigWarning();
                    return;
                }
                
                // Add loading state
                this.classList.add('loading');
                this.style.pointerEvents = 'none';
                
                // Simulate loading and open invite URL
                setTimeout(() => {
                    window.open(generateInviteUrl(), '_blank', 'noopener,noreferrer');
                    this.classList.remove('loading');
                    this.style.pointerEvents = 'auto';
                }, 500);
                
                // Track button click
                trackButtonClick('invite', buttonId);
            });
        }
    });
    
    // Setup support buttons
    supportButtons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (BOT_CONFIG.SUPPORT_SERVER === 'YOUR_SUPPORT_SERVER') {
                    showConfigWarning();
                    return;
                }
                
                window.open(generateSupportUrl(), '_blank', 'noopener,noreferrer');
                trackButtonClick('support', buttonId);
            });
        }
    });
    
    // Setup Top.gg link
    const topggLink = document.getElementById('topggLink');
    if (topggLink) {
        topggLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (BOT_CONFIG.CLIENT_ID === 'YOUR_CLIENT_ID') {
                showConfigWarning();
                return;
            }
            
            window.open(BOT_CONFIG.TOPGG_URL, '_blank', 'noopener,noreferrer');
            trackButtonClick('topgg', 'topggLink');
        });
    }
}

// Show configuration warning
function showConfigWarning() {
    const message = `
⚠️ تحتاج لتكوين معلومات البوت أولاً!

في ملف script.js، استبدل:
• YOUR_CLIENT_ID - معرف البوت
• YOUR_PERMISSIONS - صلاحيات البوت
• YOUR_SUPPORT_SERVER - كود دعوة السيرفر

تحقق من التوثيق لمعرفة كيفية الحصول على هذه القيم.
    `;
    
    alert(message);
}

// Setup animations
function setupAnimations() {
    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animatedElements = document.querySelectorAll([
        '.feature-card',
        '.command-category', 
        '.faq-item',
        '.hero-content'
    ].join(','));
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    // Counter animation for stats
    animateCounters();
}

// Setup scroll effects
function setupScrollEffects() {
    const heroLogo = document.querySelector('.hero-logo-img');
    
    if (heroLogo) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;
            
            if (scrolled < window.innerHeight) {
                heroLogo.style.transform = `translateY(${rate}px)`;
            }
        });
    }
    
    // Parallax effect for hero background
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * 0.3;
            
            if (scrolled < hero.offsetHeight) {
                hero.style.backgroundPosition = `center ${rate}px`;
            }
        });
    }
}

// Setup FAQ functionality
function setupFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const summary = item.querySelector('.faq-question');
        
        summary.addEventListener('click', () => {
            // Close other FAQ items
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.hasAttribute('open')) {
                    otherItem.removeAttribute('open');
                }
            });
        });
    });
}

// Animate counter numbers
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const digits = counter.textContent.replace(/[^0-9]/g, '');
        if (!digits) return; // لا يوجد رقم بعد (؟ أو …)
        const target = parseInt(digits, 10);
        if (isNaN(target)) {
            console.warn('قيمة غير رقمية للعداد، سيتم تجاهلها:', counter.textContent);
            return;
        }
        const suffix = counter.textContent.replace(/[0-9]/g, '');
        let current = 0;
        const increment = Math.max(1, Math.ceil(target / 100));
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = current.toLocaleString() + suffix;
        }, 15);
    });
}

// Update stats (mock function - replace with real API calls)
function updateStats() {
    const elServers = document.getElementById('serverCount');
    const elPlayers = document.getElementById('playersCount');
    const elUsers = document.getElementById('usersRegistered');
    if (elServers) elServers.textContent = '…';
    if (elPlayers) elPlayers.textContent = '…';
    if (elUsers) elUsers.textContent = '…';
    // Try API first
    fetch('/api/stats')
        .then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
        .then(j => {
            const guilds = Number(j.guild_count);
            const players = Number(j.players_count || 0);
            const users = Number(j.users_registered || 0);
            if (elServers) elServers.textContent = (!isNaN(guilds) ? guilds : 0).toLocaleString();
            if (elPlayers) elPlayers.textContent = (!isNaN(players) ? players : 0).toLocaleString();
            if (elUsers) elUsers.textContent = (!isNaN(users) ? users : 0).toLocaleString();
            animateCounters();
        })
        .catch(err => {
            console.warn('فشل /api/stats، سنجرب servers.json', err);
            fetch('servers.json')
                .then(r => r.json())
                .then(d => {
                    const v = Number(d.servers);
                    if (elServers) elServers.textContent = (!isNaN(v) ? v : 0).toLocaleString();
                    // fallback: players/users unknown when offline
                    if (elPlayers) elPlayers.textContent = '0';
                    if (elUsers) elUsers.textContent = '0';
                    animateCounters();
                })
                .catch(e2 => {
                    console.error('فشل قراءة servers.json', e2);
                    if (elServers) elServers.textContent = '0';
                    if (elPlayers) elPlayers.textContent = '0';
                    if (elUsers) elUsers.textContent = '0';
                });
        });
}

// Track button clicks (for analytics)
function trackButtonClick(type, buttonId) {
    console.log(`Button clicked: ${type} (${buttonId})`);
    
    // Here you can add Google Analytics, Plausible, or any other analytics
    // Example with Google Analytics (gtag):
    // gtag('event', 'click', {
    //     event_category: 'button',
    //     event_label: `${type}_${buttonId}`,
    //     value: 1
    // });
}

// Utility function to copy text to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        return new Promise((resolve, reject) => {
            document.execCommand('copy') ? resolve() : reject();
            textArea.remove();
        });
    }
}

// Show notification/toast message (fallback to modal for important messages)
function showNotification(message, type = 'info', useModal = false) {
    if (useModal) {
        showModal(message, type);
        return;
    }
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '8px',
        color: 'white',
        fontSize: '14px',
        fontWeight: '600',
        zIndex: '1000',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease',
        maxWidth: '300px'
    });
    const colors = {
        info: '#5865f2',
        success: '#57f287',
        warning: '#fee75c',
        error: '#ed4245'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    document.body.appendChild(notification);
    setTimeout(() => { notification.style.transform = 'translateX(0)'; }, 100);
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => { if (document.body.contains(notification)) document.body.removeChild(notification); }, 300);
    }, 3000);
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    
    // In production, you might want to send errors to a logging service
    // like Sentry, LogRocket, etc.
});

// Service Worker registration (for PWA features)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment this if you want to add PWA features
        // navigator.serviceWorker.register('/sw.js')
        //     .then((registration) => {
        //         console.log('SW registered: ', registration);
        //     })
        //     .catch((registrationError) => {
        //         console.log('SW registration failed: ', registrationError);
        //     });
    });
}

// Export functions for external use (if needed)
window.BotWebsite = {
    generateInviteUrl,
    generateSupportUrl,
    copyToClipboard,
    showNotification,
    updateStats,
    fetchCurrentUser
};

// ---------------- Authentication & Dashboard ----------------
function authInit() {
    fetchCurrentUser().then(user => {
        if (user) {
            document.getElementById('loginBtn')?.setAttribute('style', 'display:none');
            document.getElementById('logoutBtn')?.setAttribute('style', 'display:inline-flex');
            document.getElementById('dashboardBtn')?.setAttribute('style', 'display:inline-flex');
            showWelcome(user);
        }
    });

    // Buy license and referral functionality moved to dashboard.html
}

function fetchCurrentUser() {
    return fetch('/api/auth/me')
        .then(r => r.json())
        .then(j => {
            if (j.authenticated) {
                window.__AUTH_USER_ID = j.user.id;
                return j.user;
            }
            console.info('لم يتم تسجيل الدخول (api/auth/me)');
            return null;
        })
        .catch(err => { console.warn('خطأ في جلب auth/me', err); return null; });
}

function showWelcome(user) {
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.style.display = 'block';
    
    // Set user name
    const userName = document.getElementById('userName');
    if (userName) userName.textContent = user.global_name || user.username || 'المستخدم';
    
    // Set user avatar
    const userAvatar = document.getElementById('userAvatar');
    if (userAvatar) {
        const avatarUrl = user.avatar 
            ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=256`
            : `https://cdn.discordapp.com/embed/avatars/${user.id % 5}.png`;
        userAvatar.src = avatarUrl;
    }

    // Load VIP status and enhance welcome message
    loadVipStatus(user);
}

async function loadVipStatus(user) {
    try {
        // Get user stats to check VIP status and owner status
        const response = await fetch(`/api/user/${user.id}/points`);
        if (!response.ok) return;
        
        const data = await response.json();
        const vipTier = data.vip_tier;
        
        // Check if user is owner
        const ownerResponse = await fetch('/api/owner-check/' + user.id);
        const isOwner = ownerResponse.ok && (await ownerResponse.json()).is_owner;
        
        enhanceWelcomeMessage(user, vipTier, isOwner, data.stats);
    } catch (error) {
        console.log('Could not load VIP status:', error);
    }
}

function enhanceWelcomeMessage(user, vipTier, isOwner, stats) {
    const welcomeSection = document.getElementById('welcome');
    const userName = user.global_name || user.username || 'المستخدم';
    
    let specialTitle = '';
    let specialGreeting = '';
    let specialStyle = '';
    let crownIcon = '';
    
    if (isOwner) {
        specialTitle = '👑 المطور الأساسي';
        specialGreeting = `أهلاً بالمدير 👑<br><span style="font-size:1.1em;color:#FFD700;font-weight:bold;">${userName}</span>`;
        specialStyle = `
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(255, 193, 7, 0.1) 100%);
            border: 2px solid gold;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        `;
        crownIcon = '👑';
    } else if (vipTier) {
        let tierInfo = getVipTierInfo(vipTier);
        specialTitle = `${tierInfo.icon} ${tierInfo.title}`;
        specialGreeting = `مرحباً بعضو الـ ${vipTier}، ${userName}! ${tierInfo.message}`;
        specialStyle = `
            background: ${tierInfo.gradient};
            border: 2px solid ${tierInfo.borderColor};
            box-shadow: 0 0 25px ${tierInfo.shadowColor};
        `;
        crownIcon = tierInfo.icon;
    } else {
        specialGreeting = `مرحباً، ${userName}! 👋`;
        specialStyle = '';
    }
    
    // Update welcome content with special styling
    welcomeSection.innerHTML = `
        <div class="container">
            <div class="welcome-content" style="text-align: center;">
                <div class="user-avatar" style="margin: 0 auto 20px; position: relative;">
                    <img id="userAvatar" src="${getAvatarUrl(user)}" alt="صورة المستخدم" 
                         style="width: 100px; height: 100px; border-radius: 50%; border: 4px solid var(--primary); box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);">
                    ${crownIcon ? `<div class="crown-badge" style="position: absolute; top: -10px; right: -10px; background: gold; border-radius: 50%; width: 35px; height: 35px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);">${crownIcon}</div>` : ''}
                </div>
                
                ${specialTitle ? `<div class="special-title" style="color: #666eea; font-weight: bold; margin-bottom: 10px; font-size: 1.1rem;">${specialTitle}</div>` : ''}
                
                <h2 class="welcome-title" style="font-size: 2rem; color: var(--text-primary); margin-bottom: 10px;">
                    ${specialGreeting}
                </h2>
                
                ${(isOwner || vipTier) ? `
                    <div class="vip-stats" style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin: 20px 0; backdrop-filter: blur(5px);">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; text-align: center;">
                            <div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: #fff;">${stats.points.toLocaleString()}</div>
                                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8);">النقاط</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: #fff;">${stats.wins}</div>
                                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8);">الانتصارات</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: bold; color: #fff;">${stats.credits.toFixed(1)}</div>
                                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8);">الكريدتس</div>
                            </div>
                        </div>
                    </div>
                ` : ''}
                
                <p class="welcome-subtitle" style="color: var(--text-secondary); font-size: 1.1rem; margin-bottom: 30px;">
                    ${(isOwner || vipTier) ? 'شكراً لدعمك المستمر للبوت! 💜' : 'نورت الموقع! تقدر دلوقتي تشوف كل إحصائياتك في لوحة التحكم'}
                </p>
                
                <div class="welcome-actions" style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                    <a href="/dashboard.html" class="btn btn-primary btn-large">
                        📊 لوحة التحكم الكاملة
                    </a>
                    <a href="#commands" class="btn btn-secondary">
                        🎮 استكشاف الأوامر
                    </a>
                    ${isOwner ? `<a href="#admin" class="btn" style="background: gold; color: black; font-weight: bold;">⚙️ إدارة البوت</a>` : ''}
                </div>
            </div>
        </div>
    `;
    
    // Apply special styling
    if (specialStyle) {
        welcomeSection.style.cssText += specialStyle;
    }
}

function getVipTierInfo(vipTier) {
    const tierMap = {
        'VIP Diamond': {
            icon: '💎',
            title: 'عضو ماسي',
            message: 'مرحباً بالعضو الماسي المميز!',
            gradient: 'linear-gradient(135deg, rgba(185, 242, 255, 0.15) 0%, rgba(0, 191, 255, 0.1) 100%)',
            borderColor: '#00bfff',
            shadowColor: 'rgba(0, 191, 255, 0.3)'
        },
        'VIP Gold': {
            icon: '🥇',
            title: 'عضو ذهبي', 
            message: 'مرحباً بالعضو الذهبي الكريم!',
            gradient: 'linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(255, 193, 7, 0.1) 100%)',
            borderColor: '#ffd700',
            shadowColor: 'rgba(255, 215, 0, 0.3)'
        },
        'VIP Silver': {
            icon: '🥈',
            title: 'عضو فضي',
            message: 'مرحباً بالعضو الفضي المحترم!',
            gradient: 'linear-gradient(135deg, rgba(192, 192, 192, 0.15) 0%, rgba(169, 169, 169, 0.1) 100%)',
            borderColor: '#c0c0c0',
            shadowColor: 'rgba(192, 192, 192, 0.3)'
        }
    };
    
    return tierMap[vipTier] || {
        icon: '⭐',
        title: 'عضو مميز',
        message: 'مرحباً بالعضو المميز!',
        gradient: 'linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.1) 100%)',
        borderColor: '#667eea',
        shadowColor: 'rgba(102, 126, 234, 0.3)'
    };
}

function getAvatarUrl(user) {
    return user.avatar 
        ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=256`
        : `https://cdn.discordapp.com/embed/avatars/${user.id % 5}.png`;
}

// Removed old dashboard functions - now using separate dashboard.html page