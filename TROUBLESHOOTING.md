# DAM Compliance Analyzer - Troubleshooting Guide

## Quick Diagnosis

If you're experiencing issues, start here:

1. **Check your internet connection** - The application requires a stable internet connection
2. **Verify file format** - Only JPG, JPEG, and PNG files are supported
3. **Check file size** - Maximum file size is 10MB
4. **Refresh the page** - Sometimes a simple refresh resolves temporary issues
5. **Try with sample data** - Use provided sample images to verify the system is working

## Common Issues and Solutions

### Image Upload Issues

#### ❌ "The uploaded file format is not supported"

**Cause**: The file format is not JPG, JPEG, or PNG, or the file extension doesn't match the actual format.

**Solutions**:
1. **Convert your image**:
   - Use image editing software (Photoshop, GIMP, etc.)
   - Online converters (be cautious with sensitive images)
   - macOS: Preview app → Export → Choose JPEG or PNG
   - Windows: Paint → Save As → Choose JPEG or PNG

2. **Check file extension**:
   - Ensure the file extension matches the actual format
   - Rename `.jpeg` files to `.jpg` if needed

3. **Verify file integrity**:
   - Try opening the file in an image viewer
   - If it doesn't open, the file may be corrupted

#### ❌ "The uploaded file is too large. Maximum file size is 10MB"

**Cause**: The image file exceeds the 10MB size limit.

**Solutions**:
1. **Compress the image**:
   - Reduce JPEG quality (try 80-85% quality)
   - Use online compression tools (TinyPNG, CompressJPEG)
   - Image editing software compression options

2. **Resize the image**:
   - Reduce dimensions while maintaining aspect ratio
   - For web use: 1920x1080 is usually sufficient
   - For print: Consider if full resolution is necessary

3. **Change format**:
   - PNG files are often larger than JPEG
   - Convert PNG to JPEG if transparency isn't needed

#### ❌ "Error processing image"

**Cause**: The image file may be corrupted or have unusual characteristics.

**Solutions**:
1. **Try a different image** to verify the system is working
2. **Re-save the image** in a standard format
3. **Check image properties**:
   - Ensure it's a standard RGB image
   - Avoid unusual color profiles or embedded data

### Metadata Issues

#### ❌ "The metadata JSON format is invalid"

**Cause**: The JSON syntax is incorrect.

**Solutions**:
1. **Use a JSON validator**:
   - Online tools: JSONLint.com, JSONFormatter.org
   - Check for missing commas, brackets, or quotes

2. **Common JSON errors**:
   ```json
   // ❌ Wrong - missing comma
   {
     "component_id": "IMG_001"
     "component_name": "Test Image"
   }
   
   // ✅ Correct
   {
     "component_id": "IMG_001",
     "component_name": "Test Image"
   }
   ```

3. **Use the example format**:
   - Copy the provided example and modify it
   - Start simple and add fields gradually

#### ⚠️ "Required metadata fields are missing"

**Cause**: Essential fields like `component_id` or `component_name` are not provided.

**Solutions**:
1. **Add minimum required fields**:
   ```json
   {
     "component_id": "YOUR_ID_HERE",
     "component_name": "YOUR_IMAGE_NAME_HERE"
   }
   ```

2. **Use the complete example** as a template

3. **Check field names** for typos (case-sensitive)

### Analysis Issues

#### ❌ "Workflow execution failed"

**Cause**: Various system or network issues during analysis.

**Solutions**:
1. **Check internet connection**:
   - Ensure stable, high-speed connection
   - Avoid public WiFi if possible

2. **Try again**:
   - Wait a few minutes and retry
   - The issue may be temporary

3. **Use smaller image**:
   - Large images take more processing time
   - Try with a smaller test image first

4. **Simplify metadata**:
   - Start with minimal metadata
   - Add more fields after successful analysis

#### ❌ "Authentication failed"

**Cause**: System configuration issue with Google Cloud credentials.

**Solutions**:
1. **Refresh the page** and try again
2. **Clear browser cache**:
   - Chrome: Settings → Privacy → Clear browsing data
   - Firefox: Settings → Privacy → Clear Data
   - Safari: Develop → Empty Caches

3. **Try incognito/private mode**
4. **Contact support** if issue persists

#### ❌ "API rate limit exceeded"

**Cause**: Too many requests in a short time period.

**Solutions**:
1. **Wait 5-10 minutes** before trying again
2. **Avoid rapid successive requests**
3. **Use the application during off-peak hours**

