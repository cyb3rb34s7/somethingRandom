@Component({
  selector: 'app-download-progress',
  template: `
    <div *ngIf="isDownloading" class="download-toast" [@slideIn]>
      <div class="download-content">
        <div class="header">
          <span class="title">{{ 
            downloadState === 'preparing' ? 'Preparing Export' : 'Downloading'
          }}</span>
          <button class="cancel-btn" (click)="cancelDownload()">
            <span>✕</span>
          </button>
        </div>

        <div class="info-section">
          <span class="filename" [class.pulse]="downloadState === 'preparing'">
            {{ fileName }}
          </span>
          <span class="status-text">
            {{ downloadState === 'preparing' ? 'Please wait...' : progress + '%' }}
          </span>
        </div>

        <div class="progress-container">
          <div class="progress-bar" 
               [style.width.%]="progress"
               [class.indeterminate]="downloadState === 'preparing'">
          </div>
        </div>

        <div class="status-section">
          <span class="status-icon" [class.spinning]="downloadState === 'preparing'">
            {{ downloadState === 'preparing' ? '⚙️' : '📥' }}
          </span>
          <span class="status-message">
            {{ downloadState === 'preparing' ? 'Preparing your file...' : 'Downloading...' }}
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .download-toast {
      position: fixed;
      top: 20px;
      right: 20px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      padding: 16px;
      width: 320px;
      z-index: 1000;
    }

    .download-content {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .title {
      font-weight: 600;
      color: #1a1a1a;
      font-size: 14px;
    }

    .info-section {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .filename {
      font-size: 13px;
      color: #666;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .pulse {
      animation: pulse 2s infinite;
    }

    .status-text {
      font-size: 13px;
      color: #666;
      font-weight: 500;
    }

    .progress-container {
      height: 4px;
      background: #f0f0f0;
      border-radius: 4px;
      overflow: hidden;
    }

    .progress-bar {
      height: 100%;
      background: #4CAF50;
      transition: width 0.3s ease;
    }

    .progress-bar.indeterminate {
      background: linear-gradient(90deg, #4CAF50 0%, #81C784 50%, #4CAF50 100%);
      animation: progress-animation 2s linear infinite;
      width: 100%;
    }

    .status-section {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-icon {
      font-size: 16px;
    }

    .spinning {
      animation: spin 2s linear infinite;
    }

    .status-message {
      font-size: 12px;
      color: #666;
    }

    .cancel-btn {
      background: none;
      border: none;
      padding: 4px;
      cursor: pointer;
      color: #666;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .cancel-btn:hover {
      background: #f5f5f5;
      color: #333;
    }

    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.6; }
      100% { opacity: 1; }
    }

    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    @keyframes progress-animation {
      0% { background-position: -200% 0; }
      100% { background-position: 200% 0; }
    }
  `],
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ transform: 'translateX(100%)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
      ]),
      transition(':leave', [
        animate('300ms ease-in', style({ transform: 'translateX(100%)', opacity: 0 }))
      ])
    ])
  ]
})