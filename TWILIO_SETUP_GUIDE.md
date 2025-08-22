# Twilio Integration Setup Guide for VoiceAI

This guide will help you set up real Twilio integration for live phone call testing.

## Step 1: Create Twilio Account

1. Visit [Twilio Console](https://console.twilio.com/)
2. Sign up for a free account (includes $15 trial credit)
3. Verify your phone number and email

## Step 2: Get Your Credentials

From the Twilio Console Dashboard, copy these values:

### Account Info
- **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Auth Token**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Phone Number
- Purchase or use your trial phone number: `+1xxxxxxxxxx`

## Step 3: Configure Environment Variables

### For Local Development:
Create a `.env` file in the backend directory:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
WEBHOOK_BASE_URL=http://localhost:8000

# OpenAI API Key (if you have one)
OPENAI_API_KEY=your_openai_key_here

# JWT Secret
JWT_SECRET=your-super-secret-jwt-key-change-in-production
```

### For Railway Production:
Set these environment variables in your Railway project:

```bash
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
WEBHOOK_BASE_URL=https://voiceai-backend-production-81d6.up.railway.app
```

## Step 4: Configure Twilio Webhook URLs

### Method 1: Using the Dashboard (Recommended)
1. Log into your deployed application as Super Admin
2. Go to Admin Dashboard → Settings → Twilio Configuration
3. Click "Configure Webhooks" - this will automatically set up your phone number

### Method 2: Manual Configuration
In Twilio Console:

1. Go to Phone Numbers → Manage → Active Numbers
2. Click on your phone number
3. In the Voice section, set:
   - **Webhook URL**: `https://voiceai-backend-production-81d6.up.railway.app/api/v1/twilio/voice`
   - **HTTP Method**: `POST`
4. In Status Callbacks:
   - **URL**: `https://voiceai-backend-production-81d6.up.railway.app/api/v1/twilio/status`
   - **HTTP Method**: `POST`

## Step 5: Test the Integration

### New Webhook Endpoints Available:

1. **Voice Webhook**: `/api/v1/twilio/voice` - Handles incoming calls
2. **Recording Webhook**: `/api/v1/twilio/recording` - Processes recorded calls
3. **Transcription Webhook**: `/api/v1/twilio/transcription` - AI processes transcripts
4. **Status Webhook**: `/api/v1/twilio/status` - Call status updates

### Testing Steps:

1. **Call Your Twilio Number**: 
   - Dial your Twilio phone number
   - You should hear the AI greeting
   - Speak your appointment request after the beep
   - The system will record and process your call

2. **Check Call Logs**:
   - Login to tenant dashboard
   - Go to "Call Logs & Voice AI"
   - You should see your call with AI analysis

3. **Verify AI Processing**:
   - The call should show:
     - Transcription of what you said
     - AI analysis (patient name, service type, etc.)
     - Appointment creation (if applicable)

## Step 6: Features Included

### Real-time Call Processing:
- ✅ Incoming call handling
- ✅ Call recording
- ✅ Speech-to-text transcription
- ✅ AI analysis with OpenAI GPT
- ✅ Automatic appointment creation
- ✅ Call status tracking

### Dashboard Integration:
- ✅ Real-time call logs
- ✅ AI analysis display
- ✅ Recording playback
- ✅ Appointment linking
- ✅ Call statistics

### Advanced Features:
- ✅ Multi-tenant call routing
- ✅ Outbound callback capability
- ✅ Call recording downloads
- ✅ Transcript search
- ✅ Performance analytics

## Step 7: Production Best Practices

### Security:
- Never commit credentials to code
- Use environment variables
- Enable HTTPS for webhooks
- Validate Twilio requests (signature validation)

### Monitoring:
- Monitor webhook response times
- Track failed calls
- Set up alerts for high error rates
- Monitor transcription accuracy

### Scaling:
- Consider call concurrency limits
- Monitor Twilio usage costs
- Implement call queuing for high volume
- Cache frequently accessed data

## Troubleshooting

### Common Issues:

1. **Webhooks not receiving data**:
   - Check if your server is publicly accessible
   - Verify webhook URLs are correct
   - Check Twilio debugger in console

2. **Transcription not working**:
   - Ensure call recording is enabled
   - Check audio quality
   - Verify transcription webhook URL

3. **AI processing fails**:
   - Check OpenAI API key
   - Monitor API rate limits
   - Check error logs in dashboard

### Testing Webhook URLs:
```bash
# Test if webhooks are accessible
curl -X POST https://voiceai-backend-production-81d6.up.railway.app/api/v1/twilio/voice \
  -d "CallSid=test" \
  -d "From=+1234567890" \
  -d "To=+1987654321"
```

## Cost Estimation (USD)

### Twilio Pricing (approximate):
- **Phone Number**: $1/month
- **Voice Calls**: $0.0085/minute (US)
- **Recordings**: $0.0025/minute
- **Transcriptions**: $0.05/minute

### Example Monthly Cost:
- 100 calls × 3 minutes average = $2.55
- Phone number rental = $1.00
- **Total**: ~$3.55/month for basic usage

## Next Steps

1. **Set up your Twilio account**
2. **Configure environment variables**
3. **Deploy updated backend**
4. **Test with real phone calls**
5. **Monitor performance and costs**

## Support

- Twilio Documentation: https://www.twilio.com/docs
- Twilio Support: https://support.twilio.com
- OpenAI API Docs: https://platform.openai.com/docs

---

**Ready to test real voice AI?** 📞 Your system can now handle actual phone calls!