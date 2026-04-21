import axios, { AxiosInstance, AxiosResponse } from 'axios';
import EventSource from 'eventsource';

// ─── Type Definitions ────────────────────────────────────────────────

export interface TLCMClientConfig {
  apiKey?: string;
  apiBase?: string;
  timeout?: number;
}

// Memory Types
export interface MemoryStoreRequest {
  workspace: string;
  content: string;
  epoch?: string;
  source?: string;
}

export interface MemoryRecallRequest {
  query: string;
  workspace: string;
  epoch?: string;
  limit?: number;
}

export interface MemoryUpdateRequest {
  workspace: string;
  new_content: string;
  reason: string;
}

export interface MemoryQueuedResponse {
  status: string;
  temp_id: string;
  message: string;
}

export interface MemoryStatusResponse {
  status: string;
  temp_id: string;
  memory_id?: string;
  error?: string;
}

export interface QueueMetrics {
  memory_queue_size: number;
  max_capacity: number;
  pending_in_db: number;
  processing_in_db: number;
}

// Workspace Types
export interface WorkspaceCreateRequest {
  name: string;
  description?: string;
}

export interface WorkspaceLinkRequest {
  source: string;
  target: string;
  reason: string;
}

// Epoch Types
export interface EpochCreateRequest {
  workspace: string;
  name: string;
  description?: string;
  start_date?: string;
  end_date?: string;
}

// Jump Types
export interface JumpRequest {
  workspace: string;
  from_epoch: string;
  to_epoch?: string;
  query?: string;
}

// Bus Types
export interface BusStatus {
  queue_depth: number;
  worker_running: boolean;
}

// SSE Event
export interface TLCMEvent {
  type: string;
  [key: string]: any;
}

// ─── Client ──────────────────────────────────────────────────────────

export class TLCMClient {
  private client: AxiosInstance;
  private apiBase: string;
  private apiKey?: string;

  constructor(config: TLCMClientConfig = {}) {
    this.apiBase = (config.apiBase || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '');
    this.apiKey = config.apiKey;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (config.apiKey) {
      headers['Authorization'] = `Bearer ${config.apiKey}`;
    }

    this.client = axios.create({
      baseURL: this.apiBase,
      headers,
      timeout: config.timeout || 30000,
    });
  }

  // ─── Memory Operations ──────────────────────────────────────────

  /**
   * Enqueue a memory for async processing (Tier 1 STM → Tier 2 LTM).
   * Returns 202 immediately with a temp_id.
   * Listen on listenForEvents() for the completion notification.
   */
  async remember(
    content: string,
    workspace: string = 'default_workspace',
    epoch?: string,
    source: string = 'user_stated',
  ): Promise<MemoryQueuedResponse> {
    const payload: MemoryStoreRequest = { content, workspace, epoch, source };
    const res = await this.client.post<MemoryQueuedResponse>('/memories/remember', payload);
    return res.data;
  }

  /**
   * Synchronous remember — blocks until Gemini completes biological
   * memory evaluation (LTM). Use for CLI, tests, or when you need
   * the memory_id immediately.
   */
  async rememberSync(
    content: string,
    workspace: string = 'default_workspace',
    epoch?: string,
    source: string = 'user_stated',
  ): Promise<any> {
    const payload: MemoryStoreRequest = { content, workspace, epoch, source };
    const res = await this.client.post('/memories/remember/sync', payload);
    return res.data;
  }

  /**
   * Temporal Recall — retrieve the most relevant past memories
   * via neuro-weighted vector search with biological decay.
   */
  async recall(
    query: string,
    workspace: string,
    epoch?: string,
    limit: number = 5,
  ): Promise<any[]> {
    const payload: MemoryRecallRequest = { query, workspace, epoch, limit };
    const res = await this.client.post('/memories/recall', payload);
    return res.data;
  }

  /**
   * Update a memory block, creating a new version in the
   * temporal chain (Graph Surgery).
   */
  async updateMemory(
    memoryId: string,
    workspace: string,
    newContent: string,
    reason: string,
  ): Promise<any> {
    const payload: MemoryUpdateRequest = { workspace, new_content: newContent, reason };
    const res = await this.client.put(`/memories/${memoryId}`, payload);
    return res.data;
  }

  /**
   * Fetch the exact linear evolution (version chain) of a
   * specific memory block.
   */
  async getVersionHistory(memoryId: string): Promise<any[]> {
    const res = await this.client.get(`/memories/${memoryId}/history`);
    return res.data;
  }

  /**
   * Poll the processing status of an async memory by temp_id.
   * Useful for clients that cannot connect to SSE.
   */
  async getMemoryStatus(tempId: string): Promise<MemoryStatusResponse> {
    const res = await this.client.get<MemoryStatusResponse>(`/memories/status/${tempId}`);
    return res.data;
  }

  /**
   * Get all memories in a specific workspace/epoch combination.
   */
  async getEpochMemories(workspace: string, epoch: string): Promise<any[]> {
    const res = await this.client.get(`/memories/workspace/${workspace}/epoch/${epoch}`);
    return res.data;
  }

