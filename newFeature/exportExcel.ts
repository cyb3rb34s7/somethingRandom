// state-store.service.ts
export class StateStoreService {
  private readonly _downloadProgress = new BehaviorSubject<number>(0);
  private readonly _isDownloading = new BehaviorSubject<boolean>(false);
  private readonly _downloadFileName = new BehaviorSubject<string>('');

  getStoreState(key: string): any {
    switch (key) {
      case 'downloadProgress':
        return this._downloadProgress.getValue();
      case 'isDownloading':
        return this._isDownloading.getValue();
      case 'downloadFileName':
        return this._downloadFileName.getValue();
      // ... existing cases
    }
  }

  setStoreState(key: string, val: any) {
    switch (key) {
      case 'downloadProgress':
        this._downloadProgress.next(val);
        break;
      case 'isDownloading':
        this._isDownloading.next(val);
        break;
      case 'downloadFileName':
        this._downloadFileName.next(val);
        break;
      // ... existing cases
    }
  }
}

// api.service.ts
export class ApiService {
  constructor(private http: HttpClient) {}

  postBlobCall(endpoint: string, data: any) {
    return this.http.post(endpoint, data, {
      responseType: 'blob',
      observe: 'events',
      reportProgress: true
    });
  }
}

// asset.service.ts
export class AssetService {
  private currentExportSubscription?: Subscription;

  constructor(
    private apiService: ApiService,
    private stateStore: StateStoreService
  ) {}

  exportAssetToExcel(data: any) {
    // Cancel any existing export
    this.cancelExport();
    
    this.stateStore.setStoreState('isDownloading', true);
    this.stateStore.setStoreState('downloadFileName', 'assets.xlsx');
    this.stateStore.setStoreState('downloadProgress', 0);

    return this.apiService.postBlobCall('/api/export', data).pipe(
      tap(event => {
        if (event.type === HttpEventType.DownloadProgress && event.total) {
          const progress = Math.round(100 * event.loaded / event.total);
          this.stateStore.setStoreState('downloadProgress', progress);
        }
      }),
      map((event: any) => {
        if (event.type === HttpEventType.Response) {
          this.stateStore.setStoreState('isDownloading', false);
          return event.body;
        }
        return null;
      }),
      catchError(error => {
        this.stateStore.setStoreState('isDownloading', false);
        throw error;
      })
    );
  }

  cancelExport() {
    if (this.currentExportSubscription) {
      this.currentExportSubscription.unsubscribe();
      this.currentExportSubscription = undefined;
      this.stateStore.setStoreState('isDownloading', false);
      this.stateStore.setStoreState('downloadProgress', 0);
    }
  }
}

// helper.ts
export function handleDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

// download-progress.component.ts
@Component({
  selector: 'app-download-progress',
  template: `
    <div *ngIf="isDownloading" class="download-toast">
      <div class="download-content">
        <span class="filename">{{ fileName }}</span>
        <div class="progress-container">
          <div class="progress-bar" [style.width.%]="progress"></div>
        </div>
        <span class="percentage">{{ progress }}%</span>
        <button class="cancel-btn" (click)="cancelDownload()">✕</button>
      </div>
    </div>
  `,
  styles: [`
    .download-toast {
      position: fixed;
      top: 20px;
      right: 20px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      padding: 16px;
      width: 300px;
      z-index: 1000;
    }

    .download-content {
      position: relative;
      padding-right: 24px;
    }

    .filename {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
    }

    .progress-container {
      height: 4px;
      background: #eee;
      border-radius: 2px;
      overflow: hidden;
      margin-bottom: 4px;
    }

    .progress-bar {
      height: 100%;
      background: #4CAF50;
      transition: width 0.3s ease;
    }

    .percentage {
      font-size: 12px;
      color: #666;
    }

    .cancel-btn {
      position: absolute;
      top: 0;
      right: 0;
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      color: #666;
    }

    .cancel-btn:hover {
      color: #333;
    }
  `]
})
export class DownloadProgressComponent implements OnInit, OnDestroy {
  isDownloading = false;
  progress = 0;
  fileName = '';
  private destroy$ = new Subject<void>();

  constructor(
    private stateStore: StateStoreService,
    private assetService: AssetService
  ) {}

  ngOnInit() {
    this.subscribeToStoreChanges();
  }

  private subscribeToStoreChanges() {
    interval(100)
      .pipe(
        takeUntil(this.destroy$),
        map(() => ({
          isDownloading: this.stateStore.getStoreState('isDownloading'),
          progress: this.stateStore.getStoreState('downloadProgress'),
          fileName: this.stateStore.getStoreState('downloadFileName')
        }))
      )
      .subscribe(state => {
        this.isDownloading = state.isDownloading;
        this.progress = state.progress;
        this.fileName = state.fileName;
      });
  }

  cancelDownload() {
    this.assetService.cancelExport();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}

// http.interceptor.ts
export class HttpInterceptor implements HttpInterceptor {
  constructor(private stateStore: StateStoreService) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Don't show loader for blob downloads
    if (request.responseType === 'blob') {
      return next.handle(request);
    }

    // Show loader for other API calls
    this.stateStore.setStoreState('loading', true);
    
    return next.handle(request).pipe(
      finalize(() => {
        this.stateStore.setStoreState('loading', false);
      })
    );
  }
}