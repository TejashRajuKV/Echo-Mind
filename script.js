// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');

    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        
        // Animate hamburger bars
        const bars = navToggle.querySelectorAll('.bar');
        bars.forEach((bar, index) => {
            if (navMenu.classList.contains('active')) {
                if (index === 0) bar.style.transform = 'rotate(-45deg) translate(-5px, 6px)';
                if (index === 1) bar.style.opacity = '0';
                if (index === 2) bar.style.transform = 'rotate(45deg) translate(-5px, -6px)';
            } else {
                bar.style.transform = 'none';
                bar.style.opacity = '1';
            }
        });
    });

    // Close mobile menu when clicking on a link
    const navLinks = document.querySelectorAll('.nav-menu a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            const bars = navToggle.querySelectorAll('.bar');
            bars.forEach(bar => {
                bar.style.transform = 'none';
                bar.style.opacity = '1';
            });
        });
    });
});

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Demo Functionality
const claimInput = document.getElementById('claimInput');
const checkClaimBtn = document.getElementById('checkClaim');
const demoOutput = document.getElementById('demoOutput');

// Sample responses for demo (since we can't connect to the actual API in static HTML)
const sampleResponses = {
    'covid vaccine': {
        classification: 'Trustworthy',
        explanation: 'COVID-19 vaccines have been extensively tested and proven safe and effective by major health organizations.',
        score: 95,
        tips: ['Check WHO and CDC sources', 'Look for peer-reviewed studies', 'Avoid social media claims']
    },
    'earth is flat': {
        classification: 'False',
        explanation: 'The Earth is scientifically proven to be a sphere through multiple lines of evidence including satellite imagery and physics.',
        score: 2,
        tips: ['Trust established scientific consensus', 'Look for evidence-based sources', 'Be skeptical of conspiracy theories']
    },
    'climate change': {
        classification: 'Trustworthy',
        explanation: 'Climate change is supported by overwhelming scientific evidence and consensus among climate scientists.',
        score: 98,
        tips: ['Refer to IPCC reports', 'Check peer-reviewed research', 'Distinguish between weather and climate']
    },
    'default': {
        classification: 'Suspicious',
        explanation: 'This claim requires further verification. Please check multiple reliable sources.',
        score: 60,
        tips: ['Cross-reference with trusted sources', 'Look for original sources', 'Check publication dates']
    }
};

function analyzeClaimDemo(text) {
    const lowerText = text.toLowerCase();
    
    // Find matching response
    let response = sampleResponses.default;
    for (const keyword in sampleResponses) {
        if (keyword !== 'default' && lowerText.includes(keyword)) {
            response = sampleResponses[keyword];
            break;
        }
    }
    
    return `
        <div class="demo-result">
            <h3>🟢 Echo Mind Analysis Result</h3>
            <div style="margin: 1rem 0;">
                <strong>Classification:</strong> <span style="color: ${
                    response.classification === 'Trustworthy' ? '#48bb78' : 
                    response.classification === 'False' ? '#e53e3e' : '#ed8936'
                }">${response.classification}</span>
            </div>
            <div style="margin: 1rem 0;">
                <strong>Confidence Score:</strong> ${response.score}/100
            </div>
            <div style="margin: 1rem 0;">
                <strong>Explanation:</strong> ${response.explanation}
            </div>
            <div style="margin: 1rem 0;">
                <strong>📝 Educational Tips:</strong>
                <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                    ${response.tips.map(tip => `<li style="margin: 0.25rem 0;">${tip}</li>`).join('')}
                </ul>
            </div>
            <div style="margin-top: 1.5rem; padding: 1rem; background: #e6fffa; border-radius: 6px; border-left: 4px solid #38b2ac;">
                <strong>🎮 Gamification:</strong><br>
                Points earned: +10<br>
                Keep fact-checking to earn more badges!
            </div>
        </div>
    `;
}

checkClaimBtn.addEventListener('click', function() {
    const claim = claimInput.value.trim();
    
    if (!claim) {
        demoOutput.innerHTML = `
            <div style="color: #e53e3e; text-align: center; padding: 2rem;">
                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>Please enter a claim to analyze!</p>
            </div>
        `;
        return;
    }
    
    // Show loading state
    demoOutput.innerHTML = `
        <div class="loading" style="justify-content: center; padding: 2rem;">
            <div class="spinner"></div>
            <span>Analyzing claim with AI...</span>
        </div>
    `;
    
    // Simulate API delay
    setTimeout(() => {
        demoOutput.innerHTML = analyzeClaimDemo(claim);
    }, 1500);
});

// Contact Form
const contactForm = document.getElementById('contactForm');
contactForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Get form data
    const formData = new FormData(contactForm);
    const name = formData.get('name') || contactForm.querySelector('input[type="text"]').value;
    const email = formData.get('email') || contactForm.querySelector('input[type="email"]').value;
    const message = formData.get('message') || contactForm.querySelector('textarea').value;
    
    // Show success message (in a real app, you'd send this to a server)
    const submitBtn = contactForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.innerHTML = '<i class="fas fa-check"></i> Message Sent!';
    submitBtn.style.background = '#48bb78';
    submitBtn.disabled = true;
    
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.style.background = '';
        submitBtn.disabled = false;
        contactForm.reset();
    }, 3000);
});

// Scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe elements for animation
document.addEventListener('DOMContentLoaded', function() {
    const animateElements = document.querySelectorAll('.feature-card, .stat-card, .contact-item');
    
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Navbar background change on scroll
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 100) {
        navbar.style.background = 'rgba(255, 255, 255, 0.98)';
        navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.background = 'rgba(255, 255, 255, 0.95)';
        navbar.style.boxShadow = 'none';
    }
});

// Add some interactive hover effects
document.addEventListener('DOMContentLoaded', function() {
    // Feature cards tilt effect
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function(e) {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function(e) {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Stat cards counter animation
    const statNumbers = document.querySelectorAll('.stat-number');
    const animateCounters = () => {
        statNumbers.forEach(stat => {
            const target = stat.textContent;
            if (target.includes('%')) {
                animateCounter(stat, 0, parseInt(target), '%');
            } else if (target.includes('<')) {
                stat.innerHTML = '&lt;2s';
            } else if (target.includes('+')) {
                animateCounter(stat, 0, parseInt(target), '+');
            }
        });
    };
    
    const animateCounter = (element, start, end, suffix = '') => {
        const duration = 2000;
        const startTime = performance.now();
        
        const updateCounter = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(progress * (end - start) + start);
            
            element.textContent = current + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        };
        
        requestAnimationFrame(updateCounter);
    };
    
    // Trigger counter animation when stats section comes into view
    const statsSection = document.querySelector('.about-stats');
    if (statsSection) {
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounters();
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        statsObserver.observe(statsSection);
    }
});

// Add typing effect to hero subtitle
document.addEventListener('DOMContentLoaded', function() {
    const heroSubtitle = document.querySelector('.hero-subtitle');
    if (heroSubtitle) {
        const originalText = heroSubtitle.textContent;
        heroSubtitle.textContent = '';
        
        let index = 0;
        const typeWriter = () => {
            if (index < originalText.length) {
                heroSubtitle.textContent += originalText.charAt(index);
                index++;
                setTimeout(typeWriter, 50);
            }
        };
        
        // Start typing after a short delay
        setTimeout(typeWriter, 1000);
    }
});