  /**
   * Returns metrics on the internal async event queue.
   * Useful to detect backpressure or overload scenarios.
   */
  async getQueueMetrics(): Promise<QueueMetrics> {
    const res = await this.client.get<QueueMetrics>('/memories/queue/metrics');
    return res.data;
  }

  // ─── Workspace Operations ───────────────────────────────────────

  /** List all workspaces. */
  async listWorkspaces(): Promise<any[]> {
    const res = await this.client.get('/workspaces/');
    return res.data;
  }

  /** Create a new isolated workspace. */
  async createWorkspace(name: string, description?: string): Promise<any> {
    const payload: WorkspaceCreateRequest = { name, description };
    const res = await this.client.post('/workspaces/', payload);
    return res.data;
  }

  /** Get a workspace by name. */
  async getWorkspace(name: string): Promise<any> {
    const res = await this.client.get(`/workspaces/${name}`);
    return res.data;
  }

  /** Create an authorized link between two workspaces. */
  async linkWorkspaces(source: string, target: string, reason: string): Promise<any> {
    const payload: WorkspaceLinkRequest = { source, target, reason };
    const res = await this.client.post('/workspaces/link', payload);
    return res.data;
  }

  /** Get all authorized links for a workspace. */
  async getWorkspaceLinks(name: string): Promise<any[]> {
    const res = await this.client.get(`/workspaces/${name}/links`);
    return res.data;
  }

  // ─── Epoch Operations ──────────────────────────────────────────

  /** List all epochs in a workspace. */
  async listEpochs(workspace: string): Promise<any[]> {
    const res = await this.client.get(`/epochs/${workspace}`);
    return res.data;
  }

  /** Create a new temporal epoch within a workspace. */
  async createEpoch(
    workspace: string,
    name: string,
    description?: string,
    startDate?: string,
    endDate?: string,
  ): Promise<any> {
    const payload: EpochCreateRequest = {
      workspace,
      name,
      description,
      start_date: startDate,
      end_date: endDate,
    };
    const res = await this.client.post('/epochs/', payload);
    return res.data;
  }

  /** Close (seal) an epoch in a workspace. */
  async closeEpoch(workspace: string, epochName: string): Promise<any> {
    const res = await this.client.post(`/epochs/${workspace}/${epochName}/close`);
    return res.data;
  }

  // ─── Temporal Jump Operations ──────────────────────────────────

  /**
   * Perform a temporal jump — calculating how beliefs evolved
   * between two epochs.
   */
  async temporalJump(
    workspace: string,
    fromEpoch: string,
    toEpoch?: string,
    query?: string,
  ): Promise<any> {
    const payload: JumpRequest = {
      workspace,
      from_epoch: fromEpoch,
      to_epoch: toEpoch,
      query,
    };
    const res = await this.client.post('/jump/', payload);
    return res.data;
  }

  /**
   * Calculate the Mathematical Semantic Delta vector between
   * two epoch snapshots.
   */
  async getJumpDelta(
    workspace: string,
    fromEpoch: string,
    toEpoch?: string,
  ): Promise<any> {
    const payload: JumpRequest = {
      workspace,
      from_epoch: fromEpoch,
      to_epoch: toEpoch,
    };
    const res = await this.client.post('/jump/delta', payload);
    return res.data;
  }

  // ─── Export & Infrastructure ────────────────────────────────────

  /**
   * Download a Universal .tlcm Backup Format — zipped SQLite
   * database and ChromaDB vectors in a single portable payload.
   */
  async exportMind(): Promise<ArrayBuffer> {
    const res = await this.client.get('/export/', { responseType: 'arraybuffer' });
    return res.data;
  }

  /** Check the current state of the async memory bus. */
  async getBusStatus(): Promise<BusStatus> {
    const res = await this.client.get<BusStatus>('/bus/status');
    return res.data;
  }

  // ─── Real-Time SSE Events ──────────────────────────────────────

  /**
   * Subscribe to real-time Server-Sent Events from the TLCM engine.
   *
   * Events include:
   *   - memory_stored: A memory has been processed and committed to LTM
   *   - memory_error: A memory failed to process
   *
   * @returns A cleanup function that closes the SSE connection.
   *
   * @example
   * ```ts
   * const close = client.listenForEvents(
   *   (event) => console.log('Memory processed:', event),
   *   (err)   => console.error('SSE error:', err),
   * );
   *
   * // Later, to disconnect:
   * close();
   * ```
   */
  listenForEvents(
    onMessage: (data: TLCMEvent) => void,
    onError?: (err: any) => void,
  ): () => void {
    const headers: Record<string, string> = {};
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const source = new EventSource(`${this.apiBase}/events`, { headers });

    source.onmessage = (event) => {
      try {
        const payload: TLCMEvent = JSON.parse(event.data);
        onMessage(payload);
      } catch (e) {
        console.error('[TLCM] SSE Parse Error:', e);
      }
    };

    if (onError) {
      source.onerror = onError;
    }

    return () => source.close();
  }
}

// Default export for convenience
export default TLCMClient;
