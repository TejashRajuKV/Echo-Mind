# Thunderwing Falcons - Echo Mind AI Fact-Checker

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Pro-green.svg)
![Auto-Update](https://img.shields.io/badge/Auto--Update-Daily-orange.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

🚀 **NEW**: Now with **Daily Auto-Update System** and **Gemini 2.5 Pro Integration**!

A cutting-edge AI fact-checking platform by Thunderwing Falcons, built for the Google Hackathon. Features real-time news integration, automated daily updates, and advanced AI-powered analysis that stays current with the latest events.

## 🏆 **What Makes Echo Mind Special:**
- ⚡ **Always Current**: Daily updates from BBC, Reuters, The Hindu & more
- 🧠 **Smart AI**: Gemini 2.5 Pro with current date awareness
- 🔄 **Automated**: Windows Task Scheduler integration
- 📏 **Comprehensive**: Political updates, health news, and more
- 🔒 **Reliable**: Smart filtering and duplicate prevention
- 📊 **Monitored**: Complete logging and error tracking

## Features

### 🤖 **NEW: AI Auto-Update System**
- **Daily News Integration**: Automatic fetching from BBC, Reuters, The Hindu, Times of India, and more
- **Real-time Political Updates**: Current CM, PM, and government changes automatically detected
- **Smart Content Filtering**: Only relevant, high-quality information added to database
- **Gemini 2.5 Pro**: Upgraded AI model with enhanced reasoning capabilities
- **Current Date Awareness**: AI responses include current context and time-sensitive information
- **Windows Scheduler Integration**: Runs automatically every day at 6 AM

### 🎨 Modern Web Design
- Responsive design that works on all devices
- Professional gradient color scheme
- Smooth animations and transitions
- Mobile-friendly navigation

### 🚀 Interactive Elements
- Demo fact-checker with sample responses
- Smooth scrolling navigation
- Contact form with validation
- Animated statistics counters
- Hover effects and micro-interactions

### 📱 Fully Responsive
- Mobile-first design approach
- Tablet and desktop optimized layouts
- Touch-friendly interface
- Cross-browser compatibility

## Project Structure

```
Echo Mind/
├── index.html              # Main HTML file with team section
├── styles.css              # CSS styling with enhanced design
├── script.js               # JavaScript with voice features
├── app.py                  # Flask backend server
├── analysis_engine.py      # AI fact-checking engine (Gemini 2.5 Pro)
├── auto_updater.py         # 🆕 Daily news auto-update system
├── database_helper.py      # SQLite database functions
├── setup_auto_update.bat   # 🆕 Windows auto-update installer
├── AUTO_UPDATE_GUIDE.md    # 🆕 Complete auto-update documentation
├── factchecks.db          # Local fact-check database
├── current_context.json    # 🆕 Daily updated news context (auto-generated)
├── last_update.json        # 🆕 Update tracking (auto-generated)
├── auto_updater.log        # 🆕 Auto-update logs (auto-generated)
├── assets/                # Images and icons folder
├── requirements.txt       # Python dependencies (updated)
└── README.md              # This file
```

## Technologies Used

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Modern styling with flexbox/grid
- **JavaScript (ES6+)** - Interactive functionality
- **Font Awesome** - Icons
- **Google Fonts (Inter)** - Typography

### AI Backend (Original Python Project)
- **Google Vertex AI** - AI platform
- **Gemini 2.5 Pro** - Advanced fact analysis model
- **BigQuery** - Evidence database for fact-checking
- **Python** - Core logic and implementation
- **Gradio** - Web interface for the AI model
- **Google Cloud** - Cloud platform

## Demo Features

The website includes a working demo that simulates the AI fact-checker with sample responses for:
- COVID vaccine information
- Climate change facts
- Flat earth theories
- General claims analysis

## Getting Started

### 🌍 **For Website Demo:**
1. **Clone or Download** the project files
2. **Open `index.html`** in a web browser
3. **Explore** the different sections:
   - Hero section with project introduction
   - Features highlighting AI capabilities
   - Interactive demo
   - About section with tech stack
   - Contact form

### 🤖 **For Full AI System with Auto-Updates:**
1. **Clone the repository**:
   ```bash
   git clone https://github.com/TejashRajuKV/Echo-Mind.git
   cd Echo-Mind
   ```

2. **Quick Setup** (Windows - Run as Administrator):
   ```bash
   setup_auto_update.bat
   ```

3. **Manual Setup**:
   ```bash
   pip install -r requirements.txt
   python auto_updater.py update  # Test auto-updater
   python app.py                  # Start the AI backend
   ```

4. **Optional - Get NewsAPI Key** (for enhanced coverage):
   - Register at [NewsAPI.org](https://newsapi.org/register) (free)
   - Set environment variable: `set NEWSAPI_KEY=your_key_here`

5. **Access the system**:
   - Website: Open `index.html` in browser
   - API: `http://localhost:8080` (Flask backend)
   - Auto-updates: Run daily at 6 AM automatically

### 📚 **Read the Complete Guide:**
See `AUTO_UPDATE_GUIDE.md` for detailed setup, configuration, and troubleshooting.

## Website Sections

### 🏠 Hero Section
- Project introduction
- Key value proposition
- Call-to-action buttons

### ⚡ Features Section
- 6 key features with icons
- Vertex AI with Gemini integration
- BigQuery evidence database
- Trusted source verification
- Gamified learning
- Educational insights
- Real-time analysis

### 🧪 Demo Section
- Interactive fact-checker simulation
- Sample responses for testing
- Loading states and animations

### 📖 About Section
- Project background
- Technology stack
- Performance statistics

### 👥 Team Section
- Thunderwing Falcons team members
- Individual profiles with skills and contact info
- Professional team presentation

### 🎤 Voice Features
- Interactive voice welcome message
- Text-to-speech integration
- Accessibility enhancements

### 📞 Project Info Section
- Echo Mind project details
- Technology information
- Mission and innovation highlights

## Customization

### Colors
The website uses a purple-blue gradient theme. To change colors, modify the CSS custom properties:
- Primary: `#667eea` to `#764ba2`
- Background: `#fafafa`
- Text: `#333`, `#4a5568`, `#718096`

### Content
Update the HTML content in `index.html` to match your specific project details:
- Team information
- Contact details
- Project statistics
- Feature descriptions

### Demo Responses
Modify the `sampleResponses` object in `script.js` to add more demo scenarios.

## Performance Features

- **Smooth Animations** - CSS transitions and JavaScript animations
- **Lazy Loading** - Images and content load as needed
- **Optimized Assets** - Efficient CSS and JavaScript
- **Mobile Optimized** - Fast loading on mobile devices

## Browser Support

- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile browsers

## Recent Updates 🆕

- [x] **Connected to actual AI backend** - Gemini 2.5 Pro integration complete
- [x] **Daily auto-update system** - Fetches news from 5+ trusted sources
- [x] **Real-time context injection** - AI aware of current date and recent events
- [x] **Windows Task Scheduler integration** - Automated daily updates
- [x] **Enhanced database system** - Smart filtering and duplicate prevention
- [x] **Comprehensive logging** - Full monitoring and error tracking

## Future Enhancements

- [ ] User authentication system
- [ ] Advanced analytics dashboard 
- [ ] Multi-language support
- [ ] Dark mode theme
- [ ] Progressive Web App (PWA) features
- [ ] Mobile app version
- [ ] API rate limiting dashboard
- [ ] Custom news source configuration UI

## Credits

- **Company**: Thunderwing Falcons - "Electrifying speed meets sharp precision"
- **Prototype**: Echo Mind - "Suggesting intelligent responses and echoes of knowledge"
- **Project**: Google Hackathon AI Fact-Checker
- **Design**: Modern gradient UI with custom logo
- **Icons**: Font Awesome
- **Fonts**: Google Fonts (Inter)

## License

This project was created for educational and hackathon purposes.

---

**Thunderwing Falcons** - Electrifying speed meets sharp precision  
**Echo Mind** - Suggesting intelligent responses and echoes of knowledge ⚡🦅
