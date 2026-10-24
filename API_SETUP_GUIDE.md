# Echo Mind API Auto-Update System Setup Guide

## 🚀 **Real-Time API Integration System**

This system automatically fetches current data from various APIs daily, ensuring your fact-checker always has the latest information without hard-coding anything.

## 🔑 **API Keys Setup (Optional but Recommended)**

Set these environment variables for enhanced coverage:

```bash
# News API (get free key from https://newsapi.org)
set NEWS_API_KEY=your_newsapi_key_here

# Cricket API (get free key from https://cricapi.com) 
set CRICAPI_KEY=your_cricapi_key_here

# FreeNewsAPI (get free key from https://www.freenewsapi.io)
set FREE_NEWS_API_KEY=your_freenewsapi_key_here

# Weather API (get free key from https://openweathermap.org)
set OPENWEATHER_KEY=your_openweather_key_here
```

**Note:** System works with mock data even without API keys!

## 🎯 **Current API Integrations**

### **Sports APIs**
- **Cricket API**: Live match data, team information
- **News API Sports**: Latest sports news from India

### **Health APIs**
- **COVID-19 India**: Official government data
- **News API Health**: Latest health news from India

### **Technology APIs**
- **News API Technology**: Latest tech news from India

### **Financial APIs**
- **BSE API**: Stock market data
- **Economic indicators**: Real-time financial data

### **Weather/Climate APIs**
- **OpenWeather**: Current weather and climate data

## 🔧 **How to Use**

### **1. Quick Test**
```bash
# Test the system
python api_updater.py test "RCB captain"
```

### **2. Run Update Once**
```bash
# Manual update
python api_updater.py update
```

### **3. Start Daily Auto-Updates**
```bash
# Continuous daily updates at 6 AM
python api_updater.py schedule
```

## 📊 **How It Works**

### **Daily Process:**
1. **Fetch**: Gets data from all configured APIs
2. **Process**: Extracts relevant information (captains, news, stats)
3. **Store**: Saves to SQLite database with timestamps
4. **Update**: Creates context file for AI system
5. **Verify**: Logs success/failures for monitoring

### **Smart Features:**
- **Mock Data**: Works without API keys using realistic test data
- **Rate Limiting**: Respects API limits with delays
- **Error Handling**: Continues working even if some APIs fail
- **Deduplication**: Avoids storing duplicate information
- **Categorization**: Automatically sorts data by topic

## 🎯 **Adding New APIs**

To add a new API, modify `api_updater.py`:

```python
APIConfig(
    name="your_api_name",
    url="https://api.example.com/endpoint",
    headers={"Authorization": "Bearer your_key"},
    params={"param1": "value1"},
    data_path=["data", "results"],  # Path to data in JSON
    update_frequency="daily"
)
```

## 📈 **Real-Time Fact Checking**

### **What Gets Updated Daily:**

#### **🏏 Sports:**
- IPL team captains and vice-captains
- Player transfers and trades
- Match results and statistics
- Tournament updates

#### **🏥 Health:**
- COVID-19 statistics by state
- Healthcare policy changes
- Medical breakthrough news
- Public health announcements

#### **💻 Technology:**
- Tech company news
- Product launches
- Cybersecurity alerts
- AI/ML developments

#### **💰 Business:**
- Stock market indices
- Economic indicators
- Corporate announcements
- Startup funding news

#### **🌦️ Climate:**
- Weather patterns
- Air quality data
- Environmental policies
- Climate research

## 🔍 **Query Examples That Now Work:**

```bash
# Sports
"Is Faf du Plessis the captain of RCB?"
"Who is the current captain of Chennai Super Kings?"
"RCB vs CSK match result"

# Health  
"Current COVID cases in Maharashtra"
"Latest health ministry guidelines"

# Technology
"Apple's latest product launch in India"
"Government's new IT policy"

# Business
"Sensex closing today"
"Latest IPO news"
```

## 🛠️ **Integration with Analysis Engine**

The API system integrates with your main fact-checker by:

1. **Loading API Context**: Analysis engine reads `api_current_context.json`
2. **Real-time Verification**: Checks database for current information
3. **Enhanced Responses**: Provides fresh data in AI analysis
4. **Source Attribution**: Shows data sources and update timestamps

## 📋 **Monitoring & Maintenance**

### **Check System Health:**
```bash
# View logs
type api_updater.log

# Check last updates
type api_last_update.json

# Test specific query
python api_updater.py test "your question here"
```

### **Database Tables:**
- `sports_data`: Team captains, players, tournaments
- `current_info`: General current information by category
- `api_data`: Raw API responses with timestamps

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **"No API keys configured"**
- System uses mock data automatically
- Get free API keys for better coverage
- Set environment variables as shown above

#### **"API request failed"**
- Check internet connection
- Verify API key validity
- System continues with other APIs

#### **"No recent data found"**
- Run manual update: `python api_updater.py update`
- Check if APIs are responding
- Review logs for specific errors

## 🎯 **Benefits**

### **✅ Always Current:**
- No more outdated information
- Real-time sports team captains
- Latest government policies
- Current market data

### **✅ Automatic:**
- Runs daily without intervention
- Updates context for AI automatically
- Handles API failures gracefully

### **✅ Expandable:**
- Easy to add new APIs
- Configurable update frequencies
- Category-based organization

### **✅ Reliable:**
- Works with or without API keys
- Comprehensive error handling
- Detailed logging and monitoring

## 🔮 **Future Enhancements**

Easily add more APIs for:
- **Education**: Exam results, admission notifications
- **Government**: Policy changes, election results  
- **Entertainment**: Movie releases, celebrity news
- **Regional**: State-specific information
- **International**: Global news affecting India

## 📞 **API Providers**

### **Free APIs Used:**
- **NewsAPI**: 1000 requests/day free
- **COVID19 India**: Unlimited, government data
- **CricAPI**: 100 requests/day free
- **OpenWeather**: 1000 requests/day free

### **Paid APIs (Optional):**
- **Bloomberg API**: Financial data
- **ESPN API**: Comprehensive sports data
- **Twitter API**: Real-time social trends

---

**🎉 Your Echo Mind system now automatically stays current with real-time data from multiple APIs, ensuring accurate fact-checking for any topic!**