Writing complex code (like React and TypeScript) directly via CMD echo commands is extremely error-prone because characters like <, >, |, and & break the command line.
Instead, here is the fastest, safest workflow:
 * Run this block of commands to create the entire folder structure and empty files.
 * Run the final command (code .) to open VS Code.
 * Paste the code I gave you into the open files.
1. Run these commands in CMD
Copy the entire block below, paste it into your Command Prompt, and hit Enter.
:: 1. Create the root folder and enter it
mkdir release-architect
cd release-architect

:: 2. Create the sub-directories
mkdir .vscode
mkdir src
mkdir src\webview

:: 3. Create the configuration files (Root)
type nul > package.json
type nul > tsconfig.json
type nul > webpack.config.js
type nul > .gitignore

:: 4. Create the Source files (Backend)
type nul > src\extension.ts
type nul > src\gitService.ts

:: 5. Create the Webview files (Frontend)
type nul > src\webview\index.tsx
type nul > src\webview\App.tsx
type nul > src\webview\styles.css

:: 6. Open the project in VS Code immediately
code .

2. What to do next (Fill the files)
Once VS Code opens, click on these files in the Explorer on the left and paste the code from my previous response:
 * package.json: Paste the JSON configuration.
 * tsconfig.json: Paste the TypeScript config.
 * webpack.config.js: Paste the Webpack config.
 * src/extension.ts: Paste the Extension logic.
 * src/gitService.ts: Paste the Git logic.
 * src/webview/index.tsx: Paste the React entry point.
 * src/webview/App.tsx: Paste the React Dashboard code.
 * src/webview/styles.css: Paste the CSS.
 * .gitignore: Paste the 5 lines I provided (node_modules, dist, etc.).
3. Final Build Command
Once you have pasted the code and saved all files, open the terminal in VS Code (Ctrl + `) and run:
npm install && npm run compile

