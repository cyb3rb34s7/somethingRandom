Ah! That's the issue - **ShadCN UI isn't properly configured**. You need to complete the ShadCN setup for the beautiful styling to work. Here's what's missing:

## **🔧 Missing ShadCN Configuration**

### **1. Check if `components.json` exists in your root directory**
If not, run:
```bash
npx shadcn@latest init
```

### **2. Update your CSS file with ShadCN variables**
Replace your current CSS with the **complete ShadCN theme**:

**In `src/index.css` or `src/app.css`:**
```css
@import "tailwindcss";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222.2 84% 4.9%;
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96%;
    --accent-foreground: 222.2 84% 4.9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.75rem;
    
    /* Custom colors for monitoring */
    --success: 142 76% 36%;
    --warning: 38 92% 50%;
    --error: 0 84% 60%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 84% 4.9%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 94.1%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}

/* Custom animations */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

.animate-slide-in {
  animation: slideIn 0.3s ease-out;
}

.animate-pulse-success {
  animation: pulseSuccess 2s infinite;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

@keyframes pulseSuccess {
  0%, 100% { background-color: hsl(var(--success)); opacity: 1; }
  50% { opacity: 0.8; }
}
```

### **3. Create the missing utility file**
**Create `src/lib/utils.ts`:**
```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

### **4. Install missing dependencies**
```bash
npm install clsx tailwind-merge lucide-react class-variance-authority
```

### **5. Add the ShadCN components you're using**
```bash
npx shadcn@latest add button
npx shadcn@latest add badge
npx shadcn@latest add select
```

**After these steps, your sidebar should look beautiful with proper styling, colors, and animations!** ✨

Try this and let me know if it looks better!