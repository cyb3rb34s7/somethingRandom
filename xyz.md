Yes, there are several ways you can automate this process! Here are the most practical approaches:

## Web Automation Tools

**Selenium (Recommended)**
- Works with Python, Java, C#, or JavaScript
- Can handle complex web interactions like scrolling, clicking, form filling
- Most reliable for this type of task

**Playwright**
- Modern alternative to Selenium
- Faster and more stable
- Great for JavaScript/TypeScript

## Implementation Approach

1. **Read your Excel file** to get the ID mappings
2. **Loop through each record** and:
   - Navigate to the search page
   - Enter the ID in search bar
   - Click search and wait for results
   - Click "View" on the correct asset
   - Scroll to External ID section
   - Fill in the external ID
   - Click Save
   - Handle any confirmation dialogs

## Sample Structure (Python + Selenium)

```python
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Read Excel file
df = pd.read_excel('your_file.xlsx')

# Setup browser
driver = webdriver.Chrome()
driver.get('your_portal_url')

for index, row in df.iterrows():
    asset_id = row['ID']
    external_id = row['External_ID']
    
    # Search for asset
    search_box = driver.find_element(By.ID, "search_bar_id")
    search_box.clear()
    search_box.send_keys(asset_id)
    # ... continue with clicks, scrolling, form filling
```

## Considerations

- **Authentication**: Handle login if required
- **Error handling**: What if an asset isn't found?
- **Rate limiting**: Add delays to avoid overwhelming the server
- **Backup**: Keep track of processed items in case script fails

Would you like me to help you create a specific automation script? I'd need to know:
1. What programming language you prefer
2. The portal's URL structure
3. Any specific element IDs or classes from the web page