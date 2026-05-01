/**
 * APIから返却される標準的なエラーレスポンスの構造
 */
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  code?: string;
}

/**
 * ユーティリティ関数内での戻り値などで利用する型定義
 */
export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

export interface DocumentData {
  doc_id: number;
  filename: string;
  status: 'uploaded' | 'processing' | 'ingested' | 'failed';
  created_at: string;
}