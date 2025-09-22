# Echo Mind Auto-Update System Guide

## 🚀 Overview

The Echo Mind Auto-Update System automatically refreshes your fact-checking database daily with the latest information from trusted news sources. This ensures your AI fact-checker stays current with recent events, especially political changes and breaking news.

## ✨ Features

- **Daily Automatic Updates**: Fetches latest news from trusted sources every day
- **Dynamic Context Injection**: AI prompts include current date and recent news context
- **Multiple Data Sources**: RSS feeds + optional NewsAPI integration
- **Smart Filtering**: Only adds relevant, high-quality content to your database
- **Duplicate Prevention**: Avoids adding duplicate information
- **Comprehensive Logging**: Tracks all updates and errors
- **Windows Scheduler Integration**: Runs automatically in the background

## 📋 Setup Instructions

### 1. **Quick Setup (Recommended)**

```bash
# Run the setup script as Administrator
setup_auto_update.bat
```

This will:
- Install required Python packages
- Test the auto-updater
- Create a Windows scheduled task for daily updates at 6:00 AM

### 2. **Manual Setup**

```bash
# Install dependencies
pip install -r requirements.txt

# Test the auto-updater
python auto_updater.py update

# Create scheduled task manually (run as Administrator)
schtasks /create /tn "EchoMindAutoUpdate" /tr "python \"C:\path\to\your\auto_updater.py\" update" /sc daily /st 06:00 /f
```

### 3. **Optional: NewsAPI Setup (Recommended)**

1. Register at [NewsAPI.org](https://newsapi.org/register) (free)
2. Get your API key
3. Set environment variable:
   ```bash
   # Windows
   set NEWSAPI_KEY=your_api_key_here
   
   # Or add to system environment variables permanently
   ```

## 📊 How It Works

### **Data Sources**
- **BBC News**: `http://feeds.bbci.co.uk/news/rss.xml`
- **Reuters**: `http://feeds.reuters.com/reuters/topNews`
- **The Hindu**: `https://www.thehindu.com/news/feeder/default.rss`
- **India Today**: `https://www.indiatoday.in/rss/1206578`
- **Times of India**: `https://timesofindia.indiatimes.com/rssfeedstopstories.cms`
- **NewsAPI**: Top headlines from India (if API key provided)

### **Update Process**
1. **Fetch News**: Downloads latest articles from all sources
2. **Categorize**: Sorts news into politics, health, finance, environment, general
3. **Filter**: Keeps only recent (last 24 hours) and relevant items
4. **Extract Context**: Identifies political updates, current events
5. **Update Database**: Adds new fact-checks from trusted sources
6. **Update Context File**: Creates `current_context.json` with latest info
7. **Log Results**: Records success/failure in `auto_updater.log`

### **AI Integration**
- Gemini 2.5 Pro now receives current date and context
- Political claims are cross-referenced with latest news
- Knowledge cutoff limitations are acknowledged
- Fresh data improves fact-checking accuracy

## 🎯 Usage Commands

### **Run Update Once**
```bash
python auto_updater.py update
```

### **Start Continuous Scheduler**
```bash
python auto_updater.py schedule
```
*(Runs continuously, checking every minute for scheduled updates)*

### **Check Logs**
```bash
type auto_updater.log
```

### **View Current Context**
```bash
type current_context.json
```

## 📁 Generated Files

| File | Purpose |
|------|---------|
| `current_context.json` | Latest political updates and news context |
| `last_update.json` | Timestamp of last successful update |
| `auto_updater.log` | Detailed logs of all update activities |
| `factchecks.db` | Updated with new fact-checks from news |

## 🔧 Configuration Options

### **Modify News Sources**
Edit `auto_updater.py`, line ~46:
```python
self.news_sources = {
    'BBC': 'http://feeds.bbci.co.uk/news/rss.xml',
    'Your Source': 'https://yoursource.com/rss.xml',
    # Add more sources here
}
```

### **Change Update Schedule**
Edit line ~345:
```python
schedule.every().day.at("06:00").do(self.daily_update)
# Change "06:00" to your preferred time
```

### **Modify Categories**
Edit lines ~55-65 to add/remove keywords for different categories.

## 🚨 Troubleshooting

### **Common Issues**

#### ❌ "Failed to create scheduled task"
**Solution**: Run `setup_auto_update.bat` as Administrator

#### ❌ "No module named 'schedule'"
**Solution**: Install requirements
```bash
pip install -r requirements.txt
```

#### ❌ "NewsAPI key not configured"
**Solution**: This is just a warning. RSS feeds still work. For better coverage, get a free NewsAPI key.

#### ❌ "Error fetching news from [Source]"
**Solution**: Check internet connection. Some RSS feeds may be temporarily unavailable.

### **Verification Steps**

1. **Check if updates are working**:
   ```bash
   python auto_updater.py update
   # Should show "Daily update completed successfully"
   ```

2. **Verify scheduled task**:
   ```bash
   schtasks /query /tn "EchoMindAutoUpdate"
   ```

3. **Test AI integration**:
   ```bash
   python app.py
   # Try fact-checking a recent political claim
   ```

## 📈 Monitoring & Maintenance

### **Daily Checks**
- Review `auto_updater.log` for any errors
- Verify `current_context.json` has recent timestamp
- Check database growth with new entries

### **Weekly Maintenance**
- Clean old log files if they get too large
- Update RSS feed URLs if any become inactive
- Review and update political keywords if needed

### **Monthly Review**
- Analyze which sources provide most valuable updates
- Consider adding new trusted news sources
- Update hard-coded political information if major changes occur

## 🔒 Security & Privacy

- **No Personal Data**: System only processes public news articles
- **Local Storage**: All data stored locally in SQLite database
- **API Rate Limiting**: Respectful delays between API calls
- **Source Verification**: Only trusted, established news sources
- **No User Tracking**: System doesn't track individual user queries

## ⚡ Performance Optimization

### **Resource Usage**
- **Memory**: ~50-100MB during updates
- **Storage**: ~5-10MB growth per month in database
- **Network**: ~10-20MB download per daily update
- **CPU**: Minimal impact, runs for ~30-60 seconds daily

### **Optimization Tips**
1. Run updates during low-usage hours (default: 6 AM)
2. Set NewsAPI key for more efficient data fetching
3. Regularly clean up old database entries (optional)
4. Monitor log file sizes and rotate if needed

## 🎯 Success Metrics

After setup, you should see:
- ✅ Daily updates in logs
- ✅ Fresh political context in AI responses
- ✅ Growing database with recent fact-checks
- ✅ Improved accuracy for current events
- ✅ Current date and context in AI explanations

## 🆘 Support

If you encounter issues:

1. **Check logs**: `auto_updater.log` contains detailed error information
2. **Verify setup**: Run `python auto_updater.py update` manually
3. **Test API**: Try with and without NewsAPI key
4. **Database check**: Ensure `factchecks.db` is writable
5. **Permissions**: Run as Administrator if needed

---

**🚀 Congratulations!** Your Echo Mind fact-checker now stays current with daily updates from trusted news sources, ensuring accurate and timely analysis of claims!