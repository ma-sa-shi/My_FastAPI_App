import type { ApiErrorResponse } from './types';

/**
 * サーバーエラーレスポンスからエラーメッセージを安全に抽出する内部関数
 */
async function extractErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type');

  // JSON形式のみパースする
  if (contentType && contentType.includes('application/json')) {
    try {
      const errorData: ApiErrorResponse = await response.json();
      return errorData.detail || errorData.message || `Error: ${response.status}`;
    } catch {
      return `レスポンスの解析に失敗しました (Status: ${response.status})`;
    }
  }
  return `サーバーエラーが発生しました (Status: ${response.status})`;
}

/**
 * 標準的なAPIリクエストユーティリティ
 */
export async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorMessage = await extractErrorMessage(response);
      throw new Error(errorMessage);
    }

    // 204 No Contentはnullを許容してパースを避ける
    if (response.status === 204) {
      return null as T;
    }

    return (await response.json()) as T;
  } catch (error) {
    // 開発者へのエラーログ出力
    console.error('[API Request Failed]:', {
      url,
      error: error instanceof Error ? error.message : error,
    });

    // 呼び出し元にエラーを流しユーザーに通知
    throw error;
  }
}
