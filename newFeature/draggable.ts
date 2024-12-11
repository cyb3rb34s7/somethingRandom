@Component({
  selector: 'app-download-progress',
  template: `
    <div *ngIf="isDownloading" 
         class="download-toast" 
         [@slideIn]
         [style.top.px]="position.y"
         [style.left.px]="position.x"
         (mousedown)="startDragging($event)"
         [class.dragging]="isDragging">
      <!-- Same content as before -->
      <div class="download-content">
        <div class="header" 
             [class.draggable]="true">  <!-- Visual indicator for draggable area -->
          <span class="title">{{ 
            downloadState === 'preparing' ? 'Preparing Export' : 'Downloading'
          }}</span>
          <button class="cancel-btn" (click)="cancelDownload()">
            <span>✕</span>
          </button>
        </div>
        <!-- Rest of your existing content -->
      </div>
    </div>
  `,
  styles: [`
    /* Previous styles remain the same */
    
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
      cursor: grab;  /* Indicate draggable */
      user-select: none;  /* Prevent text selection while dragging */
    }

    .dragging {
      cursor: grabbing;
      opacity: 0.9;  /* Visual feedback while dragging */
    }

    .draggable {
      cursor: grab;
    }

    .draggable:hover {
      background: rgba(0, 0, 0, 0.02);  /* Subtle hover effect */
    }

    .header {
      padding: 4px;
      border-radius: 4px;
    }

    /* Rest of your existing styles */
  `]
})
export class DownloadProgressComponent implements OnInit, OnDestroy {
  // Existing properties
  isDownloading = false;
  progress = 0;
  fileName = '';
  downloadState = '';
  
  // New properties for dragging
  isDragging = false;
  position = { x: window.innerWidth - 340, y: 20 };  // Initial position
  private dragOffset = { x: 0, y: 0 };
  private destroy$ = new Subject<void>();

  constructor(
    private stateStore: StateStoreService,
    private assetService: AssetService
  ) {
    // Add global mouse event listeners
    fromEvent<MouseEvent>(document, 'mousemove').pipe(
      takeUntil(this.destroy$)
    ).subscribe(event => this.onMouseMove(event));

    fromEvent<MouseEvent>(document, 'mouseup').pipe(
      takeUntil(this.destroy$)
    ).subscribe(() => this.stopDragging());
  }

  startDragging(event: MouseEvent) {
    // Don't start drag if clicking cancel button
    if ((event.target as HTMLElement).closest('.cancel-btn')) {
      return;
    }

    this.isDragging = true;
    const rect = (event.target as HTMLElement).getBoundingClientRect();
    this.dragOffset = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  onMouseMove(event: MouseEvent) {
    if (!this.isDragging) return;

    // Calculate new position
    let newX = event.clientX - this.dragOffset.x;
    let newY = event.clientY - this.dragOffset.y;

    // Keep within window bounds
    const maxX = window.innerWidth - 320;  // toast width
    const maxY = window.innerHeight - 100;  // approximate toast height

    newX = Math.max(0, Math.min(newX, maxX));
    newY = Math.max(0, Math.min(newY, maxY));

    this.position = { x: newX, y: newY };
  }

  stopDragging() {
    this.isDragging = false;
  }

  // Don't forget to clean up
  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ... rest of your existing component code
}