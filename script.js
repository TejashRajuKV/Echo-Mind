document.addEventListener('DOMContentLoaded', function() {
    // Centralized initialization - Updated 2024-09-21 14:21
    initializeMobileNav();
    initializeSmoothScroll();
    initializeDemoFunctionality();
    initializeScrollAnimations();
    initializeInteractiveEffects();
    initializeTypingEffect();
    initializeVoiceWelcome();
});

function initializeMobileNav() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    if (!navToggle || !navMenu) return;
    
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
}

function initializeSmoothScroll() {
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
}

function initializeDemoFunctionality() {
    const claimInput = document.getElementById('claimInput');
    const checkClaimBtn = document.getElementById('checkClaim');
    const demoOutput = document.getElementById('demoOutput');

    if (!claimInput || !checkClaimBtn || !demoOutput) {
        console.error("Demo UI elements not found!");
        return;
    }

    const getClassificationClass = (classification) => {
        if (classification === 'Trustworthy') return 'classification-trustworthy';
        if (classification === 'False') return 'classification-false';
        return 'classification-suspicious';
    };

    // This function builds the HTML from the real API response
    function displayAnalysisResult(data) {
        return `
            <div class="demo-result" style="text-align: left;">
                <h3>🟢 AI Fact-Check Analysis:</h3>
                <div style="margin: 1rem 0; padding: 1rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #4299e1;">
                    <p><strong>Classification:</strong> <span class="${getClassificationClass(data.classification)}" style="font-weight: bold; font-size: 1.1em;">${data.classification}</span></p>
                    <p><strong>Confidence Score:</strong> ${data.score}/100</p>
                </div>
                
                <div style="margin: 1.5rem 0;">
                    <h4 style="margin-bottom: 0.75rem; color: #2d3748;">📋 Detailed Analysis:</h4>
                    <div style="background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; line-height: 1.6;">
                        ${data.explanation}
                    </div>
                </div>
                
                <div style="margin: 1.5rem 0;">
                    <h4 style="margin-bottom: 0.75rem; color: #2d3748;">📌 Supporting Evidence:</h4>
                    <div style="background: #f7fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                        ${data.evidence}
                    </div>
                </div>

                <div style="margin: 1.5rem 0;">
                    <h4 style="margin-bottom: 0.75rem; color: #2d3748;">📝 Educational Guidelines:</h4>
                    <div style="background: #fffbf0; padding: 1rem; border-radius: 8px; border: 1px solid #fed7aa;">
                        <ul style="margin: 0; padding-left: 1.5rem; line-height: 1.5;">
                            ${data.tips.slice(0, 6).map(tip => `<li style="margin: 0.5rem 0;">${tip}</li>`).join('')}
                        </ul>
                        ${data.tips.length > 6 ? `
                            <details style="margin-top: 1rem;">
                                <summary style="cursor: pointer; font-weight: bold; color: #d69e2e;">Show More Tips (${data.tips.length - 6} additional)</summary>
                                <ul style="margin: 0.5rem 0; padding-left: 1.5rem; line-height: 1.5;">
                                    ${data.tips.slice(6).map(tip => `<li style="margin: 0.5rem 0;">${tip}</li>`).join('')}
                                </ul>
                            </details>
                        ` : ''}
                    </div>
                </div>

                <div style="margin-top: 1.5rem; padding: 1rem; background: #e6fffa; border-radius: 8px; border-left: 4px solid #38b2ac;">
                    <strong>🎮 Your Progress:</strong><br>
                    <span style="font-size: 1.1em;">Points: ${data.gamification.points}</span><br>
                    Badges: ${data.gamification.badges.join(', ') || 'None yet - keep fact-checking to earn badges!'}
                    ${data.gamification.badge_earned ? `<br><span style="color: #38b2ac; font-weight: bold; font-size: 1.1em;">🎉 Congratulations! New Badge Earned: ${data.gamification.badge_earned}!</span>` : ''}
                </div>

                <div style="margin-top: 1rem; padding: 1rem; background: #ebf4ff; border-radius: 8px; border-left: 4px solid #4299e1;">
                    <strong>📊 Personalized Guidance:</strong><br>
                    <span style="font-weight: bold;">Topic Category:</span> ${data.personalization.category}<br><br>
                    <span style="font-weight: bold;">Specific Advice:</span><br>
                    <em>${data.personalization.tip}</em>
                </div>
            </div>
        `;
    }

    function displayError(errorMessage) {
        return `
            <div class="demo-result" style="border-left-color: #e53e3e;">
                <h3>🔴 Error</h3>
                <p>Could not connect to the analysis server. Please ensure the Python server is running and try again.</p>
                <p style="font-family: monospace; background: #fef2f2; padding: 0.5rem; border-radius: 4px; margin-top: 1rem; color: #c53030;">${errorMessage}</p>
                <div style="margin-top: 1rem; padding: 1rem; background: #fef2f2; border-radius: 6px;">
                    <strong>Troubleshooting Steps:</strong>
                    <ol style="margin: 0.5rem 0; padding-left: 1.5rem;">
                        <li>Make sure the Flask server is running: <code>python app.py</code></li>
                        <li>Check that the server is accessible at https://echo-mind-191043917366.us-central1.run.app</li>
                        <li>Verify your Google Cloud credentials are set up correctly</li>
                        <li>Check the browser console for additional error details</li>
                    </ol>
                </div>
            </div>
        `;
    }

    checkClaimBtn.addEventListener('click', async function() {
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
            <div class="loading" style="display: flex; align-items: center; justify-content: center; padding: 2rem;">
                <div class="spinner" style="margin-right: 1rem; width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span>Connecting to Vertex AI...</span>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        
        try {
            const response = await fetch('https://echo-mind-191043917366.us-central1.run.app/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'gdo4N6BnLrvu9MOaH25Ml5M8msPjVf9tsez24Dq8eRI'
                },
                body: JSON.stringify({ claim: claim }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server responded with status: ${response.status}. ${errorText}`);
            }

            const data = await response.json();
            console.log('Analysis result:', data); // For debugging
            demoOutput.innerHTML = displayAnalysisResult(data);

        } catch (error) {
            console.error('Fetch Error:', error);
            demoOutput.innerHTML = displayError(error.message);
        }
    });

    // Add Enter key support for the textarea
    claimInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            checkClaimBtn.click();
        }
    });
}

// Scroll animations
function initializeScrollAnimations() {
    const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, observerOptions);

    const animateElements = document.querySelectorAll('.feature-card, .stat-card, .contact-item, .team-card, .mission-card');
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

function initializeInteractiveEffects() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function(e) {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function(e) {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
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
            const current = Math.floor(start + (end - start) * progress);
            element.textContent = current + suffix;

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        };

        requestAnimationFrame(updateCounter);
    };

    // Trigger counter animation when stats section comes into view
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    const aboutStats = document.querySelector('.about-stats');
    if (aboutStats) {
        statsObserver.observe(aboutStats);
    }
}

function initializeTypingEffect() {
    const heroTitle = document.querySelector('.hero-title');
    if (!heroTitle) return;

    // This is a placeholder function - implement typing effect if needed
    // For now, we'll just ensure the title is visible
    heroTitle.style.opacity = '1';
}

function initializeVoiceWelcome() {
    // Check if the browser supports Speech Synthesis
    if (!('speechSynthesis' in window)) {
        console.log('Speech Synthesis not supported in this browser');
        return;
    }

    // Check if this is the first visit to avoid repeated announcements on refresh
    const hasPlayedWelcome = sessionStorage.getItem('echoMindVoiceWelcome');
    
    if (hasPlayedWelcome) {
        return; // Don't play if already played in this session
    }

    // Add welcome voice button instead of auto-play (due to browser restrictions)
    addWelcomeVoiceButton();
}

function speakWelcomeMessage() {
    try {
        // Create speech synthesis utterance
        const welcomeText = "Welcome to Echo Mind. Your AI-powered fact checker by Thunderwing Falcons.";
        const utterance = new SpeechSynthesisUtterance(welcomeText);
        
        // Configure voice settings
        utterance.rate = 0.9; // Slightly slower for clarity
        utterance.pitch = 1.0; // Normal pitch
        utterance.volume = 0.8; // 80% volume to not be too loud
        
        // Try to use a nice voice if available
        const voices = speechSynthesis.getVoices();
        if (voices.length > 0) {
            // Prefer female voices or specific high-quality voices
            const preferredVoice = voices.find(voice => 
                voice.name.includes('Google') || 
                voice.name.includes('Microsoft') || 
                voice.name.includes('Samantha') ||
                voice.gender === 'female'
            ) || voices[0];
            
            utterance.voice = preferredVoice;
        }

        // Event listeners for voice feedback
        utterance.onstart = () => {
            console.log('🎤 Echo Mind voice welcome started');
            showVoiceIndicator();
        };
        
        utterance.onend = () => {
            console.log('🎤 Echo Mind voice welcome completed');
            hideVoiceIndicator();
        };
        
        utterance.onerror = (event) => {
            console.error('🎤 Voice welcome error:', event.error);
        };

        // Speak the welcome message
        speechSynthesis.speak(utterance);
        
    } catch (error) {
        console.error('Error with voice welcome:', error);
    }
}

// Optional: Add a function to replay the welcome message
function replayWelcomeMessage() {
    // Stop any current speech
    speechSynthesis.cancel();
    
    // Play the welcome message again
    setTimeout(() => {
        speakWelcomeMessage();
    }, 100);
}

// Add welcome voice button for user interaction
function addWelcomeVoiceButton() {
    // Create a welcome voice button
    const welcomeButton = document.createElement('div');
    welcomeButton.id = 'welcome-voice-button';
    welcomeButton.innerHTML = `
        <button onclick="playWelcomeVoice()" class="welcome-voice-btn" title="Click to hear welcome message">
            🎤 Welcome Message
        </button>
    `;
    welcomeButton.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        z-index: 1000;
        animation: bounce 2s infinite;
    `;
    
    // Add bounce animation
    if (!document.getElementById('welcome-voice-style')) {
        const style = document.createElement('style');
        style.id = 'welcome-voice-style';
        style.textContent = `
            .welcome-voice-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 25px;
                font-size: 0.9rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .welcome-voice-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                60% { transform: translateY(-5px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(welcomeButton);
    
    // Remove button after 10 seconds if not used
    setTimeout(() => {
        if (document.getElementById('welcome-voice-button')) {
            document.getElementById('welcome-voice-button').remove();
        }
    }, 10000);
}

// Function to play welcome voice (called by button)
function playWelcomeVoice() {
    speakWelcomeMessage();
    sessionStorage.setItem('echoMindVoiceWelcome', 'true');
    
    // Remove the button after clicking
    const button = document.getElementById('welcome-voice-button');
    if (button) {
        button.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => button.remove(), 500);
    }
}

// Visual feedback functions
function showVoiceIndicator() {
    // Create a subtle visual indicator when voice is speaking
    const indicator = document.createElement('div');
    indicator.id = 'voice-indicator';
    indicator.innerHTML = '🎤 Speaking...';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.9rem;
        z-index: 1000;
        animation: pulse 2s infinite;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    `;
    
    // Add pulse animation
    if (!document.getElementById('voice-animation-style')) {
        const style = document.createElement('style');
        style.id = 'voice-animation-style';
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 0.8; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.05); }
                100% { opacity: 0.8; transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(indicator);
}

function hideVoiceIndicator() {
    const indicator = document.getElementById('voice-indicator');
    if (indicator) {
        indicator.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 500);
    }
}

// Optional: Add voice controls for accessibility
function addVoiceControls() {
    // You can call this function if you want to add voice control buttons later
    const voiceControlsHTML = `
        <div class="voice-controls" style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
            <button onclick="replayWelcomeMessage()" class="voice-btn" title="Replay Welcome Message">
                🔊
            </button>
        </div>
    `;
    
    // Uncomment the line below if you want to add the replay button
    // document.body.insertAdjacentHTML('beforeend', voiceControlsHTML);
}