#### ❌ "The AI service is temporarily unavailable"

**Cause**: Google Vertex AI service is experiencing issues.

**Solutions**:
1. **Wait and retry** in 10-15 minutes
2. **Check Google Cloud Status** page for service updates
3. **Try during different times** if issue persists

### Browser Issues

#### ❌ Page won't load or appears broken

**Cause**: Browser compatibility or caching issues.

**Solutions**:
1. **Use a supported browser**:
   - Chrome (recommended)
   - Firefox
   - Safari
   - Edge

2. **Clear browser cache and cookies**
3. **Disable browser extensions** temporarily
4. **Try incognito/private mode**
5. **Update your browser** to the latest version

#### ❌ Upload button not working

**Cause**: JavaScript disabled or browser security settings.

**Solutions**:
1. **Enable JavaScript** in browser settings
2. **Check browser security settings**
3. **Disable ad blockers** temporarily
4. **Try a different browser**

### Performance Issues

#### ⏳ Analysis taking too long

**Cause**: Large images or high system load.

**Expected times**:
- Small images (< 1MB): 15-30 seconds
- Medium images (1-5MB): 30-60 seconds  
- Large images (5-10MB): 60-90 seconds

**Solutions**:
1. **Be patient** - complex analysis takes time
2. **Don't refresh** the page during analysis
3. **Try smaller images** for faster processing
4. **Use during off-peak hours**

#### ⏳ Page loading slowly

**Cause**: Network or server issues.

**Solutions**:
1. **Check internet speed** (minimum 5 Mbps recommended)
2. **Close other browser tabs** using bandwidth
3. **Try different network** if possible
4. **Wait for better network conditions**

## Error Code Reference

### Validation Errors (VAL_xxx)
- **VAL_001**: Invalid image format
- **VAL_002**: File size too large
- **VAL_003**: Invalid JSON syntax
- **VAL_004**: Missing required fields

### Authentication Errors (AUTH_xxx)
- **AUTH_001**: Invalid credentials
- **AUTH_002**: Expired token

### API Errors (API_xxx)
- **API_001**: Rate limit exceeded
- **API_002**: Service unavailable
- **API_003**: Content blocked by filters

### Network Errors (NET_xxx)
- **NET_001**: Connection timeout

### Processing Errors (PROC_xxx)
- **PROC_001**: General processing failure

## Advanced Troubleshooting

### For Technical Users

#### Check Browser Console
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for error messages
4. Share relevant errors when reporting issues

#### Network Analysis
1. Open Developer Tools → Network tab
2. Reload page and try upload
3. Look for failed requests (red entries)
4. Check response codes and error messages

#### Test with Sample Data
1. Use provided sample images and metadata
2. If samples work but your data doesn't, the issue is with your files
3. If samples don't work, it's a system issue

### Reporting Issues

When contacting support, please provide:

1. **Error message** (exact text)
2. **Browser and version** (Chrome 91, Firefox 89, etc.)
3. **Operating system** (Windows 10, macOS 12, etc.)
4. **File details** (size, format, dimensions)
5. **Steps to reproduce** the issue
6. **Screenshots** if helpful
7. **Console errors** (if technical user)

## Prevention Tips

### Best Practices
1. **Test with sample data** before using your own files
2. **Start with small, simple images** for initial testing
3. **Keep metadata simple** initially, add complexity gradually
4. **Use stable internet connection** for uploads
5. **Don't refresh page** during analysis
6. **Save your metadata** in a text file before pasting

### File Preparation
1. **Optimize images** before upload:
   - Reasonable file size (< 5MB preferred)
   - Standard dimensions (1920x1080 or similar)
   - Standard color profile (sRGB)

2. **Prepare metadata** in advance:
   - Use JSON validator before pasting
   - Start with example template
   - Add fields incrementally

### System Requirements
- **Internet**: Stable broadband connection (5+ Mbps)
- **Browser**: Modern browser with JavaScript enabled
- **Screen**: Minimum 1024x768 resolution recommended

## Still Having Issues?

If you've tried the solutions above and are still experiencing problems:

1. **Try the sample data** to verify system functionality
2. **Test with a different browser** or device
3. **Wait and try again later** (may be temporary issue)
4. **Document the issue** with screenshots and error messages
5. **Contact support** with detailed information

Remember: This is a proof-of-concept application, so some limitations are expected. Your feedback helps improve the system!

---

*For general usage instructions, see the USER_GUIDE.md file.*