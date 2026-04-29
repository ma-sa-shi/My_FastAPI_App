const routes: Record<string, () => Promise<void>> = {
  '/register': async () => {
    await import('./register');
    document.getElementById('app')!.innerHTML = '<register-view></register-view>';
  },
  '/login': async () => {
    await import('./login');
    document.getElementById('app')!.innerHTML = '<login-view></login-view>';
  },
  '/upload': async () => {
    await import('./upload');
    document.getElementById('app')!.innerHTML = '<upload-view></upload-view>';
  },
  '/ingest': async () => {
    await import('./ingest');
    document.getElementById('app')!.innerHTML = '<ingest-view></ingest-view>';
  },
  '/query': async () => {
    await import('./query');
    document.getElementById('app')!.innerHTML = '<query-view></query-view>';
  },
};

export const handleNavigation = async () => {
  //URLのドメインより後ろを取得
  const path = window.location.pathname;
  const routeAction = routes[path] || routes['/register'];
  if (routeAction) {
    await routeAction();
  }
};